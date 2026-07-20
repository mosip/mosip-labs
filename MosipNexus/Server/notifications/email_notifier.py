"""
Email Notifier.

Sends notifications to the MOSIP team in three scenarios:
  1. Unanswered   — question not found in docs, community, or web (user-triggered).
  2. Low confidence — AI answered but is not confident; expert can do better (auto).
  3. User requested — user explicitly clicked "Ask MOSIP Expert" (user-triggered).

Uses Python's built-in smtplib — no additional packages required.
Configure SMTP credentials in Server/.env (see Server/.env.example).
"""

from __future__ import annotations

import logging
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    NOTIFY_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER,
)

logger = logging.getLogger("nexus.notify")

# ── Internal helpers ───────────────────────────────────────────────────────────

def _is_configured() -> bool:
    return all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL])


def _send(subject: str, body: str, reply_to: str = "") -> tuple[bool, str]:
    """Send an email via configured SMTP server."""
    msg = MIMEMultipart("alternative")
    msg["From"]    = SMTP_USER
    msg["To"]      = NOTIFY_EMAIL
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(body, "plain"))

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        logger.info("Email sent to=%s subject=%r", NOTIFY_EMAIL, subject[:80])
        return True, f"Notification sent to {NOTIFY_EMAIL}."
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for user=%s", SMTP_USER)
        return False, "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env."
    except smtplib.SMTPException as e:
        logger.exception("SMTP error")
        return False, f"SMTP error: {e}"
    except Exception as e:
        logger.exception("Failed to send email")
        return False, f"Failed to send email: {e}"


def _format_body(question: str, language: str, reason_block: str, user_email: str = "") -> str:
    timestamp  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    reply_line = f"User email (for follow-up): {user_email}" if user_email else "User email: not provided"
    return (
        f"{reason_block}\n\n"
        f"{'━' * 42}\n"
        f"Question\n"
        f"{'━' * 42}\n"
        f"{question}\n\n"
        f"{'━' * 42}\n"
        f"Details\n"
        f"{'━' * 42}\n"
        f"Language  : {language}\n"
        f"Timestamp : {timestamp}\n"
        f"{reply_line}\n\n"
        f"{'━' * 42}\n"
        f"Sent automatically by MOSIP Nexus.\n"
        f"{'━' * 42}"
    )


def _short_subject(tag: str, question: str) -> str:
    q = question[:80] + ("..." if len(question) > 80 else "")
    return f"[MOSIP Nexus] {tag}: {q}"


# ── Public API ─────────────────────────────────────────────────────────────────

def send_unanswered_notification(
    question: str,
    language: str = "English",
    user_email: str = "",
) -> tuple[bool, str]:
    """Notify team when no answer was found in MOSIP sources or web (user-triggered).

    Args:
        question: The unanswered user question.
        language: Language the user was using.
        user_email: Optional reply-to address for follow-up.

    Returns:
        ``(ok, message)`` — ``ok`` is False when SMTP is not configured or send fails.
    """
    if not _is_configured():
        return False, "Email notification is not configured (check SMTP settings in .env)."

    reason = (
        "A question was asked on MOSIP Nexus that could not be answered\n"
        "from MOSIP documentation, community forum, or web search.\n"
        "Please consider adding this topic to the MOSIP knowledge base."
    )
    body    = _format_body(question, language, reason, user_email)
    subject = _short_subject("Unanswered question", question)
    logger.info("Queue unanswered notification lang=%s q_len=%d", language, len(question))
    return _send(subject, body, reply_to=user_email)


def send_low_confidence_notification(
    question: str,
    language: str = "English",
    source_type: str = "",
) -> tuple[bool, str]:
    """Auto-notify team when AI answered but with low confidence (automatic).

    Called silently by the app — the user does not need to click anything.

    Args:
        question: The user question that received a low-confidence answer.
        language: Response language.
        source_type: RAG ``source_type`` label for the email body.

    Returns:
        ``(ok, message)``.
    """
    if not _is_configured():
        return False, "Email not configured."

    source_label = {
        "mosip_docs": "MOSIP documentation",
        "community":  "community forum",
        "mixed":      "MOSIP documentation and community forum",
        "web":        "external web sources",
    }.get(source_type, "available sources")

    reason = (
        f"MOSIP Nexus provided an answer from {source_label}, but the AI confidence\n"
        f"was LOW — the retrieved content may not fully address the question.\n"
        f"A MOSIP expert can provide a more accurate and complete response.\n\n"
        f"[This notification was sent automatically — no user action was needed.]"
    )
    body    = _format_body(question, language, reason)
    subject = _short_subject("Low-confidence answer — expert review needed", question)
    logger.info(
        "Queue low-confidence notification source_type=%s lang=%s",
        source_type,
        language,
    )
    return _send(subject, body)


def send_job_failure_alert(job_name: str, error: str = "") -> tuple[bool, str]:
    """Notify team when a background job (e.g. nexus-updater CronJob) fails.

    Args:
        job_name: Human-readable job identifier (e.g. "nexus-updater").
        error:    Optional error message or traceback excerpt.

    Returns:
        ``(ok, message)``.
    """
    if not _is_configured():
        return False, "Email notification is not configured (check SMTP settings in .env)."

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = (
        f"The Nexus background job '{job_name}' failed at {timestamp}.\n\n"
        f"{'━' * 42}\n"
        f"{error[:2000] if error else 'No error details captured.'}\n"
        f"{'━' * 42}\n\n"
        f"Action: check logs with:\n"
        f"  kubectl logs -n mosip-nexus job/{job_name} --previous\n"
        f"  kubectl get jobs -n mosip-nexus\n"
    )
    subject = f"[Nexus] Job failure: {job_name} ({timestamp})"
    return _send(subject, body)


def send_expert_request_notification(
    question: str,
    language: str = "English",
    user_email: str = "",
    context: str = "",
) -> tuple[bool, str]:
    """Notify team when user explicitly requests a MOSIP expert answer.

    Args:
        question: The question to escalate.
        language: Response language.
        user_email: User contact for Reply-To.
        context: Optional snippet of the AI answer for the expert.

    Returns:
        ``(ok, message)``.
    """
    if not _is_configured():
        return False, "Email notification is not configured (check SMTP settings in .env)."

    ctx_block = f"\nAI answer context: {context[:300]}..." if context else ""
    reason = (
        f"A user has requested a response from a MOSIP expert.\n"
        f"The AI provided an answer, but the user would like an authoritative response.{ctx_block}"
    )
    body    = _format_body(question, language, reason, user_email)
    subject = _short_subject("Expert response requested", question)
    return _send(subject, body, reply_to=user_email)
