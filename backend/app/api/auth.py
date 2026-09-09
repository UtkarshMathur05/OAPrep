"""Account endpoints.

Two shapes here, on purpose:

* the JSON endpoints the SPA calls (`/auth/signup`, `/auth/signin`, `/auth/me`, …)
* the two **browser-navigation** endpoints OAuth needs — `/auth/{provider}/start`
  and `/auth/{provider}/callback`. These are full-page redirects, not fetches,
  because the provider redirects the browser back to us. They end by bouncing to
  the app, never by returning JSON a user would see as raw text.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.config import GUEST_PROBLEM_LIMIT, PUBLIC_APP_URL
from app.identity import current_principal, current_session
from app.schemas.auth import (
    AuthResponse,
    Claimed,
    ForgotPasswordRequest,
    MeResponse,
    PublicUser,
    ResetPasswordRequest,
    SignInRequest,
    SignUpRequest,
    VerifyEmailRequest,
)
from app.services import auth_service, database_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _finish(request: Request, response: Response, user: dict) -> AuthResponse:
    """Start a session and pull the browser's anonymous history into the account."""
    auth_service.start_session(response, user["id"], request.headers.get("user-agent", ""))
    claimed = auth_service.claim(user["id"], current_session(request))
    return AuthResponse(user=PublicUser(**auth_service.public_user(user)),
                        claimed=Claimed(**claimed))


@router.post("/signup", response_model=AuthResponse)
def signup(req: SignUpRequest, request: Request, response: Response) -> AuthResponse:
    user = auth_service.sign_up(str(req.email), req.password, req.display_name)
    return _finish(request, response, user)


@router.post("/signin", response_model=AuthResponse)
def signin(req: SignInRequest, request: Request, response: Response) -> AuthResponse:
    user = auth_service.sign_in(str(req.email), req.password)
    return _finish(request, response, user)


@router.post("/signout")
def signout(request: Request, response: Response) -> dict:
    auth_service.end_session(request, response)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(request: Request) -> MeResponse:
    """Who the caller is. 200 with a null user when signed out — see the schema."""
    principal = current_principal(request)
    if principal.user_id:
        row = auth_service.get_user(principal.user_id)
        if row:
            return MeResponse(user=PublicUser(**auth_service.public_user(row)))
    used = database_service.guest_problems_used(principal.session_id)
    return MeResponse(user=None, guest_runs_left=max(0, GUEST_PROBLEM_LIMIT - used))


# ------------------------------------------------------------ email round trips

@router.post("/verify-email", response_model=PublicUser)
def verify_email(req: VerifyEmailRequest) -> PublicUser:
    return PublicUser(**auth_service.public_user(auth_service.verify_email(req.token)))


@router.post("/resend-verification")
def resend_verification(request: Request) -> dict:
    principal = current_principal(request)
    if principal.user_id:
        user = auth_service.get_user(principal.user_id)
        if user:
            auth_service.send_verification(user)
    # Same answer either way: whether a session is signed in is not something
    # this endpoint needs to reveal, and there is nothing useful to say anyway.
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest) -> dict:
    auth_service.request_password_reset(str(req.email))
    # Always the same, whether or not that address has an account.
    return {"ok": True, "message": "If that address has an account, a reset link is on its way."}


@router.post("/reset-password", response_model=AuthResponse)
def reset_password(req: ResetPasswordRequest, request: Request, response: Response) -> AuthResponse:
    user = auth_service.reset_password(req.token, req.password)
    return _finish(request, response, user)


# --------------------------------------------------------------------- oauth

@router.get("/{provider}/start")
def oauth_start(provider: str, next: str = Query("/")) -> RedirectResponse:
    """Send the browser to the provider. A redirect, not JSON."""
    return RedirectResponse(auth_service.authorize_url(provider, next), status_code=302)


@router.get("/{provider}/callback")
def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Where the provider sends the browser back.

    Every exit is a redirect into the app, including the failures: this URL is
    displayed in the address bar, so a raw JSON error object is the worst thing
    a person could be shown here. Problems land on /signin with a message.
    """
    def back(path: str) -> RedirectResponse:
        # The session cookie is set on *this* response, before the redirect.
        return RedirectResponse(f"{PUBLIC_APP_URL}{path}", status_code=302)

    def failed(message: str) -> RedirectResponse:
        from urllib.parse import quote
        return back(f"/signin?error={quote(message)}")

    if error:
        return failed("Sign-in was cancelled.")
    if not code or not state:
        return failed("That sign-in link was incomplete. Try again.")

    try:
        next_path = auth_service.read_state(state, provider)
        profile = auth_service.exchange(provider, code)
        user = auth_service.upsert_oauth_user(provider, profile)
    except HTTPException as exc:
        return failed(str(exc.detail))

    response = back(next_path)
    auth_service.start_session(response, user["id"], request.headers.get("user-agent", ""))
    auth_service.claim(user["id"], current_session(request))
    return response
