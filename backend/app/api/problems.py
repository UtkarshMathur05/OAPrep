"""GET /problems — browse the known-problem corpus.

Thin: filters in, service call, shape out. All SQL lives in database_service.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.problems import ProblemDetail, ProblemListResponse
from app.services import database_service

router = APIRouter(tags=["problems"])


@router.get("/problems", response_model=ProblemListResponse)
def list_problems(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    difficulty: Optional[str] = Query(None, description="easy | medium | hard"),
    company: Optional[str] = Query(None, description="lowercase slug, e.g. 'google'"),
    search: Optional[str] = Query(None, description="case-insensitive title match"),
) -> ProblemListResponse:
    rows, total = database_service.list_problems(
        limit=limit, offset=offset,
        difficulty=difficulty, company=company, search=search,
    )
    return ProblemListResponse(total=total, limit=limit, offset=offset, problems=rows)


@router.get("/problems/{problem_id}", response_model=ProblemDetail)
def get_problem(problem_id: str) -> ProblemDetail:
    """Accepts a UUID or a slug, so /problems/two-sum works."""
    row = database_service.get_problem(problem_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No problem matching '{problem_id}'")
    return ProblemDetail(**row)
