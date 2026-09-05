"""POST /memory — transcript -> Problem Genome."""

from fastapi import APIRouter, HTTPException

from app.schemas.memory import MemoryRequest, MemoryResponse
from app.services import ai_service, database_service

router = APIRouter(tags=["memory"])


@router.post("/memory", response_model=MemoryResponse)
def create_memory(req: MemoryRequest) -> MemoryResponse:
    if not req.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript must not be empty")

    result = ai_service.extract_memory(req)
    # Persist so /reconstruct has a real memory_id to load from. The genome the
    # caller sees is the one we stored, not a mock id.
    result.memory_id = database_service.save_memory(result.memory, req.transcript)
    return result


@router.get("/memory/{memory_id}", response_model=MemoryResponse)
def get_memory(memory_id: str) -> MemoryResponse:
    """Read back a stored genome — useful for debugging and for a shareable URL."""
    row = database_service.get_memory(memory_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No memory matching '{memory_id}'")

    from app.schemas.memory import Genome

    return MemoryResponse(memory_id=row["id"], memory=Genome(**{
        k: row[k] for k in ("concepts", "operations", "constraints", "objective",
                            "uncertainties", "data_structures", "algorithm_hints")
    }))
