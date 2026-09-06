"""Community contributions: match first, create only if nothing matches.

The order matters. Letting a user create a row before checking the corpus would
fill the database with near-duplicates of problems we already have, and the
recall pipeline is exactly the tool for noticing that — so the contribution
flow runs it first and only writes a new row when it comes up empty.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from app.config import GEMINI_API_KEY, USE_MOCK_AI
from app.schemas.contribute import (
    ContributeMatchRequest, ContributeMatchResponse,
    ContributeRequest, ContributeResponse,
)
from app.schemas.memory import MemoryRequest
from app.schemas.search import SearchRequest
from app.services import ai_service, database_service

log = logging.getLogger(__name__)

# Above this rerank confidence we assume the user is describing a problem we
# already have. Not a hard block — the UI still offers "none of these" — but it
# flips the default from "create" to "confirm".
DUPLICATE_THRESHOLD = 0.75


def match(req: ContributeMatchRequest) -> ContributeMatchResponse:
    """Run the recall pipeline over a contribution, tolerating no matches.

    Unlike POST /search this must not 404 when the corpus has nothing: "we do
    not have this" is the answer that sends the user on to create it.
    """
    extracted = ai_service.extract_memory(MemoryRequest(transcript=req.transcript))
    memory_id = database_service.save_memory(extracted.memory, req.transcript)

    candidates = []
    try:
        found = ai_service.search_candidates(
            SearchRequest(memory=extracted.memory, memory_id=memory_id, top_k=req.top_k)
        )
        candidates = found.candidates
    except HTTPException as exc:
        # 404 "nothing found" and 400 "too vague" are both normal here.
        if exc.status_code not in (400, 404):
            raise
        log.info("contribution match found nothing: %s", exc.detail)

    top = candidates[0].confidence if candidates else 0.0
    return ContributeMatchResponse(
        memory_id=memory_id,
        memory=extracted.memory,
        candidates=candidates,
        likely_duplicate=top >= DUPLICATE_THRESHOLD,
    )


def submit(req: ContributeRequest) -> ContributeResponse:
    """Either corroborate an existing problem or create a community one."""
    if req.confirm_problem_id:
        return _confirm(req)
    return _create(req)


def _confirm(req: ContributeRequest) -> ContributeResponse:
    problem_id = database_service.resolve_problem_id(req.confirm_problem_id)
    if problem_id is None:
        raise HTTPException(404, "That problem no longer exists.")

    row = database_service.get_problem(problem_id)
    result = database_service.record_contribution(
        problem_id,
        kind="confirmed",
        transcript=req.transcript,
        details=req.details.model_dump(),
    )
    community = row["origin"] == "community"
    return ContributeResponse(
        problem_id=problem_id,
        slug=row["slug"],
        title=row["title"],
        action="confirmed",
        confidence=result["confidence"],
        contribution_count=result["contribution_count"],
        test_case_count=row.get("test_case_count", 0),
        message=(
            f"Thanks — that is {result['contribution_count']} independent "
            f"descriptions of this problem, so its confidence is now "
            f"{result['confidence']:.0%}."
            if community else
            "Thanks — we already had this one from LeetCode, so its statement "
            "is unchanged. Your description was recorded."
        ),
    )


def _create(req: ContributeRequest) -> ContributeResponse:
    if USE_MOCK_AI or not GEMINI_API_KEY:
        raise HTTPException(
            503, "Contributing needs the AI pipeline. Set USE_MOCK_AI=false with a "
                 "GEMINI_API_KEY, or browse the existing corpus instead.")

    from ai.contribution.draft import draft_problem, embedding_text, slugify
    from ai.gemini_client import AIError, embed

    details = req.details.model_dump()
    try:
        drafted = draft_problem(req.transcript, details)
    except AIError as exc:
        log.warning("draft failed: %s", exc)
        raise HTTPException(503, "We couldn't write that problem up just now. Try again shortly.")

    if not drafted.description.strip():
        # An empty statement is worse than no row: it would match everything
        # in retrieval and reconstruct into nonsense.
        raise HTTPException(
            422, "There wasn't enough there to write a problem statement. "
                 "Add what the input looks like and what you had to return.")

    topics = drafted.topics or details.get("topics") or []
    difficulty = drafted.difficulty or (details.get("difficulty") or "").lower() or None

    try:
        vector = embed(embedding_text(drafted.title, drafted.description,
                                      topics, difficulty or ""))
    except AIError as exc:
        # Without an embedding the row exists but is invisible to recall, which
        # is a confusing half-success. Refuse instead.
        log.warning("contribution embedding failed: %s", exc)
        raise HTTPException(503, "We couldn't index that problem. Nothing was saved; try again.")

    created = database_service.create_community_problem(
        slug=slugify(drafted.title),
        title=drafted.title,
        description=_with_assumptions(drafted),
        difficulty=difficulty,
        topics=topics,
        companies=details.get("companies") or [],
        embedding=vector,
    )

    # The row is inserted with contribution_count 0; this call is what makes it
    # 1. Seeding the counter at 1 as well double-counted the author, so the
    # second person to describe a problem pushed it straight to 0.65.
    recorded = database_service.record_contribution(
        created["id"], kind="created", transcript=req.transcript, details=details)

    stored = _seed_test_cases(created["id"], drafted)

    return ContributeResponse(
        problem_id=created["id"],
        slug=created["slug"],
        title=drafted.title,
        action="created",
        confidence=recorded["confidence"],
        contribution_count=recorded["contribution_count"],
        test_case_count=stored,
        message="Added as a community problem at 35% confidence. It rises each "
                "time someone else describes the same problem.",
    )


def _with_assumptions(drafted) -> str:
    """Append the model's own assumptions to the stored statement.

    A community row is an inference; burying that in a column nobody renders
    would be exactly the silent promotion CLAUDE.md §19 forbids. Keeping it in
    the description means it survives into reconstruction and onto the page.
    """
    body = drafted.description.strip()
    if drafted.constraints:
        body += "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in drafted.constraints)
    if drafted.assumptions:
        body += ("\n\nAssumed while writing this up (not remembered by the "
                 "contributor):\n" + "\n".join(f"- {a}" for a in drafted.assumptions))
    return body


def _seed_test_cases(problem_id: str, drafted) -> int:
    """Store the drafted examples as test cases so the problem is solvable.

    Best-effort: a problem with no tests still browses and still reconstructs,
    and /verify generates its own suite on demand.
    """
    from ai.models.problem_genome import TestCase

    cases = [
        TestCase(input=e.input.rstrip(), expected_output=e.output.rstrip(),
                 explanation=e.explanation)
        for e in drafted.examples
        if (e.input or "").strip() and (e.output or "").strip()
    ]
    if not cases:
        return 0
    try:
        return database_service.save_test_cases(problem_id, cases)
    except Exception:  # noqa: BLE001 - never lose the problem over its examples
        log.warning("could not store contributed examples", exc_info=True)
        return 0
