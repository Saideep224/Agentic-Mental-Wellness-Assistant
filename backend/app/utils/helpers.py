"""
Common helper utilities used across the backend.
"""

import json
from datetime import datetime, timezone, timedelta


def safe_json_parse(text: str, fallback: dict | None = None) -> dict:
    """Parse JSON string safely, cleaning up markdown codeblocks and other garbage."""
    if not text:
        return fallback or {}
    text_clean = text.strip()
    
    # Remove markdown code block wraps
    if text_clean.startswith("```"):
        lines = text_clean.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text_clean = "\n".join(lines).strip()
        
    try:
        return json.loads(text_clean)
    except (json.JSONDecodeError, TypeError):
        import re
        try:
            match = re.search(r"(\{.*\})", text_clean, re.DOTALL)
            if match:
                brace_content = match.group(1)
                try:
                    return json.loads(brace_content)
                except json.JSONDecodeError:
                    # Clean trailing commas
                    cleaned_block = re.sub(r',\s*([\]}])', r'\1', brace_content)
                    try:
                        return json.loads(cleaned_block)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        return fallback or {}


def get_ist_time() -> str:
    """Get current time in IST timezone as formatted string."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    return now.strftime("%I:%M %p IST, %B %d %Y")


def normalize_uuid(value) -> str | None:
    """Safely normalizes any uuid-like object or string to a string UUID or None."""
    return str(value) if value else None


import random

HUMAN_FALLBACK_RESPONSES = [
    "wait my brain froze for a sec 😭 ||| hold on, what were we saying?",
    "my imaginary wifi betrayed me for a second... 😭 ||| okay, tell me more, I'm listening.",
    "hold on, I got distracted for a sec ||| let me think properly... what's on your mind?",
    "sorry, my train of thought got completely lost there 😭 ||| let's try that again. what were you saying?",
    "wait one sec 😭 lemme read that again",
    "okay wait I lost my train of thought for a moment... ||| what's on your mind?",
    "my brain lagged for a moment ||| hold on, okay, tell me more.",
    "hold onnn... my thoughts buffered for a moment 😭 ||| I'm back now. continue!"
]


def get_random_human_fallback() -> str:
    """Returns a randomized, human-like excuse to keep conversation continuity on error."""
    return random.choice(HUMAN_FALLBACK_RESPONSES)


def get_speculative_transition(message: str) -> str:
    """Returns a fast transition placeholder to trigger typing indicator."""
    return "typing"


def detect_specialist_action(message: str, active_specialists: list[str], pending_specialist: str | None = None) -> tuple[str | None, str | None]:
    """
    Analyzes user message for specialist invite/removal intent.
    DISABLED: Automatic expert switching is disabled. Buddy never auto-connects.
    Always returns (None, None).
    """
    return None, None



