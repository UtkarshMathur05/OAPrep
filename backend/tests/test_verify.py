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
                        lambda req, cases: VerifyResponse(
                            status="Judge0 unavailable: ConnectError",
                            passed=0, total=len(cases)))
    r = client.post("/verify", json={"problem_id": any_slug,
                                     "code": "print(1)", "language": "python"})
    assert r.status_code == 200
    assert "unavailable" in r.json()["status"]


def test_unsupported_language_is_reported_not_raised(monkeypatch):
    from app.schemas.verify import VerifyRequest
    from app.services import judge_service

    out = judge_service.run_submission(
        VerifyRequest(problem_id="x", code="int main(){}", language="cpp"),
        [{"input": "1", "expected_output": "1"}],
    )
    assert "Unsupported language" in out.status
    assert out.passed == 0
