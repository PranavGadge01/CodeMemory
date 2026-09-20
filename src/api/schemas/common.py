from typing import Generic, TypeVar, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")

class BaseCamelModel(BaseModel):
    """Base model that automatically aliases fields to camelCase."""
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

class PaginatedResponse(BaseCamelModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int
