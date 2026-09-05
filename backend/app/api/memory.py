"""POST /memory — transcript -> Problem Genome."""

from fastapi import APIRouter

from app.schemas.memory import MemoryRequest, MemoryResponse
from app.services import ai_service

router = APIRouter(tags=["memory"])


@router.post("/memory", response_model=MemoryResponse)
def create_memory(req: MemoryRequest) -> MemoryResponse:
    # TODO(backend): persist the genome to problem_memories and return its id.
    return ai_service.extract_memory(req)
