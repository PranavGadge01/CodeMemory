from typing import List, Optional, Dict, Any
from api.schemas.common import BaseCamelModel

class GraphNodeOut(BaseCamelModel):
    id: str
    label: str
    type: str
    # Optional expanded details for Problem nodes
    difficulty: Optional[str] = None
    topics: Optional[List[str]] = None
    approaches: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    mistakes: Optional[List[str]] = None
    # Connection counts for the knowledge snapshot
    connectionCount: Optional[int] = None

class GraphEdgeOut(BaseCamelModel):
    source_id: str
    target_id: str
    relationship: str

class KnowledgeGraphOut(BaseCamelModel):
    nodes: List[GraphNodeOut]
    edges: List[GraphEdgeOut]

class KnowledgeClusterOut(BaseCamelModel):
    id: str
    title: str
    description: str
    topic_id: str
    problem_ids: List[str]
    mastery_pct: int

class KnowledgeOut(BaseCamelModel):
    graph: KnowledgeGraphOut
    clusters: List[KnowledgeClusterOut]
    # Snapshot of entity counts for the knowledge header
    entityCounts: Dict[str, int]
