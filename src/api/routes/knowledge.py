"""Knowledge API routes.

Knowledge page endpoint - exposes the personal coding knowledge graph.
Focused on relationships between problems, topics, approaches, languages, and mistakes.
"""

from typing import Dict, Any
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from codememory.core.service import CodeMemoryService
from codememory.graph.knowledge_patterns import KnowledgePatternExtractor

from api.dependencies import get_service
from api.schemas.knowledge import KnowledgeOut
from api.schemas.knowledge_patterns import (
    PatternSummary,
    PatternRelationship,
    KnowledgePatternsOut,
)

router = APIRouter(tags=["knowledge"])

@router.get("/knowledge", response_model=KnowledgeOut)
def get_knowledge(service: CodeMemoryService = Depends(get_service)):
    """Get the knowledge graph with connections and entity counts.

    Returns a graph of relationships between coding concepts plus a snapshot
    of entity counts. When a LeetCode account is connected, only that account's
    data is used.
    """
    account = service.active_account
    snapshot = service.history_snapshot()
    graph = service.get_knowledge_graph(account=account, snapshot=snapshot)

    # Build expanded node data for problems
    problems_dict = {p.id: p for p in snapshot.problems}

    # Count connections per node (how many edges each node participates in)
    connection_counts: Dict[str, int] = defaultdict(int)
    for edge in graph.edges:
        connection_counts[edge.source_id] += 1
        connection_counts[edge.target_id] += 1

    # Build nodes with optional problem details
    nodes_out = []
    for node in graph.nodes:
        node_dict: Dict[str, Any] = {
            "id": node.id,
            "label": node.label,
            "type": node.type,
        }

        # For Problem nodes, add expanded details
        if node.type == "Problem":
            # Node id is "prob_<problem_id>"
            problem_id = node.id[5:] if node.id.startswith("prob_") else node.id
            problem = problems_dict.get(problem_id)
            if problem:
                # Collect unique approaches from attempts
                approaches = list(set(
                    att.approach_summary for att in problem.attempts
                    if att.approach_summary
                ))
                # Collect unique mistakes
                mistakes = list(set(
                    m for att in problem.attempts for m in (att.mistakes or [])
                ))
                # Collect unique languages from submissions
                languages = list(set(
                    sub.language.capitalize() for att in problem.attempts
                    for sub in att.submissions if sub.language
                ))

                node_dict.update({
                    "difficulty": problem.difficulty.value if hasattr(problem.difficulty, 'value') else str(problem.difficulty),
                    "topics": problem.topics,
                    "approaches": approaches,
                    "languages": languages,
                    "mistakes": mistakes,
                    "connectionCount": connection_counts.get(node.id, 0),
                })

        nodes_out.append(node_dict)

    # Compute entity counts for the knowledge snapshot
    type_counts: Dict[str, int] = defaultdict(int)
    for node in graph.nodes:
        type_counts[node.type] += 1

    return KnowledgeOut(
        graph={
            "nodes": nodes_out,
            "edges": [e.model_dump(mode="json") for e in graph.edges]
        },
        clusters=[],  # Deprecated - clusters belong to Analytics
        entityCounts=dict(type_counts)
    )


@router.get("/knowledge/patterns", response_model=KnowledgePatternsOut)
def get_knowledge_patterns(service: CodeMemoryService = Depends(get_service)):
    """Get pattern summaries and relationships for the Knowledge page.

    Returns the top patterns encountered in the user's practice history
    along with relationships between patterns that appear together.
    """
    account = service.active_account
    snapshot = service.history_snapshot()
    graph = service.get_knowledge_graph(account=account, snapshot=snapshot)

    # Build problem data with attempts and languages
    problems_data: Dict[str, Any] = {}
    for p in snapshot.problems:
        topics = p.topics or []

        # Get approaches from attempts
        approaches = []
        for att in p.attempts:
            if att.approach_summary:
                approaches.append(att.approach_summary)

        # Get languages from submissions
        languages = []
        for att in p.attempts:
            for sub in att.submissions:
                if sub.language:
                    languages.append(sub.language.capitalize())

        # Track if problem is solved (a Problem has no status of its own; it is
        # solved when at least one of its attempts was accepted).
        is_solved = any(att.is_accepted for att in p.attempts)

        # Get attempt statuses
        attempts_data = []
        for att in p.attempts:
            att_data = {
                "status": att.status.value if hasattr(att.status, 'value') else str(att.status),
                "approach_summary": att.approach_summary,
                "submissions": len(att.submissions),
            }
            attempts_data.append(att_data)

        problems_data[p.id] = {
            "topics": topics,
            "approaches": approaches,
            "languages": languages,
            "is_solved": is_solved,
            "attempts": attempts_data,
            "title": p.title,
            "slug": p.slug,
        }

    # Extract patterns and relationships
    extractor = KnowledgePatternExtractor()
    patterns, relationships = extractor.extract_patterns(graph, problems_data)

    return KnowledgePatternsOut(
        patterns=[PatternSummary(**p) for p in patterns],
        relationships=[PatternRelationship(**r) for r in relationships],
        generated_at=datetime.now(timezone.utc)
    )
