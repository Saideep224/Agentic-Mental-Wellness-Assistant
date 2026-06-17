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
    Returns: (action, specialist_id)
    where action can be 'invite', 'remove', or None.
    """
    msg = (message or "").lower().strip()
    
    # Define mapping of keywords to specialist IDs
    spec_keywords = {
        "lex": ["lex", "lawyer", "legal", "attorney"],
        "maya": ["maya", "doctor", "dr. maya", "dr maya", "physician", "health support", "med"],
        "ray": ["ray", "officer ray", "officer", "cop", "security", "safety", "cyber"],
        "techie": ["techie", "tech", "programmer", "developer", "coding", "debugger"],
        "mentor": ["mentor", "study", "academic", "tutor", "class"],
        "finance": ["finance", "money", "budget", "financial"],
        "fitness": ["fitness", "workout", "gym", "trainer", "exercise"]
    }
    
    # 1. Check for removal intent
    removal_triggers = [
        "remove", "disconnect", "leave", "go away", "don't need", "dont need",
        "can leave", "ask to leave", "thanks", "thank you", "goodbye", "bye", "dismiss"
    ]
    
    is_removal = any(trigger in msg for trigger in removal_triggers)
    
    if is_removal:
        # Check if they mention an active specialist
        for spec_id in active_specialists:
            keywords = spec_keywords.get(spec_id, [spec_id])
            if any(kw in msg for kw in keywords):
                return "remove", spec_id
        # Fallback: if they just say "disconnect all" or "remove specialist" or "can leave"
        if "specialist" in msg or "specialists" in msg or "disconnect" in msg or "remove" in msg or "leave" in msg:
            if active_specialists:
                return "remove", active_specialists[0]
                
    # 2. Check for invite intent
    confirm_words = ["yes", "sure", "okay", "connect", "bring them in", "add them", "invite them", "yeah", "ok", "yep", "go ahead", "do it", "bring him in", "bring her in", "add him", "add her", "invite him", "invite her", "please", "pls"]
    
    if pending_specialist:
        # Check if message contains confirmation
        is_confirm = any(word in msg.split() for word in confirm_words) or (msg in ["y", "ok"])
        if is_confirm and not is_removal:
            return "invite", pending_specialist

    return None, None



