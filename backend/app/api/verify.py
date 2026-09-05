"""POST /verify — run submitted code against the problem's test cases."""

from fastapi import APIRouter

from app.schemas.verify import VerifyRequest, VerifyResponse
from app.services import judge_service

router = APIRouter(tags=["verify"])


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    # TODO(backend): load test cases for problem_id, then record the submission.
    return judge_service.run_submission(req)
