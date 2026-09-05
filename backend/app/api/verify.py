"""POST /verify — run submitted code against the problem's test cases."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.verify import VerifyRequest, VerifyResponse
from app.services import database_service, judge_service

router = APIRouter(tags=["verify"])

log = logging.getLogger(__name__)


def _generate_and_store(problem_id: str) -> list[dict]:
    """Fallback source of test cases, for a problem the user never reconstructed.

    The primary source is /reconstruct, which stores its own examples for free.
    This path only runs when that never happened, and it is the untrusted one:
    asked for answers alone the model produces inconsistent stdin formats and
    wrong arithmetic. So it also asks for a reference solution, runs it on
    Judge0, and keeps only the cases where executing the code agrees with the
    claimed answer. Two independent derivations agreeing is the evidence.

    Returns [] on any failure — a problem without tests is a state to report,
    never a 500 (CLAUDE.md §20).
    """
    row = database_service.get_problem(problem_id)
    if row is None:
        return []

    try:
        from ai.models.problem_genome import ReconstructedProblem
        from ai.verification.test_generator import generate_suite

        suite = generate_suite(ReconstructedProblem(
            title=row["title"], description=row["description"],
        ))
    except Exception:  # noqa: BLE001 - includes a missing API key
        # exc_info on purpose: this catch is broad enough to swallow a plain
        # code bug, and a silent [] then looks exactly like "no tests exist".
        log.warning("test generation unavailable for %r", problem_id, exc_info=True)
        return []

    if not suite.cases:
        return []

    kept = _validated(suite)
    if not kept:
        log.warning("all %d generated cases for %r failed validation",
                    len(suite.cases), problem_id)
        return []

    database_service.save_test_cases(problem_id, kept)
    log.info("stored %d/%d validated cases for %r", len(kept), len(suite.cases), problem_id)
    return database_service.get_test_cases(problem_id, limit=judge_service.MAX_TEST_CASES)


def _validated(suite) -> list:
    """Keep only cases whose claimed answer matches what the reference prints."""
    actual = judge_service.run_reference(
        suite.reference_solution, [c.input for c in suite.cases]
    )
    kept = []
    for case, got in zip(suite.cases, actual):
        if got is None:
            continue  # reference crashed or timed out on this input
        if got.rstrip() == (case.expected_output or "").rstrip():
            kept.append(case)
    return kept


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest) -> VerifyResponse:
    """problem_id accepts a UUID or a slug, like GET /problems/{id}."""
    if not req.code.strip():
        raise HTTPException(status_code=422, detail="code must not be empty")

    if database_service.resolve_problem_id(req.problem_id) is None:
        raise HTTPException(status_code=404, detail=f"No problem matching '{req.problem_id}'")

    cases = database_service.get_test_cases(req.problem_id, limit=judge_service.MAX_TEST_CASES)
    if not cases:
        # Generate once, store, and carry on. Costs one model request per
        # problem ever — the next visit reads these rows back.
        cases = _generate_and_store(req.problem_id)
    if not cases:
        return VerifyResponse(
            status="No test cases for this problem",
            passed=0, total=0,
        )

    result = judge_service.run_submission(req, cases)
    # Audit trail; never let a failed write sink the user's result.
    database_service.save_submission(req.problem_id, req.code, req.language, result)
    return result
