"""Accounts.

These hit the real database, like the rest of the suite. Every test mints its
own address so runs do not collide.

The cases worth having are the security ones — an enumeration oracle and a
replayable reset link are not the kind of bug a passing happy path reveals.
"""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app import email as mailer
from app.main import app

PASSWORD = "hunter2hunter2"


@pytest.fixture
def sent(monkeypatch):
    """Capture mail instead of sending it, and hand back the outbox."""
    box = []
    monkeypatch.setattr(mailer, "send",
                        lambda to, subject, body: (box.append((to, subject, body)), True)[1])
    return box


@pytest.fixture
def client():
    return TestClient(app, headers={"X-Session-Id": str(uuid.uuid4())})


def fresh_email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def token_in(mail) -> str:
    return re.search(r"token=([\w.\-_]+)", mail[2]).group(1)


# ------------------------------------------------------------------ the basics

def test_signup_signs_you_in_and_never_returns_the_hash(client, sent):
    r = client.post("/api/auth/signup", json={"email": fresh_email(), "password": PASSWORD})
    assert r.status_code == 200
    assert "password_hash" not in r.text
    assert client.get("/api/auth/me").json()["user"] is not None


def test_signed_out_is_a_200_not_a_401(client):
    """Most visitors are signed out; a page that treats an error as normal will
    eventually treat a real error as normal too."""
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["user"] is None


def test_email_is_case_insensitive(client, sent):
    email = fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    client.post("/api/auth/signout")
    assert client.post("/api/auth/signin",
                       json={"email": email.upper(), "password": PASSWORD}).status_code == 200


def test_signout_revokes_the_session_server_side(client, sent):
    """Clearing the cookie alone would leave a token that still works."""
    client.post("/api/auth/signup", json={"email": fresh_email(), "password": PASSWORD})
    token = client.cookies["memoize_session"]
    client.post("/api/auth/signout")

    stolen = TestClient(app)
    stolen.cookies.set("memoize_session", token)
    assert stolen.get("/api/auth/me").json()["user"] is None


# ------------------------------------------------------------- not an oracle

def test_a_wrong_password_and_an_unknown_account_are_indistinguishable(client, sent):
    email = fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    client.post("/api/auth/signout")

    wrong = client.post("/api/auth/signin", json={"email": email, "password": "notitnotit"})
    missing = client.post("/api/auth/signin", json={"email": fresh_email(), "password": "notitnotit"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_forgot_password_says_the_same_thing_for_an_unknown_address(client, sent):
    known = fresh_email()
    client.post("/api/auth/signup", json={"email": known, "password": PASSWORD})
    sent.clear()

    a = client.post("/api/auth/forgot-password", json={"email": known})
    b = client.post("/api/auth/forgot-password", json={"email": fresh_email()})
    assert a.json() == b.json()
    assert len(sent) == 1, "only the real address is mailed"


# --------------------------------------------------------------- email links

def test_a_reset_link_works_once(client, sent):
    """Single-use without a table: the token pins `password_changed_at`, and
    using it changes the password."""
    email = fresh_email()
    client.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
    client.post("/api/auth/signout")
    sent.clear()

    client.post("/api/auth/forgot-password", json={"email": email})
    token = token_in(sent[-1])

    assert client.post("/api/auth/reset-password",
                       json={"token": token, "password": "brandnewpass1"}).status_code == 200
    replayed = client.post("/api/auth/reset-password",
                           json={"token": token, "password": "thirdpassword1"})
    assert replayed.status_code == 400

    client.post("/api/auth/signout")
    assert client.post("/api/auth/signin", json={"email": email, "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/signin",
                       json={"email": email, "password": "brandnewpass1"}).status_code == 200


def test_a_forged_link_is_refused(client):
    assert client.post("/api/auth/verify-email", json={"token": "not-a-real-token"}).status_code == 400


def test_verifying_marks_the_address(client, sent):
    client.post("/api/auth/signup", json={"email": fresh_email(), "password": PASSWORD})
    assert client.get("/api/auth/me").json()["user"]["email_verified"] is False
    r = client.post("/api/auth/verify-email", json={"token": token_in(sent[-1])})
    assert r.json()["email_verified"] is True


# ------------------------------------------------------------- the guest limit

def test_a_guest_gets_two_problems_then_is_asked_to_sign_in(client, sent):
    """The limit is on distinct problems, so iterating on one costs nothing."""
    from app.config import GUEST_PROBLEM_LIMIT

    solved = "class Solution:\n    def twoSum(self, nums, target): return [0, 1]\n"
    assert client.get("/api/auth/me").json()["guest_runs_left"] == GUEST_PROBLEM_LIMIT

    for slug in ("two-sum", "3sum"):
        r = client.post("/api/verify", json={"problem_id": slug, "code": solved,
                                         "language": "python", "kind": "run"}).json()
        assert not r["requires_sign_in"]

    blocked = client.post("/api/verify", json={"problem_id": "valid-parentheses", "code": solved,
                                           "language": "python", "kind": "run"}).json()
    assert blocked["requires_sign_in"] and blocked["total"] == 0

    again = client.post("/api/verify", json={"problem_id": "two-sum", "code": solved,
                                         "language": "python", "kind": "run"}).json()
    assert not again["requires_sign_in"], "a problem already started stays free"

    client.post("/api/auth/signup", json={"email": fresh_email(), "password": PASSWORD})
    after = client.post("/api/verify", json={"problem_id": "valid-parentheses", "code": solved,
                                         "language": "python", "kind": "run"}).json()
    assert not after["requires_sign_in"]


def test_signing_in_claims_the_anonymous_work(client, sent):
    """The reason `session_id` was stored before accounts existed (§20b)."""
    code = "class Solution:\n    def twoSum(self, nums, target): return [0, 1]\n"
    client.post("/api/verify", json={"problem_id": "two-sum", "code": code,
                                 "language": "python", "kind": "run"})

    r = client.post("/api/auth/signup", json={"email": fresh_email(), "password": PASSWORD})
    assert r.json()["claimed"]["submissions"] >= 1

    progress = client.get("/api/progress").json()
    assert "two-sum" in progress["solved"] + progress["attempted"]


def test_progress_follows_the_account_across_browsers(client, sent):
    code = "class Solution:\n    def twoSum(self, nums, target): return [0, 1]\n"
    client.post("/api/verify", json={"problem_id": "two-sum", "code": code,
                                 "language": "python", "kind": "run"})
    client.post("/api/auth/signup", json={"email": fresh_email(), "password": PASSWORD})

    other_browser = TestClient(app, headers={"X-Session-Id": str(uuid.uuid4())})
    other_browser.cookies.set("memoize_session", client.cookies["memoize_session"])
    seen = other_browser.get("/api/progress").json()
    assert "two-sum" in seen["solved"] + seen["attempted"]


# --------------------------------------------------------------------- oauth

def test_an_unconfigured_provider_says_so_rather_than_500ing(client):
    r = client.get("/api/auth/github/start", follow_redirects=False)
    assert r.status_code == 503


def test_a_failed_callback_lands_in_the_app_not_on_raw_json(client):
    """This URL is in the address bar, so a JSON error object is the worst
    thing a person could be shown."""
    r = client.get("/api/auth/github/callback?error=access_denied", follow_redirects=False)
    assert r.status_code == 302
    assert "/signin?error=" in r.headers["location"]


def test_state_must_be_ours(client):
    r = client.get("/api/auth/github/callback?code=x&state=forged", follow_redirects=False)
    assert r.status_code == 302
    assert "/signin?error=" in r.headers["location"]
