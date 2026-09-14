"""Thin client around the Canvas REST API for pulling outstanding work.

Uses four endpoints:
  - /api/v1/courses                        -> which courses count as "currently enrolled"
  - /api/v1/users/self/favorites/courses   -> which of those are starred
  - /api/v1/planner/items                   -> upcoming assignments/quizzes/discussions (due today or later)
  - /api/v1/users/self/missing_submissions -> already-overdue, ungraded work

All are paginated via the standard Canvas `Link` response header.
"""
from datetime import datetime, timezone
from typing import List, Optional, Set
from urllib.parse import urljoin

import requests

from .models import Assignment


class CanvasClientError(Exception):
    """Raised when the Canvas API can't be reached or rejects the request."""


class CanvasClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_token}"})

    def get_active_course_ids(self) -> Set[int]:
        """Course ids for enrollments that are currently active (excludes completed/concluded courses)."""
        url = f"{self.base_url}/api/v1/courses"
        params = {"enrollment_state": "active", "per_page": 100}
        return {item["id"] for item in self._paginate(url, params)}

    def get_favorite_course_ids(self) -> Set[int]:
        """Course ids the user has starred in Canvas."""
        url = f"{self.base_url}/api/v1/users/self/favorites/courses"
        params = {"per_page": 100}
        return {item["id"] for item in self._paginate(url, params)}

    def get_upcoming_assignments(
        self, start_date: Optional[datetime] = None, allowed_course_ids: Optional[Set[int]] = None
    ) -> List[Assignment]:
        """Planner items with a plannable date today or later, excluding anything already submitted/excused.

        `allowed_course_ids`, if given, drops items belonging to any other course. Items with no
        associated course (e.g. personal planner notes) are always kept.
        """
        start_date = start_date or datetime.now(timezone.utc)
        url = f"{self.base_url}/api/v1/planner/items"
        params = {
            "start_date": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "include[]": "submission",
            "per_page": 50,
        }

        assignments = []
        for item in self._paginate(url, params):
            if not self._course_allowed(item.get("course_id"), allowed_course_ids):
                continue
            assignment = self._parse_planner_item(item)
            if assignment is not None:
                assignments.append(assignment)
        return assignments

    def get_missing_submissions(self, allowed_course_ids: Optional[Set[int]] = None) -> List[Assignment]:
        """Assignments already past due with no submission — surfaced separately as 'overdue'."""
        url = f"{self.base_url}/api/v1/users/self/missing_submissions"
        params = {"include[]": "course", "per_page": 50}

        assignments = []
        for item in self._paginate(url, params):
            if not self._course_allowed(item.get("course_id"), allowed_course_ids):
                continue
            due_at = self._parse_datetime(item.get("due_at"))
            course = (item.get("course") or {}).get("name") or f"Course {item.get('course_id', '?')}"
            assignments.append(
                Assignment(
                    title=item.get("name", "Assignment"),
                    course=course,
                    due_at=due_at,
                    url=self._absolute_url(item.get("html_url")),
                    submitted=False,
                )
            )
        return assignments

    @staticmethod
    def _course_allowed(course_id: Optional[int], allowed_course_ids: Optional[Set[int]]) -> bool:
        if allowed_course_ids is None or course_id is None:
            return True
        return course_id in allowed_course_ids

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

    def _parse_planner_item(self, item: dict) -> Optional[Assignment]:
        plannable = item.get("plannable") or {}
        submission = item.get("submissions")
        submitted = isinstance(submission, dict) and (submission.get("submitted") or submission.get("excused"))
        if submitted:
            return None

        due_at = self._parse_datetime(item.get("plannable_date") or plannable.get("due_at"))
        title = plannable.get("title") or item.get("plannable_type", "Item")
        course = item.get("context_name") or "Unknown course"

        return Assignment(
            title=title, course=course, due_at=due_at, url=self._absolute_url(item.get("html_url")), submitted=False
        )

    def _absolute_url(self, path: Optional[str]) -> Optional[str]:
        """Canvas's `html_url` fields are relative paths (e.g. "/courses/1/assignments/2") —
        resolve them against the Canvas host so links actually work outside a browser tab
        that's already on that domain (e.g. in an email)."""
        if not path:
            return None
        return urljoin(self.base_url, path)

    @staticmethod
    def _parse_datetime(raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
