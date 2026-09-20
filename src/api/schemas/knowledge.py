from typing import List, Optional
from api.schemas.common import BaseCamelModel

class GraphNodeOut(BaseCamelModel):
    id: str
    label: str
    type: str

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
