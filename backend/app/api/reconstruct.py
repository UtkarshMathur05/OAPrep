"""POST /reconstruct — memory + chosen candidate -> full problem statement."""

from fastapi import APIRouter

from app.schemas.reconstruct import ReconstructRequest, ReconstructResponse
from app.services import ai_service

router = APIRouter(tags=["reconstruct"])


@router.post("/reconstruct", response_model=ReconstructResponse)
def reconstruct(req: ReconstructRequest) -> ReconstructResponse:
    return ai_service.reconstruct(req)
