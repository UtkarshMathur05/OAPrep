"""POST /search — Problem Genome -> ranked candidate problems."""

from fastapi import APIRouter

from app.schemas.search import SearchRequest, SearchResponse
from app.services import ai_service

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    return ai_service.search_candidates(req)
