"""Renders the assignment digest as an email and sends it via the Resend HTTP API.

Plain SMTP sockets don't work from every environment this script might run in (some
sandboxes only proxy HTTP/HTTPS traffic), so delivery goes over a regular HTTPS POST
instead of opening an SMTP connection.
"""
from html import escape
from typing import List, Tuple

import requests

from .models import Assignment

RESEND_API_URL = "https://api.resend.com/emails"

_SECTIONS = [
    ("overdue", "⚠️ Overdue", "#c0392b"),
    ("upcoming", "📌 Upcoming", "#2c3e50"),
    ("no_due_date", "🗒️ No due date", "#7f8c8d"),
]


def _format_due(a: Assignment) -> str:
    if a.due_at is None:
        return "No due date"
    return a.due_at.astimezone().strftime("%a %b %d, %I:%M %p")


def render_email(
    overdue: List[Assignment], upcoming: List[Assignment], no_due_date: List[Assignment]
) -> Tuple[str, str]:
    """Returns (html_body, text_body)."""
    groups = {"overdue": overdue, "upcoming": upcoming, "no_due_date": no_due_date}
    total = sum(len(v) for v in groups.values())

    if total == 0:
        return "<p>Nothing due — you're all caught up! 🎉</p>", "Nothing due — you're all caught up!"

    html_parts = []
    text_parts = []

    for key, heading, color in _SECTIONS:
        items = groups[key]
        if not items:
            continue

        text_parts.append(heading)
        for a in items:
            text_parts.append(f"  - [{a.course}] {a.title} — {_format_due(a)}")
        text_parts.append("")

        rows = "".join(
            "<tr>"
            f"<td style='padding:6px 10px;color:#555;'>{escape(a.course)}</td>"
            f"<td style='padding:6px 10px;'><a href='{escape(a.url or '#')}'>{escape(a.title)}</a></td>"
            f"<td style='padding:6px 10px;color:#555;white-space:nowrap;'>{_format_due(a)}</td>"
            "</tr>"
            for a in items
        )
        html_parts.append(
            f"<h3 style='color:{color};margin:18px 0 6px;'>{heading}</h3>"
            f"<table style='border-collapse:collapse;width:100%;font-family:sans-serif;font-size:14px;'>{rows}</table>"
        )

    html_body = "".join(html_parts)
    text_body = "\n".join(text_parts).rstrip()
    return html_body, text_body


class EmailSendError(Exception):
    """Raised when the Resend API rejects or fails to send the email."""


def send_email(
    subject: str, html_body: str, text_body: str, *, api_key: str, recipient: str, from_address: str
) -> None:
    resp = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": from_address, "to": [recipient], "subject": subject, "html": html_body, "text": text_body},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise EmailSendError(f"Resend API returned {resp.status_code}: {resp.text}")
