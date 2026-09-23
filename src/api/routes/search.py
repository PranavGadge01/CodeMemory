from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from codememory.core.service import CodeMemoryService

from api.dependencies import get_service
from api.schemas.problems import SearchResponse, SearchResultItem

router = APIRouter(tags=["search"])

MAX_QUERY_LENGTH = 200
MAX_RESULTS = 50

@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=MAX_QUERY_LENGTH),
    limit: Optional[int] = Query(None, ge=1, le=MAX_RESULTS),
    service: CodeMemoryService = Depends(get_service),
):
    """Global lexical search across problems and submissions.

    Results are returned in deterministic rank order:
    1. Exact title match
    2. Title starts with query
    3. Title contains query
    4. Slug match
    5. Topic match

    All LeetCode-derived results respect the active account: if a LeetCode
    account is connected, only that account's data is returned; otherwise
    LeetCode-sourced submissions are excluded entirely.
    """
    raw = service.global_search(q, limit=limit or MAX_RESULTS)

    results: List[SearchResultItem] = []
    for item in raw:
        results.append(SearchResultItem(
            type=item["_type"],
            id=item["id"],
            title=item["title"],
            slug=item["slug"],
            metadata=item.get("metadata", {}),
        ))

    return SearchResponse(query=q, results=results)
