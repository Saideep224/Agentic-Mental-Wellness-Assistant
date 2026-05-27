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
    """Returns a fast, speculative emotional acknowledgment or transitional phrase to reduce perceived latency."""
    msg = (message or "").lower().strip()
    if not msg:
        return "Hmm... ||| "
        
    # Greetings
    if msg in ("hi", "hello", "hey", "yo", "sup", "greetings"):
        return "Hey! 👋 ||| "
        
    # Sad/stressed keywords
    sad_words = ("sad", "bad", "depress", "exhaust", "tired", "burnout", "stressed", "anx", "panic", "cry", "hurt", "lonely", "alone")
    if any(w in msg for w in sad_words):
        return random.choice([
            "Oh, I hear you... ||| ",
            "I'm right here. ||| ",
            "That sounds really heavy... ||| ",
            "Hmm, hold on... ||| "
        ])
        
    # Success/Happy keywords
    happy_words = ("happy", "good", "great", "excit", "awesome", "won", "passed", "love", "smile", "glad")
    if any(w in msg for w in happy_words):
        return random.choice([
            "Oh, wow! ||| ",
            "Aww! ||| ",
            "Love that! ||| ",
            "Hmm, let's see... ||| "
        ])
        
    # Default transitions
    return random.choice([
        "Hmm... ||| ",
        "Hold on... ||| ",
        "Let's see... ||| ",
        "Yeah... ||| "
    ])


