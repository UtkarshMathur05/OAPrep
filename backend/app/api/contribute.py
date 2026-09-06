"""POST /contribute — add a problem the corpus is missing.

Thin: validate, delegate to contribute_service, return.
"""

from fastapi import APIRouter

from app.schemas.contribute import (
    ContributeMatchRequest, ContributeMatchResponse,
    ContributeRequest, ContributeResponse,
)
from app.services import contribute_service

router = APIRouter(tags=["contribute"])


@router.post("/contribute/match", response_model=ContributeMatchResponse)
def contribute_match(req: ContributeMatchRequest) -> ContributeMatchResponse:
    """Check whether we already have what the user is describing."""
    return contribute_service.match(req)


@router.post("/contribute", response_model=ContributeResponse)
def contribute(req: ContributeRequest) -> ContributeResponse:
    """Create a community problem, or corroborate an existing one."""
    return contribute_service.submit(req)
