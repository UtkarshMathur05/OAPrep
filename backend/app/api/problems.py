"""GET /problems — browse the known-problem corpus.

Thin: filters in, service call, shape out. All SQL lives in database_service.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.problems import FacetsResponse, ProblemDetail, ProblemListResponse
from app.services import database_service

router = APIRouter(tags=["problems"])


@router.get("/problems", response_model=ProblemListResponse)
def list_problems(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    difficulty: Optional[str] = Query(None, description="easy | medium | hard"),
    company: Optional[str] = Query(None, description="lowercase slug, e.g. 'google'"),
    search: Optional[str] = Query(None, description="case-insensitive title/statement match"),
    topic: Optional[str] = Query(None, description="LeetCode tag, e.g. 'Dynamic Programming'"),
    origin: Optional[str] = Query(None, description="corpus | community"),
    sort: str = Query("popularity",
                      description="popularity | title | difficulty | companies | "
                                  "acceptance | newest"),
) -> ProblemListResponse:
    rows, total = database_service.list_problems(
        limit=limit, offset=offset,
        difficulty=difficulty, company=company, search=search,
        topic=topic, origin=origin, sort=sort,
    )
    return ProblemListResponse(total=total, limit=limit, offset=offset, problems=rows)


# Declared before /problems/{problem_id} so "facets" is not read as an id.
@router.get("/problems/facets", response_model=FacetsResponse)
def problem_facets() -> FacetsResponse:
    """Every browse axis with its counts — one request for the whole nav."""
    return FacetsResponse(**database_service.facets())


@router.get("/problems/{problem_id}", response_model=ProblemDetail)
def get_problem(problem_id: str) -> ProblemDetail:
    """Accepts a UUID or a slug, so /problems/two-sum works."""
    row = database_service.get_problem(problem_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No problem matching '{problem_id}'")
    return ProblemDetail(**row, runnable_languages=_runnable(row),
                         **_solvability(row))


# LeetCode's own tags, so this is not our inference about what a problem is.
# A `Database` problem is answered with a query and a `Design` problem by
# implementing a class the judge then calls a sequence of methods on. Neither is
# a program that reads stdin, and neither has a harness.
_CANNOT_RUN = {
    "Database": "The answer to this one is a SQL query, and Memoize runs programs.",
    "Design": "This is a class-design problem: the judge builds your class and "
              "calls a sequence of methods on it, which Memoize cannot express yet.",
}


def _solvability(row: dict) -> dict:
    """Whether this problem can be attempted here, and if not, why.

    Only meaningful for a problem with no stored cases. A stdin problem with no
    cases generates them on the first run, which is fine for an ordinary
    algorithm question and meaningless for these two kinds -- there, generating
    would invent an input format for a problem that has none, and then judge
    somebody against it.
    """
    if row.get("test_case_count"):
        return {"solvable": True, "unsolvable_reason": None}
    for tag, reason in _CANNOT_RUN.items():
        if tag in (row.get("topics") or []):
            return {"solvable": False, "unsolvable_reason": reason}
    return {"solvable": True, "unsolvable_reason": None}


def _runnable(row: dict) -> list[str]:
    """Languages this problem can actually be solved in.

    A functional problem needs both a starter for the language and a harness
    that can express its types, so the list is usually shorter than the eleven
    we can execute. Offering a language that answers "not available yet" the
    moment you press Run is worse than not offering it.
    """
    from app import harness
    from app.languages import LANGUAGES

    if row.get("exec_mode") != "functional":
        return [lang.id for lang in LANGUAGES]

    snippets = row.get("code_snippets") or {}
    return [lang.id for lang in LANGUAGES
            if lang.id in snippets and harness.supports(lang.id, row.get("signature"))]
