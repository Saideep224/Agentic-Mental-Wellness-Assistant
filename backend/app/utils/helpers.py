"""
Common helper utilities used across the backend.
"""

import json
from datetime import datetime, timezone, timedelta


def safe_json_parse(text: str, fallback: dict | None = None) -> dict:
    """Parse JSON string safely, returning fallback on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return fallback or {}


def get_ist_time() -> str:
    """Get current time in IST timezone as formatted string."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    return now.strftime("%I:%M %p IST, %B %d %Y")
