"""Renders the assignment digest as an email and sends it over Gmail SMTP."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from typing import List, Tuple

from .models import Assignment

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


def send_email(subject: str, html_body: str, text_body: str, *, sender: str, app_password: str, recipient: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.starttls()
        server.login(sender, app_password)
        server.sendmail(sender, [recipient], msg.as_string())
