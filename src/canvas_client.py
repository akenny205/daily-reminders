"""Thin client around the Canvas REST API for pulling outstanding work.

Uses two endpoints:
  - /api/v1/planner/items       -> upcoming assignments/quizzes/discussions (due today or later)
  - /api/v1/users/self/missing_submissions -> already-overdue, ungraded work

Both are paginated via the standard Canvas `Link` response header.
"""
from datetime import datetime, timezone
from typing import List, Optional

import requests

from .models import Assignment


class CanvasClientError(Exception):
    """Raised when the Canvas API can't be reached or rejects the request."""


class CanvasClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_token}"})

    def get_upcoming_assignments(self, start_date: Optional[datetime] = None) -> List[Assignment]:
        """Planner items with a plannable date today or later, excluding anything already submitted/excused."""
        start_date = start_date or datetime.now(timezone.utc)
        url = f"{self.base_url}/api/v1/planner/items"
        params = {
            "start_date": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "include[]": "submission",
            "per_page": 50,
        }

        assignments = []
        for item in self._paginate(url, params):
            assignment = self._parse_planner_item(item)
            if assignment is not None:
                assignments.append(assignment)
        return assignments

    def get_missing_submissions(self) -> List[Assignment]:
        """Assignments already past due with no submission — surfaced separately as 'overdue'."""
        url = f"{self.base_url}/api/v1/users/self/missing_submissions"
        params = {"include[]": "course", "per_page": 50}

        assignments = []
        for item in self._paginate(url, params):
            due_at = self._parse_datetime(item.get("due_at"))
            course = (item.get("course") or {}).get("name") or f"Course {item.get('course_id', '?')}"
            assignments.append(
                Assignment(
                    title=item.get("name", "Assignment"),
                    course=course,
                    due_at=due_at,
                    url=item.get("html_url"),
                    submitted=False,
                )
            )
        return assignments

    def _paginate(self, url: str, params: Optional[dict]):
        while url:
            resp = self.session.get(url, params=params)
            if resp.status_code == 401:
                raise CanvasClientError(
                    "Canvas rejected the API token (401 Unauthorized). Check CANVAS_API_TOKEN."
                )
            resp.raise_for_status()
            for item in resp.json():
                yield item
            url = resp.links.get("next", {}).get("url")
            params = None  # the "next" URL already carries the query string

    @staticmethod
    def _parse_planner_item(item: dict) -> Optional[Assignment]:
        plannable = item.get("plannable") or {}
        submission = item.get("submissions")
        submitted = isinstance(submission, dict) and (submission.get("submitted") or submission.get("excused"))
        if submitted:
            return None

        due_at = CanvasClient._parse_datetime(item.get("plannable_date") or plannable.get("due_at"))
        title = plannable.get("title") or item.get("plannable_type", "Item")
        course = item.get("context_name") or "Unknown course"

        return Assignment(title=title, course=course, due_at=due_at, url=item.get("html_url"), submitted=False)

    @staticmethod
    def _parse_datetime(raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
