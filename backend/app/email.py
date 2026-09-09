"""Sending a link to an address.

One seam, four backends, chosen by `EMAIL_PROVIDER`:

    console   print it to the server log     (default — no account, no network)
    resend    HTTPS POST to Resend           (free tier: 3,000/month, needs a domain)
    brevo     HTTPS POST to Brevo            (free tier: 300/day, single sender is enough)
    smtp      any SMTP server                (local use, or a host that permits it)

`brevo` and `smtp` reach the same Brevo account by different roads, and the road
matters: **Render's free instances block outbound traffic to ports 25, 465 and
587**, so an SMTP provider is simply unreachable from a free web service — the
send times out rather than failing loudly. The HTTP API is not blocked. `smtp`
stays because it is right for a laptop and for hosts that allow it.

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
    BREVO_API_KEY,
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
        if EMAIL_PROVIDER == "brevo":
            return _brevo(to, subject, body)
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


def _brevo(to: str, subject: str, body: str) -> bool:
    """Brevo's transactional API. Same account as SMTP, over HTTPS.

    Brevo wants the sender split into name and address rather than one RFC 5322
    string, so EMAIL_FROM is parsed instead of passed through.
    """
    if not BREVO_API_KEY:
        log.warning("EMAIL_PROVIDER=brevo but BREVO_API_KEY is unset")
        return False
    from email.utils import parseaddr

    name, address = parseaddr(EMAIL_FROM)
    if not address:
        log.warning("EMAIL_FROM has no address to send from: %r", EMAIL_FROM)
        return False
    sender = {"email": address}
    if name:
        sender["name"] = name

    r = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_API_KEY, "accept": "application/json"},
        json={"sender": sender, "to": [{"email": to}],
              "subject": subject, "textContent": body},
        timeout=TIMEOUT,
    )
    if r.status_code >= 400:
        # Brevo's own words are more useful than ours: an unverified sender and
        # a bad key are different problems with the same symptom.
        log.warning("brevo rejected the mail: %s %s", r.status_code, r.text[:200])
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
