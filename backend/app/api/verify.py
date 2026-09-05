"""POST /verify — run submitted code against the problem's test cases."""

from fastapi import APIRouter, HTTPException

from app.schemas.verify import VerifyRequest, VerifyResponse
from app.services import database_service, judge_service

router = APIRouter(tags=["verify"])


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    """problem_id accepts a UUID or a slug, like GET /problems/{id}."""
    if not req.code.strip():
        raise HTTPException(status_code=422, detail="code must not be empty")

    if database_service.resolve_problem_id(req.problem_id) is None:
        raise HTTPException(status_code=404, detail=f"No problem matching '{req.problem_id}'")

    cases = database_service.get_test_cases(req.problem_id, limit=judge_service.MAX_TEST_CASES)
    if not cases:
        # Not an error: the corpus has the problem but nobody has generated
        # tests for it yet (ai/verification/test_generator.py, task for Dev 2).
        return VerifyResponse(status="No test cases for this problem", passed=0, total=0)

    result = judge_service.run_submission(req, cases)
    # Audit trail; never let a failed write sink the user's result.
    database_service.save_submission(req.problem_id, req.code, req.language, result)
    return result
