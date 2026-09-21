from fastapi import APIRouter, Depends
from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.knowledge import KnowledgeOut

router = APIRouter(tags=["knowledge"])

@router.get("/knowledge", response_model=KnowledgeOut)
def get_knowledge(service: CodeMemoryService = Depends(get_service)):
    """Get the knowledge graph and topic-based clusters."""
    graph = service.get_knowledge_graph()
    clusters = service.analytics_service.get_knowledge_clusters()

    return KnowledgeOut(
        graph={
            "nodes": [n.model_dump(mode="json") for n in graph.nodes],
            "edges": [e.model_dump(mode="json") for e in graph.edges]
        },
        clusters=[c.model_dump(mode="json") for c in clusters]
    )
