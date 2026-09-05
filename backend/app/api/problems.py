"""GET /problems — browse the known-problem corpus."""

from typing import List

from fastapi import APIRouter

from app.schemas.reconstruct import Problem

router = APIRouter(tags=["problems"])


@router.get("/problems", response_model=List[Problem])
def list_problems(limit: int = 20):
    # TODO(backend): read from database_service.
    return []


@router.get("/problems/{problem_id}", response_model=Problem)
def get_problem(problem_id: str):
    # TODO(backend): read from database_service; 404 when missing.
    raise NotImplementedError
