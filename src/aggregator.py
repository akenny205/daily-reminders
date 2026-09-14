"""Sorts and buckets assignments so the digest reads soonest-due first."""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from .models import Assignment

DEFAULT_LOOKAHEAD_DAYS = 14


def bucket_assignments(
    assignments: List[Assignment], lookahead_days: int = DEFAULT_LOOKAHEAD_DAYS
) -> Tuple[List[Assignment], List[Assignment], List[Assignment]]:
    """Returns (overdue, upcoming, no_due_date), each already sorted for display.

    - overdue: due in the past, not submitted — most urgent, meant to be shown first.
    - upcoming: due between now and `lookahead_days` from now, ascending by due date.
    - no_due_date: no due date at all, shown last.
    """
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=lookahead_days)

    overdue, upcoming, no_due_date = [], [], []
    for a in assignments:
        if a.due_at is None:
            no_due_date.append(a)
        elif a.due_at < now:
            overdue.append(a)
        elif a.due_at <= cutoff:
            upcoming.append(a)
        # else: further out than the lookahead window — omitted from the digest

    overdue.sort(key=lambda a: a.due_at)
    upcoming.sort(key=lambda a: a.due_at)
    no_due_date.sort(key=lambda a: a.title.lower())

    return overdue, upcoming, no_due_date
