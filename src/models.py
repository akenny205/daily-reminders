"""Shared data model for a piece of homework, regardless of source."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Assignment:
    title: str
    course: str
    due_at: Optional[datetime]  # None means no due date was set
    url: Optional[str] = None
    submitted: bool = False
