"""Request/response models for the account endpoints."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(default="", max_length=80)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=200)


class VerifyEmailRequest(BaseModel):
    token: str


class PublicUser(BaseModel):
    """What the browser is allowed to know. Never carries the password hash."""

    id: str
    email: str
    email_verified: bool
    display_name: str
    avatar_url: Optional[str] = None
    # Whether this account can sign in with a password at all — an OAuth-only
    # account has none, and the UI has to offer "set a password" instead of
    # "change password".
    has_password: bool = False
    providers: List[str] = Field(default_factory=list)


class Claimed(BaseModel):
    """What signing in pulled across from the anonymous session."""

    submissions: int = 0
    contributions: int = 0
    problems: int = 0


class AuthResponse(BaseModel):
    user: PublicUser
    claimed: Claimed = Field(default_factory=Claimed)


class MeResponse(BaseModel):
    """Deliberately 200-with-null rather than 401 when signed out.

    Signed out is the normal state for most visitors, and a page that has to
    treat an error as "fine, carry on" is a page that will eventually treat a
    real error as fine too.
    """

    user: Optional[PublicUser] = None
    # Distinct problems a signed-out visitor may still run, so the editor can
    # warn before the wall rather than at it. Null once signed in.
    guest_runs_left: Optional[int] = None
