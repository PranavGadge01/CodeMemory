from fastapi import APIRouter, Depends
from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.knowledge import KnowledgeOut

router = APIRouter(tags=["knowledge"])

@router.get("/knowledge", response_model=KnowledgeOut)
def get_knowledge(service: CodeMemoryService = Depends(get_service)):
    """Get the knowledge graph. Clusters are deferred for V1."""
    graph = service.get_knowledge_graph()
    
    return KnowledgeOut(
        graph={
            "nodes": [n.model_dump() for n in graph.nodes],
            "edges": [e.model_dump() for e in graph.edges]
        },
        clusters=[] # Deferred: Requires business logic to compute mastery which is not in the service layer yet.
    )
