"""Verification routing. Does not call Judge0 — the judge client is stubbed."""

from app.schemas.verify import VerifyResponse


def test_unknown_problem_is_404(client):
    r = client.post("/verify", json={"problem_id": "nope", "code": "print(1)", "language": "python"})
    assert r.status_code == 404


def test_empty_code_is_422(client, any_slug):
    r = client.post("/verify", json={"problem_id": any_slug, "code": "  ", "language": "python"})
    assert r.status_code == 422


def test_problem_without_tests_degrades(client, monkeypatch):
    """No test cases is a state to report, not an error."""
    from app.services import database_service

    monkeypatch.setattr(database_service, "get_test_cases", lambda *a, **k: [])
    rows = client.get("/problems", params={"limit": 1}).json()["problems"]
    r = client.post("/verify", json={"problem_id": rows[0]["slug"],
                                     "code": "print(1)", "language": "python"})
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert "No test cases" in r.json()["status"]


def test_judge_failure_does_not_500(client, monkeypatch, any_slug):
    """Judge0 is the flakiest dependency; it must degrade, not crash."""
    from app.services import database_service, judge_service

    monkeypatch.setattr(database_service, "get_test_cases",
                        lambda *a, **k: [{"input": "1", "expected_output": "1"}])
    monkeypatch.setattr(judge_service, "run_submission",
                        lambda req, cases, problem=None: VerifyResponse(
                            status="Judge0 unavailable: ConnectError",
                            passed=0, total=len(cases)))
    r = client.post("/verify", json={"problem_id": any_slug,
                                     "code": "print(1)", "language": "python"})
    assert r.status_code == 200
    assert "unavailable" in r.json()["status"]


def test_unsupported_language_is_reported_not_raised():
    """An unknown language is a message, not an exception.

    Uses a language that will never exist rather than a real one — this test
    previously named "cpp", and started failing the day C++ was supported,
    which is a test asserting the absence of a feature rather than a behaviour.
    """
    from app.schemas.verify import VerifyRequest
    from app.services import judge_service

    out = judge_service.run_submission(
        VerifyRequest(problem_id="x", code="whatever", language="brainfuck"),
        [{"input": "1", "expected_output": "1"}],
    )
    assert "Unsupported language" in out.status
    assert out.passed == 0


def test_every_language_has_a_judge0_id_and_starter():
    """A language in the picker that cannot run is worse than one absent."""
    from app.languages import LANGUAGES

    assert len(LANGUAGES) >= 2, "multi-language support is the point"
    ids = [l.judge0_id for l in LANGUAGES]
    assert len(set(ids)) == len(ids), "two languages share a Judge0 id"
    for lang in LANGUAGES:
        assert lang.judge0_id > 0
        assert lang.starter.strip(), f"{lang.id} has no starter"
        assert lang.monaco, f"{lang.id} has no Monaco mode"


def test_java_starter_declares_class_main():
    """Judge0 compiles the file as Main.java, so the class must be Main."""
    from app.languages import BY_ID

    assert "public class Main" in BY_ID["java"].starter


def test_languages_endpoint_lists_starters(client):
    body = client.get("/languages").json()
    assert body, "no languages exposed"
    assert {"id", "label", "monaco", "starter"} <= set(body[0])
    assert any(l["id"] == "python" for l in body)


def test_progress_is_empty_without_a_session(client):
    """An unidentified caller is a supported state, not an error."""
    body = client.get("/progress").json()
    assert body == {"solved": [], "attempted": [], "runs": 0, "solved_count": 0}


def test_progress_ignores_a_malformed_session_header(client):
    """A bad header degrades to anonymous rather than 400ing the request."""
    r = client.get("/progress", headers={"X-Session-Id": "not-a-uuid"})
    assert r.status_code == 200
    assert r.json()["solved"] == []


def test_verify_defaults_to_a_run(client):
    """kind is optional, and the safe default is the one that cannot complete
    a problem by accident."""
    from app.schemas.verify import VerifyRequest

    assert VerifyRequest(problem_id="x", code="y").kind == "run"
    assert VerifyRequest(problem_id="x", code="y").language == "python"


def test_a_passing_run_does_not_complete_a_problem():
    """The rule the whole Run/Submit split exists for.

    A run that happens to pass is a trial. Treating it as completion would take
    the decision away from the user and mark problems solved that they were
    still experimenting with. Only an accepted *submit* counts.
    """
    from uuid import uuid4

    from app.schemas.verify import VerifyResponse
    from app.services import database_service as db

    session = uuid4()
    passing = VerifyResponse(status="Accepted", passed=2, total=2, all_passed=True)

    try:
        db.save_submission("triangle", "code", "python", passing,
                           kind="run", session_id=session)
        after_run = db.problem_progress(session, "triangle")
        assert after_run["runs"] == 1
        assert after_run["solved"] is False, "a passing run must not complete a problem"

        db.save_submission("triangle", "code", "python", passing,
                           kind="submit", session_id=session)
        after_submit = db.problem_progress(session, "triangle")
        assert after_submit["solved"] is True
        assert after_submit["runs"] == 1, "a submit is not also a run"
        assert after_submit["submissions"] == 1

        assert "triangle" in db.session_progress(session)["solved"]
    finally:
        db.execute("DELETE FROM submissions WHERE session_id = %s", [session])


def test_a_failing_submit_does_not_complete_a_problem():
    from uuid import uuid4

    from app.schemas.verify import VerifyResponse
    from app.services import database_service as db

    session = uuid4()
    failing = VerifyResponse(status="Wrong Answer", passed=1, total=2)
    try:
        db.save_submission("triangle", "code", "python", failing,
                           kind="submit", session_id=session)
        assert db.problem_progress(session, "triangle")["solved"] is False
    finally:
        db.execute("DELETE FROM submissions WHERE session_id = %s", [session])


def test_sessions_do_not_see_each_others_progress():
    from uuid import uuid4

    from app.schemas.verify import VerifyResponse
    from app.services import database_service as db

    mine, theirs = uuid4(), uuid4()
    passing = VerifyResponse(status="Accepted", passed=2, total=2, all_passed=True)
    try:
        db.save_submission("triangle", "code", "python", passing,
                           kind="submit", session_id=mine)
        assert db.session_progress(mine)["solved"] == ["triangle"]
        assert db.session_progress(theirs)["solved"] == []
    finally:
        db.execute("DELETE FROM submissions WHERE session_id IN (%s, %s)", [mine, theirs])


# ------------------------------------------------------------- input formats
#
# Solutions here are whole programs reading stdin, so a test case only means
# anything under one input format. Two reconstructions of a problem routinely
# pick different ones, and storage used to merge on `input` alone: two-sum
# accumulated nine cases across incompatible shapes and became unsolvable.

def test_test_cases_do_not_accumulate_across_formats():
    """The regression that made two-sum unsolvable.

    A second writer's cases must not join the first writer's. They are only
    meaningful as a set: merged, no single program can pass them all.
    """
    from ai.models.problem_genome import TestCase
    from app.services import database_service as db

    slug = "triangle"
    before = db.get_test_cases(slug, limit=50)
    first = [TestCase(input="1\n5", expected_output="5")]
    second = [TestCase(input="5", expected_output="5")]  # a different shape

    stored_ids = []
    try:
        db.execute("DELETE FROM test_cases WHERE problem_id = "
                   "(SELECT id FROM problems WHERE slug = %s)", (slug,))
        assert db.save_test_cases(slug, first) == 1
        assert db.save_test_cases(slug, second) == 0, \
            "a later writer must not add cases in its own format"
        assert [c["input"] for c in db.get_test_cases(slug, limit=50)] == ["1\n5"]
    finally:
        db.execute("DELETE FROM test_cases WHERE problem_id = "
                   "(SELECT id FROM problems WHERE slug = %s)", (slug,))
        for case in before:
            db.execute("INSERT INTO test_cases (problem_id, input, expected_output) "
                       "SELECT id, %s, %s FROM problems WHERE slug = %s",
                       (case["input"], case["expected_output"], slug))
        stored_ids.clear()


def test_io_format_is_stored_and_never_silently_rewritten():
    """The format the stored cases obey is the one people have been solving
    against, so a later writer may state it but not change it."""
    from ai.models.problem_genome import TestCase
    from app.services import database_service as db

    slug = "unique-paths"
    before = db.query_one("SELECT io_format FROM problems WHERE slug = %s", (slug,))
    try:
        db.execute("UPDATE problems SET io_format = NULL WHERE slug = %s", (slug,))
        db.set_io_format(slug, "Line 1: two integers m and n.")
        db.set_io_format(slug, "Line 1: n. Line 2: m.")
        row = db.query_one("SELECT io_format FROM problems WHERE slug = %s", (slug,))
        assert row["io_format"] == "Line 1: two integers m and n."
        assert db.get_problem(slug)["io_format"] == "Line 1: two integers m and n."
    finally:
        db.execute("UPDATE problems SET io_format = %s WHERE slug = %s",
                   (before["io_format"], slug))


def test_a_stated_format_outranks_the_examples_when_generating():
    """A problem people already solved must not have its format redecided."""
    from ai.models.problem_genome import ReconstructedProblem, WorkedExample
    from ai.verification.test_generator import _format_hint

    problem = ReconstructedProblem(
        title="x", description="y",
        io_format="Line 1: an integer n.",
        examples=[WorkedExample(input="1 2 3", output="6")],
    )
    hint = _format_hint(problem)
    assert "Line 1: an integer n." in hint
    assert "1 2 3" not in hint, "examples must not override a stated format"


def test_a_problem_with_no_format_still_generates_from_examples():
    """The fallback the corpus mostly relies on today."""
    from ai.models.problem_genome import ReconstructedProblem, WorkedExample
    from ai.verification.test_generator import _format_hint

    hint = _format_hint(ReconstructedProblem(
        title="x", description="y",
        examples=[WorkedExample(input="1 2 3", output="6")]))
    assert "1 2 3" in hint
