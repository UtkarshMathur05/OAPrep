"""Judge0 client. The frontend never talks to Judge0 directly.

Two execution modes, and Judge0 sees the same thing either way — stdin in,
stdout out. What differs is who writes the parsing.

**functional** (`problems.exec_mode`): the person writes the function the
statement describes. `app.harness` appends a driver that reads one JSON argument
per line, calls their method, and prints the return value; answers are compared
as JSON values, so `[0,1]` and `[0, 1]` are the same answer. Requires a typed
signature, which for corpus problems comes from LeetCode's own `metaData`.

**stdin**: the original contract, still the default. `test_cases.input` is sent
verbatim and stdout is compared after stripping trailing whitespace. Problems
with no signature — class-design questions like LRU Cache, and anything a
harness has no type for — stay here rather than being forced.

Every supported language lives in `app.languages`. In stdin mode adding one
costs a Judge0 id and a starter; in functional mode it also costs a harness,
which is the price of the person not having to write a parser.
"""

from __future__ import annotations

import time

import httpx

from app.config import JUDGE0_API_HOST, JUDGE0_API_KEY, JUDGE0_URL
from app.schemas.verify import TestResult, VerifyRequest, VerifyResponse

from app import harness
from app.languages import BY_ID, DEFAULT, get as get_language

# Kept as a mapping for callers that only need the id. The registry in
# app.languages is the source of truth.
LANGUAGE_IDS = {key: lang.judge0_id for key, lang in BY_ID.items()}

MAX_TEST_CASES = 5
JUDGE0_TIMEOUT_SECONDS = 20.0
POLL_INTERVAL_SECONDS = 0.7
MAX_POLLS = 20

# Judge0 status ids: 1 queued, 2 processing, 3 accepted, 4 wrong answer,
# 5 time limit, 6 compile error, 7-12 runtime error, 13+ internal.
_FINISHED = 2  # anything above this has settled


def _headers() -> dict:
    """RapidAPI needs a key and host; a self-hosted or public CE instance does not."""
    if JUDGE0_API_KEY and JUDGE0_API_HOST:
        return {"X-RapidAPI-Key": JUDGE0_API_KEY, "X-RapidAPI-Host": JUDGE0_API_HOST}
    return {}


def _normalise(text: str | None) -> str:
    """Compare ignoring trailing whitespace, which Judge0 always appends."""
    return (text or "").rstrip()


def run_submission(req: VerifyRequest, test_cases: list[dict],
                   problem: dict | None = None) -> VerifyResponse:
    """Run `req.code` against every test case and aggregate the outcome.

    `problem` carries `exec_mode`, `signature` and `judge_mode`. Omitted, or
    without a signature, the run is a plain stdin one — which is what every
    caller got before functional mode existed.
    """
    language = get_language(req.language)
    if language is None:
        supported = ", ".join(sorted(LANGUAGE_IDS))
        return VerifyResponse(
            status=f"Unsupported language '{req.language}' (supported: {supported})",
            passed=0, total=len(test_cases),
        )
    language_id = language.judge0_id
    if not test_cases:
        return VerifyResponse(status="No test cases", passed=0, total=0)

    cases = test_cases[:MAX_TEST_CASES]
    problem = problem or {}
    functional = (problem.get("exec_mode") == "functional"
                  and harness.supports(req.language, problem.get("signature")))

    if problem.get("exec_mode") == "functional" and not functional:
        # Being explicit beats running their function body as a program and
        # reporting a syntax error they cannot act on.
        return VerifyResponse(
            status=f"{language.label} is not available for this problem yet",
            passed=0, total=len(cases),
        )

    source = (harness.build(req.language, problem["signature"], req.code)
              if functional else req.code)
    submissions = [
        {"language_id": language_id, "source_code": source, "stdin": c["input"]}
        for c in cases
    ]

    try:
        outputs = _run_batch(submissions)
    except httpx.HTTPError as exc:
        # Judge0 is the flakiest dependency; degrade with a message, never a 500.
        return VerifyResponse(
            status=f"Judge0 unavailable: {type(exc).__name__}",
            passed=0, total=len(cases),
        )

    return _aggregate(cases, outputs,
                      functional=functional,
                      judge_mode=problem.get("judge_mode") or "exact")


def run_reference(code: str, inputs: list[str]) -> list[str | None]:
    """Execute `code` against each stdin and return its stdout, or None.

    Used to validate generated test cases: a case is only trustworthy if the
    reference solution actually prints the answer that was claimed for it.
    None means the run failed (compile error, crash, timeout) and the case
    cannot be confirmed.
    """
    if not code.strip() or not inputs:
        return [None] * len(inputs)

    submissions = [
        {"language_id": LANGUAGE_IDS[DEFAULT], "source_code": code, "stdin": stdin}
        for stdin in inputs
    ]
    try:
        rows = _run_batch(submissions)
    except httpx.HTTPError:
        return [None] * len(inputs)

    out: list[str | None] = []
    for row in rows:
        status = (row.get("status") or {}).get("description")
        out.append(_normalise(row.get("stdout")) if status == "Accepted" else None)
    return out


def _run_batch(submissions: list[dict]) -> list[dict]:
    """Submit all cases in one request, then poll until every one has settled."""
    with httpx.Client(timeout=JUDGE0_TIMEOUT_SECONDS, headers=_headers()) as client:
        created = client.post(
            f"{JUDGE0_URL}/submissions/batch",
            params={"base64_encoded": "false"},
            json={"submissions": submissions},
        )
        created.raise_for_status()
        tokens = [row["token"] for row in created.json()]

        for _ in range(MAX_POLLS):
            time.sleep(POLL_INTERVAL_SECONDS)
            got = client.get(
                f"{JUDGE0_URL}/submissions/batch",
                params={"tokens": ",".join(tokens), "base64_encoded": "false"},
            )
            got.raise_for_status()
            rows = got.json()["submissions"]
            if all((r.get("status") or {}).get("id", 0) > _FINISHED for r in rows):
                return rows

        raise httpx.TimeoutException("Judge0 did not settle within the poll budget")


def _aggregate(cases: list[dict], outputs: list[dict], *,
               functional: bool = False,
               judge_mode: str = "exact") -> VerifyResponse:
    """Turn per-case Judge0 rows into one VerifyResponse."""
    results: list[TestResult] = []
    passed = 0
    worst: str | None = None
    total_time = 0.0
    peak_memory = 0

    for index, (case, out) in enumerate(zip(cases, outputs)):
        status = (out.get("status") or {}).get("description", "Unknown")
        actual = _normalise(out.get("stdout"))
        expected = _normalise(case["expected_output"])
        # Judge0 says "Accepted" when the program merely ran; correctness is ours
        # to decide, since we never send it an expected_output.
        if status != "Accepted":
            ok = False
        elif functional:
            # Values, not text: languages space their JSON differently, and a
            # problem may accept any order.
            ok = harness.compare(expected, actual, judge_mode)
        else:
            ok = actual == expected
        passed += ok

        if not ok and worst is None:
            worst = "Wrong Answer" if status == "Accepted" else status

        try:
            total_time += float(out.get("time") or 0)
        except (TypeError, ValueError):
            pass
        peak_memory = max(peak_memory, out.get("memory") or 0)

        results.append(TestResult(
            index=index,
            passed=ok,
            input=case["input"],
            expected_output=expected,
            # Surface stderr/compile output so a failure is diagnosable.
            actual_output=actual or _normalise(
                out.get("stderr") or out.get("compile_output")
            ),
        ))

    return VerifyResponse(
        status="Accepted" if passed == len(cases) else (worst or "Wrong Answer"),
        passed=passed,
        total=len(cases),
        runtime=f"{total_time:.3f}s",
        memory=f"{peak_memory // 1024}MB" if peak_memory else None,
        results=results,
    )
