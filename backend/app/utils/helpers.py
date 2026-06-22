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


def detect_specialist_action(message: str, active_specialists: list[str], suggested_specialist: str | None = None) -> tuple[str | None, str | None]:
    """
    Analyzes user message for specialist invite/removal intent.
    Returns: (action, specialist_id)
    where action can be 'invite', 'remove', or None.
    """
    msg = (message or "").lower().strip()
    
    # Minimal keyword list strictly for explicit connects or removes by name
    spec_keywords = {
        "lex": ["lex"],
        "maya": ["maya", "dr. maya", "dr maya"],
        "ray": ["ray", "officer ray"],
        "techie": ["techie"],
        "mentor": ["mentor"],
        "finance": ["finance coach"],
        "fitness": ["fitness coach"],
        "relationship": ["relationship coach"]
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
                
    # 2. Explicit confirmation of a suggested specialist
    if suggested_specialist and not is_removal:
        confirmation_triggers = [
            "yes", "yeah", "yep", "sure", "okay", "ok", "connect", "bring", "do it", "please", "alright", "fine"
        ]
        rejection_triggers = [
            "no", "nah", "nope", "nevermind", "don't", "dont", "stop", "never mind"
        ]
        
        is_rejection = any(msg.startswith(t) for t in rejection_triggers) or msg == "n"
        if not is_rejection:
            # If they use a confirmation word or it's a very short affirmative message
            if any(t in msg for t in confirmation_triggers) or msg == "y":
                return "invite", suggested_specialist
                
    # 3. Explicit invite by exact specialist name
    invite_triggers = [
        "connect", "invite", "add", "call", "bring in", "summon", "talk to", "chat with"
    ]
    
    is_invite = any(trigger in msg for trigger in invite_triggers)
    
    if is_invite and not is_removal:
        # Find which specialist they are explicitly requesting by name
        for spec_id, keywords in spec_keywords.items():
            if any(kw in msg for kw in keywords):
                # Only invite if they aren't already active
                if spec_id not in active_specialists:
                    return "invite", spec_id
                        
    return None, None



