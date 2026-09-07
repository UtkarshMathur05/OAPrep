"""POST /verify — run submitted code against the problem's test cases."""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.identity import current_session
from app.languages import LANGUAGES
from app.schemas.verify import (
    LanguageOut, ProblemProgress, SessionProgress, VerifyRequest, VerifyResponse,
)
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

        # A format the problem already carries is authoritative: people may
        # already have solved it under that shape.
        suite = generate_suite(ReconstructedProblem(
            title=row["title"], description=row["description"],
            io_format=row.get("io_format") or "",
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

    database_service.save_test_cases(problem_id, kept, io_format=suite.io_format)
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


@router.get("/languages", response_model=list[LanguageOut])
def languages() -> list[LanguageOut]:
    """Every language a solution can be written in, with its starter program.

    The starter lives server-side so the editor and the runner can never
    disagree about the calling convention — both come from app.languages.
    """
    return [
        LanguageOut(id=l.id, label=l.label, monaco=l.monaco, starter=l.starter)
        for l in LANGUAGES
    ]


@router.get("/progress", response_model=SessionProgress)
def progress(request: Request) -> SessionProgress:
    """What the calling session has solved and attempted, for marking listings."""
    return SessionProgress(**database_service.session_progress(current_session(request)))


@router.get("/progress/{problem_id}", response_model=ProblemProgress)
def problem_progress(problem_id: str, request: Request) -> ProblemProgress:
    """The calling session's standing on one problem. Survives a page reload."""
    return ProblemProgress(
        **database_service.problem_progress(current_session(request), problem_id)
    )


@router.post("/verify", response_model=VerifyResponse)
def verify(req: VerifyRequest, request: Request) -> VerifyResponse:
    """Run or submit a solution. problem_id accepts a UUID or a slug."""
    if not req.code.strip():
        raise HTTPException(status_code=422, detail="code must not be empty")

    if database_service.resolve_problem_id(req.problem_id) is None:
        raise HTTPException(status_code=404, detail=f"No problem matching '{req.problem_id}'")

    session = current_session(request)

    row = database_service.get_problem(req.problem_id) or {}

    cases = database_service.get_test_cases(req.problem_id, limit=judge_service.MAX_TEST_CASES)

    # A SQL or class-design problem is not a program that reads stdin, so
    # generating cases for one would invent an input format it does not have and
    # then judge somebody against it. Say so instead.
    from app.api.problems import _solvability
    verdict = _solvability(row | {"test_case_count": len(cases)})
    if not verdict["solvable"]:
        return VerifyResponse(status=verdict["unsolvable_reason"], passed=0, total=0,
                              kind=req.kind, **_standing(session, req.problem_id))

    if not cases and row.get("exec_mode") != "functional":
        # Only stdin problems generate their own cases. A functional problem's
        # cases are JSON arguments matching a typed signature; a generated stdin
        # case would be silently unrunnable against it.
        # Generate once, store, and carry on. Costs one model request per
        # problem ever — the next visit reads these rows back.
        cases = _generate_and_store(req.problem_id)
    if not cases:
        # Not recorded as an attempt: the user's code never ran, so counting it
        # against them would be wrong.
        return VerifyResponse(status="No test cases for this problem", passed=0, total=0,
                              kind=req.kind, **_standing(session, req.problem_id))

    result = judge_service.run_submission(req, cases, problem=row)
    result.kind = req.kind
    result.all_passed = result.total > 0 and result.passed == result.total

    # Audit trail; never let a failed write sink the user's result.
    result.submission_id = database_service.save_submission(
        req.problem_id, req.code, req.language, result,
        kind=req.kind, session_id=session,
    )

    # Read the standing back rather than incrementing in memory, so the counter
    # is the database's answer and stays right if two tabs are open.
    for field, value in _standing(session, req.problem_id).items():
        setattr(result, field, value)
    return result


def _standing(session, problem_id: str) -> dict:
    """The session's counters for this problem, shaped for VerifyResponse."""
    p = database_service.problem_progress(session, problem_id)
    return {"solved": p["solved"], "runs": p["runs"], "submissions": p["submissions"]}
