#!/usr/bin/env python3
"""Daily homework reminder: fetches outstanding Canvas work and emails a prioritized digest.

Usage:
    python main.py            # fetch + send the email
    python main.py --dry-run  # fetch + print the digest instead of sending
"""
import argparse
import os
import sys
from datetime import date

from dotenv import load_dotenv

from src.aggregator import bucket_assignments
from src.canvas_client import CanvasClient, CanvasClientError
from src.emailer import render_email, send_email


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print the digest instead of emailing it.")
    args = parser.parse_args()

    load_dotenv()

    base_url = os.environ.get("CANVAS_BASE_URL")
    token = os.environ.get("CANVAS_API_TOKEN")
    if not base_url or not token:
        print("Missing CANVAS_BASE_URL or CANVAS_API_TOKEN in the environment (see .env.example).", file=sys.stderr)
        sys.exit(1)

    client = CanvasClient(base_url, token)
    try:
        active_ids = client.get_active_course_ids()
        favorite_ids = client.get_favorite_course_ids() & active_ids
        if favorite_ids:
            allowed_ids = favorite_ids
        else:
            allowed_ids = active_ids
            print(
                "No starred courses found in Canvas — showing all currently-enrolled courses instead. "
                "Star your current courses in Canvas to narrow the digest down.",
                file=sys.stderr,
            )

        assignments = client.get_upcoming_assignments(allowed_course_ids=allowed_ids)
        assignments += client.get_missing_submissions(allowed_course_ids=allowed_ids)
    except CanvasClientError as e:
        print(f"Canvas error: {e}", file=sys.stderr)
        sys.exit(1)

    overdue, upcoming, no_due_date = bucket_assignments(assignments)

    subject = f"\U0001F4DA Homework digest — {date.today():%A, %b %d}"
    if overdue:
        subject += f" ({len(overdue)} overdue)"

    html_body, text_body = render_email(overdue, upcoming, no_due_date)

    if args.dry_run:
        print(subject)
        print("=" * len(subject))
        print(text_body)
        return

    sender = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("RECIPIENT_EMAIL") or sender
    if not sender or not app_password:
        print("Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in the environment (see .env.example).", file=sys.stderr)
        sys.exit(1)

    send_email(subject, html_body, text_body, sender=sender, app_password=app_password, recipient=recipient)
    print(f"Email sent to {recipient}.")


if __name__ == "__main__":
    main()
