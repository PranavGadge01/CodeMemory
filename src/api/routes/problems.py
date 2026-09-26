from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from codememory.core.service import CodeMemoryService
from codememory.domain.enums import DifficultyLevel
from codememory.domain.exceptions import ProblemNotFoundError

from api.dependencies import get_service
from api.schemas.common import PaginatedResponse
from api.schemas.problems import ProblemOut, ProblemListItemOut, SolutionEvolutionOut

router = APIRouter(tags=["problems"])

@router.get("/problems", response_model=PaginatedResponse[ProblemListItemOut])
def list_problems(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    service: CodeMemoryService = Depends(get_service)
):
    """List problems with python-side filtering and pagination.

    When a LeetCode account is connected, only problems with submissions from
    that account are returned.
    """
    all_problems = service.list_problems()
    
    # Apply filters
    filtered = all_problems
    if search:
        s = search.lower()
        filtered = [p for p in filtered if s in p.title.lower() or s in p.slug.lower()]
    
    if difficulty:
        d_upper = difficulty.upper()
        try:
            d_enum = DifficultyLevel[d_upper]
            filtered = [p for p in filtered if p.difficulty == d_enum]
        except KeyError:
            pass # Ignore invalid difficulty filters
            
    if status:
        status = status.lower()
        # To filter by status (solved/unsolved), we check if there's any accepted attempt
        # This is a bit of logic, but it's basic filtering on domain objects.
        if status == "solved":
            filtered = [p for p in filtered if any(a.is_accepted for a in p.attempts)]
        elif status == "unsolved":
            filtered = [p for p in filtered if not any(a.is_accepted for a in p.attempts)]

    # Sort: default to created_at descending
    filtered.sort(key=lambda x: x.created_at, reverse=True)
    
    # Paginate
    total = len(filtered)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items = filtered[start_idx:end_idx]
    
    return PaginatedResponse(
        items=[ProblemListItemOut(**p.model_dump()) for p in items],
        page=page,
        page_size=page_size,
        total=total
    )

@router.get("/problems/{slug}", response_model=ProblemOut)
def get_problem(slug: str, service: CodeMemoryService = Depends(get_service)):
    """Get a problem by its slug."""
    try:
        problem = service.get_problem(slug, account=service.active_account)
        return ProblemOut(**problem.model_dump())
    except ProblemNotFoundError:
        raise HTTPException(status_code=404, detail="Problem not found")


@router.get("/problems/{slug}/evolution", response_model=SolutionEvolutionOut)
def get_problem_evolution(slug: str, service: CodeMemoryService = Depends(get_service)):
    """Get solution evolution summary for a problem.

    When a LeetCode account is connected, only that account's submissions are
    used to build the evolution timeline.
    """
    try:
        evolution = service.get_solution_evolution(slug)
        return SolutionEvolutionOut(
            problem_id=evolution.problem_id,
            problem_title=evolution.problem_title,
            total_attempts=evolution.total_attempts,
            steps=[s.model_dump(mode="json") for s in evolution.steps],
            evolution_narrative=evolution.evolution_narrative,
            key_breakthrough=evolution.key_breakthrough,
            better_approach=getattr(evolution, "better_approach", None),
            similar_problems=getattr(evolution, "similar_problems", []),
        )
    except ProblemNotFoundError:
        raise HTTPException(status_code=404, detail="Problem not found")
