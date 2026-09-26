from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException

from codememory.core.service import CodeMemoryService
from codememory.domain.models import Submission

from api.dependencies import get_service
from api.schemas.problems import SubmissionOut
from api.schemas.submissions import SubmissionListOut

router = APIRouter(tags=["submissions"])

def _get_all_submissions(service: CodeMemoryService) -> List[Submission]:
    """Helper to flatten all submissions from all problems.

    When a LeetCode account is connected, only that account's submissions
    are returned.
    """
    submissions = []
    account = service.active_account
    for problem in service.list_problems():
        for attempt in problem.attempts:
            for s in attempt.submissions:
                if account is None or s.source_account == account:
                    submissions.append(s)
    return submissions

@router.get("/submissions", response_model=SubmissionListOut)
def list_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    language: Optional[str] = None,
    status: Optional[str] = None,
    problem: Optional[str] = None,
    service: CodeMemoryService = Depends(get_service)
):
    """List flattened submissions with filtering and pagination."""
    all_subs = _get_all_submissions(service)
    
    filtered = all_subs
    if language:
        lang_lower = language.lower()
        filtered = [s for s in filtered if s.language.lower() == lang_lower]
        
    if status:
        status_lower = status.lower()
        filtered = [s for s in filtered if s.status.value.lower() == status_lower]
        
    if problem:
        prob_lower = problem.lower()
        # Find the problem ID for the given slug/title
        matching_probs = [p.id for p in service.list_problems() if prob_lower in p.slug.lower() or prob_lower in p.title.lower()]
        filtered = [s for s in filtered if s.problem_id in matching_probs]

    # Sort descending by submission time
    filtered.sort(key=lambda x: x.submitted_at, reverse=True)
    
    total = len(filtered)
    accepted = sum(1 for submission in filtered if submission.status.value.lower() == "accepted")
    problem_count = len({submission.problem_id for submission in filtered})
    language_count = len({submission.language.casefold() for submission in filtered})
    summary = {
        "total": total,
        "accepted": accepted,
        "failed": total - accepted,
        "acceptance_rate": (accepted / total * 100) if total else 0.0,
        "problem_count": problem_count,
        "language_count": language_count,
    }
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items = filtered[start_idx:end_idx]
    
    return SubmissionListOut(
        items=[SubmissionOut(**s.model_dump()) for s in items],
        page=page,
        page_size=page_size,
        total=total,
        summary=summary,
    )

@router.get("/submissions/{id}", response_model=SubmissionOut)
def get_submission(id: str, service: CodeMemoryService = Depends(get_service)):
    """Get a single submission by ID, scoped to the active account."""
    sub = service.get_submission(id, account=service.active_account)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return SubmissionOut(**sub.model_dump())
