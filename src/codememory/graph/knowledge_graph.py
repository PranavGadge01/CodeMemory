"""Lightweight local knowledge graph model mapping problem relationships."""

from typing import List, Dict, Set, Tuple, Optional
from pydantic import BaseModel, Field
from codememory.domain.models import Problem, Submission


class GraphNode(BaseModel):
    """Node in the lightweight DSA knowledge graph."""

    id: str
    label: str
    type: str  # Topic, Problem, Approach, Mistake, Language


class GraphEdge(BaseModel):
    """Directed or undirected edge connecting knowledge nodes."""

    source_id: str
    target_id: str
    relationship: str  # TAGGED_WITH, USES_APPROACH, ENCOUNTERED_MISTAKE, SOLVED_IN, RELATED_TO


class KnowledgeGraph(BaseModel):
    """Complete graph representation of user DSA knowledge network."""

    nodes: List[GraphNode]
    edges: List[GraphEdge]

    def get_neighbors(self, node_id: str) -> List[GraphNode]:
        """Find connected neighbor nodes for a given node ID."""
        connected_ids = set()
        for edge in self.edges:
            if edge.source_id == node_id:
                connected_ids.add(edge.target_id)
            elif edge.target_id == node_id:
                connected_ids.add(edge.source_id)
        return [node for node in self.nodes if node.id in connected_ids]


class KnowledgeGraphBuilder:
    """Builder for constructing the lightweight DSA relationship graph."""

    def build_graph(self, problems: List[Problem], submissions: List[Submission]) -> KnowledgeGraph:
        """Construct graph nodes and edges from problems and submission history."""
        nodes_dict: Dict[str, GraphNode] = {}
        edges_set: Set[Tuple[str, str, str]] = set()

        # Group submissions by problem
        prob_subs: Dict[str, List[Submission]] = {}
        for sub in submissions:
            prob_subs.setdefault(sub.problem_id, []).append(sub)

        for problem in problems:
            # 1. Problem Node
            p_node_id = f"prob_{problem.id}"
            nodes_dict[p_node_id] = GraphNode(id=p_node_id, label=problem.title, type="Problem")

            # 2. Topic Nodes & Edges
            for topic in problem.topics:
                t_node_id = f"topic_{topic.lower().replace(' ', '_')}"
                if t_node_id not in nodes_dict:
                    nodes_dict[t_node_id] = GraphNode(id=t_node_id, label=topic, type="Topic")
                edges_set.add((p_node_id, t_node_id, "TAGGED_WITH"))

            subs = prob_subs.get(problem.id, [])
            for sub in subs:
                # 3. Language Node
                lang_node_id = f"lang_{sub.language.lower()}"
                if lang_node_id not in nodes_dict:
                    nodes_dict[lang_node_id] = GraphNode(id=lang_node_id, label=sub.language.capitalize(), type="Language")
                edges_set.add((p_node_id, lang_node_id, "SOLVED_IN"))

            # 4 & 5. Approach and Mistake Nodes from Attempts
            for attempt in problem.attempts:
                if attempt.approach_summary or attempt.reasoning:
                    appr_label = (attempt.approach_summary or attempt.reasoning or "").strip()[:30]
                    appr_node_id = f"appr_{hash(appr_label) & 0xFFFFFFFF}"
                    if appr_node_id not in nodes_dict:
                        nodes_dict[appr_node_id] = GraphNode(id=appr_node_id, label=appr_label, type="Approach")
                    edges_set.add((p_node_id, appr_node_id, "USES_APPROACH"))

                for mist in attempt.mistakes:
                    mist_label = mist.strip()[:30]
                    mist_node_id = f"mist_{hash(mist_label) & 0xFFFFFFFF}"
                    if mist_node_id not in nodes_dict:
                        nodes_dict[mist_node_id] = GraphNode(id=mist_node_id, label=mist_label, type="Mistake")
                    edges_set.add((p_node_id, mist_node_id, "ENCOUNTERED_MISTAKE"))

        # 6. Connect Related Problems sharing 2+ topics
        problem_list = list(problems)
        for i in range(len(problem_list)):
            for j in range(i + 1, len(problem_list)):
                p1, p2 = problem_list[i], problem_list[j]
                shared = set(p1.topics).intersection(set(p2.topics))
                if len(shared) >= 2:
                    edges_set.add((f"prob_{p1.id}", f"prob_{p2.id}", "RELATED_TO"))

        edges = [
            GraphEdge(source_id=src, target_id=tgt, relationship=rel)
            for src, tgt, rel in edges_set
        ]

        return KnowledgeGraph(nodes=list(nodes_dict.values()), edges=edges)
