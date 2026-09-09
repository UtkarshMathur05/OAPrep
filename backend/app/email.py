"""Sending a link to an address.

One seam, three backends, chosen by `EMAIL_PROVIDER`:

    console   print it to the server log     (default — no account, no network)
    resend    HTTPS POST to Resend           (free tier: 3,000/month)
    smtp      any SMTP server                (Brevo, Gmail app password, …)

`console` exists for the same reason `USE_MOCK_AI` does: the whole
verify-your-address and reset-your-password flow has to be testable on a laptop
with no provider account, no domain and no network. It prints the link so you
can click it. It is *not* a silent no-op — a mail that vanishes without trace is
how you ship a reset flow that has never worked.

Sending never raises. An address that cannot be mailed must not fail the
signup that triggered it: the account exists, the link can be re-requested, and
a 500 here would leave the user unable to retry with an address already taken.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.config import (
    EMAIL_FROM,
    EMAIL_PROVIDER,
    RESEND_API_KEY,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)

log = logging.getLogger(__name__)

TIMEOUT = 10.0


def send(to: str, subject: str, body: str) -> bool:
    """Deliver one plain-text mail. Returns whether it went out."""
    try:
        if EMAIL_PROVIDER == "resend":
            return _resend(to, subject, body)
        if EMAIL_PROVIDER == "smtp":
            return _smtp(to, subject, body)
        return _console(to, subject, body)
    except Exception:  # noqa: BLE001 - see the module docstring
        log.warning("could not send %r to %s", subject, to, exc_info=True)
        return False


def _console(to: str, subject: str, body: str) -> bool:
    # Deliberately loud and deliberately at INFO: this is the delivery
    # mechanism in development, so burying it at DEBUG would break the flow.
    log.info(
        "\n--- email (EMAIL_PROVIDER=console, not actually sent) ---\n"
        "to:      %s\nsubject: %s\n\n%s\n"
        "--- end email ---",
        to, subject, body,
    )
    return True


def _resend(to: str, subject: str, body: str) -> bool:
    if not RESEND_API_KEY:
        log.warning("EMAIL_PROVIDER=resend but RESEND_API_KEY is unset")
        return False
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": EMAIL_FROM, "to": [to], "subject": subject, "text": body},
        timeout=TIMEOUT,
    )
    if r.status_code >= 400:
        log.warning("resend rejected the mail: %s %s", r.status_code, r.text[:200])
        return False
    return True


def _smtp(to: str, subject: str, body: str) -> bool:
    if not SMTP_HOST:
        log.warning("EMAIL_PROVIDER=smtp but SMTP_HOST is unset")
        return False
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=TIMEOUT) as s:
        s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASSWORD)
        s.send_message(msg)
    return True
