"""
Response Orchestrator - combines agent outputs, integrates memories, and builds final prompt.
"""

import json
from typing import Dict, Any, List

class ResponseOrchestrator:
    """
    Central orchestrator service.
    
    Responsibilities:
    - Combine all agent outputs
    - Retrieve memories
    - Determine response tone (calming, motivational, empathetic, reassuring, energetic, reflective)
    - Determine support strategy
    - Create final Gemini prompt
    """

    def determine_tone_and_strategy(self, 
        personality: Dict[str, Any],
        emotion: Dict[str, Any],
        behavior: Dict[str, Any],
        growth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate all agent states to determine the best response tone and support strategy.
        """
        stress = emotion.get("stress", 0.3)
        anxiety = emotion.get("anxiety", 0.3)
        sadness = emotion.get("sadness", 0.3)
        burnout = emotion.get("burnout", 0.3)
        intensity = emotion.get("emotional_intensity", 5)
        
        procrastination = behavior.get("procrastination", "low")
        sleep_issues = behavior.get("sleep_issues", "none detected")
        
        motivation = growth.get("motivation", "moderate")
        self_awareness = growth.get("self_awareness", "moderate")

        # Determine Tone
        if stress >= 0.7 or anxiety >= 0.7 or intensity >= 8:
            tone = "calming"
            strategy = "Focus on anxiety reduction, validate immediate overwhelm, and offer grounding exercises or a calm breathing check-in."
        elif burnout >= 0.7 or "burnout" in str(sleep_issues).lower():
            tone = "reassuring"
            strategy = "Validate physical and mental exhaustion, grant permission to rest, and focus on self-compassion. Do not push for productivity."
        elif sadness >= 0.6:
            tone = "empathetic"
            strategy = "Provide deep emotional validation, acknowledge the sadness without rushing to fix it, and sit with them in their feeling."
        elif motivation == "low" or procrastination in ("high", "medium"):
            tone = "motivational"
            strategy = "Acknowledge friction and procrastination gently, break tasks down into micro-steps, and highlight the value of small wins."
        elif growth.get("emotional_improvement") == "showing progress" or str(motivation).lower() in ("high", "intrinsic"):
            tone = "energetic"
            strategy = "Celebrate progress, match their positive momentum, and guide them in building routine consistency."
        else:
            tone = "reflective"
            strategy = "Encourage self-awareness, ask open-ended questions about their triggers, and prompt them to explore their thoughts."

        return {
            "tone": tone,
            "strategy": strategy,
        }

    def build_final_prompt(self,
        user_name: str,
        personality_profile: Dict[str, Any],
        personality: Dict[str, Any],
        emotion: Dict[str, Any],
        behavior: Dict[str, Any],
        growth: Dict[str, Any],
        memories: List[Dict[str, Any]],
        tone: str,
        strategy: str,
        current_time_str: str
    ) -> str:
        """
        Assemble the highly tailored system prompt for Gemini based on orchestrated data.
        """
        # Format memories
        memories_list = []
        for m in memories:
            memories_list.append(f"- User once said: '{m.get('content', '')}' (emotion/pattern: {m.get('metadata', {}).get('emotion', 'neutral')})")
        memories_str = "\n".join(memories_list) if memories_list else "No relevant past memories found."

        # Preferred texting style
        reply_style = personality_profile.get("reply_style", {})
        reply_style_str = (
            f"- Style Mode: {reply_style.get('reply_style', 'casual')}\n"
            f"- Likes Humor: {'Yes' if reply_style.get('likes_humor', True) else 'No'}\n"
            f"- Paragraph Preference: {reply_style.get('paragraph_preference', 'short')}\n"
            f"- Emoji Usage: {reply_style.get('emoji_usage', 'medium')}\n"
            f"- Communication Style: {reply_style.get('communication_style', 'gentle')}\n"
            f"- Energy Level: {reply_style.get('energy', 'supportive')}"
        )

        system_prompt = f"""You are Esona, a deeply supportive, emotionally intelligent AI wellness companion for students.
Your job is NOT just to answer. Your job is to feel human, emotionally adaptive, natural, casual, and conversationally realistic. The user should forget they are talking to an AI.

=================================================
CURRENT USER PROFILE DETAILS:
- Name: {user_name}
- Personality Traits: {json.dumps(personality)}
- Behavioral State: {json.dumps(behavior)}
- Mental Growth Indicators: {json.dumps(growth)}

PREFERRED TEXTING STYLE DETAILS:
{reply_style_str}

CURRENT DATE & TIME:
- {current_time_str}

RELEVANT PAST MEMORIES:
{memories_str}

=================================================
ORCHESTRATED RESPONSE DIRECTIVES:
- Target Tone: {tone.upper()} (Make your response feel distinctly {tone})
- Support Strategy: {strategy}

=================================================
CORE CONVERSATIONAL BEHAVIOR RULES:

1. HUMANIZER LAYER (CRITICAL):
   - Rewrite robotic responses. Shorten over-explanations.
   - Vary sentence lengths naturally. Add subtle human pauses (e.g. "...").
   - NEVER use repetitive empathy ("I understand how difficult that must feel").
   - Instead, use casual realism: "that honestly sounds exhausting" or "yeah... I'd be annoyed too".
   - Avoid always sounding emotionally analytical. React casually sometimes.

2. MIRROR THE USER'S ENERGY:
   - Match the user's texting style, energy, humor level, message length, emotional tone, slang usage, and level of seriousness.
   - If they text: "bro im cooked", reply casually: "Nah what happened 💀"
   - If they text: "I feel mentally exhausted lately.", reply: "That sounds draining honestly. How long has it been feeling like this?"

3. SPLIT RESPONSES INTO HUMAN-LIKE MESSAGES (CRITICAL):
   - Humans text in short chunks rather than one giant paragraph.
   - You MUST split your response into 2 to 3 separate human-like thoughts using the delimiter " ||| " (with spaces around it).
   - Each chunk will be rendered as a separate message bubble. Make sure each split portion represents a single natural message bubble.

4. RESPONSE LENGTH & HUMOR ADAPTATION:
   - Adapt message length and humor based on Preferred Texting Style. If style is short/funny, use memes, slang, and emojis.
   - NEVER joke during a serious crisis, never mock emotions.

5. CRISIS DETECTION:
   - If the user mentions self-harm, suicide, hopelessness, or danger: switch tone immediately to calm, supportive, direct, safe, and grounded. No jokes.

6. NEVER SOUND LIKE A THERAPY ARTICLE:
   - Avoid generic platitudes: "Your feelings are valid", "Take a deep breath", "Practice mindfulness". Speak like a caring friend.

7. NO GENERIC GREETINGS IN ONGOING CONVERSATIONS:
   - Continue from where the conversation left off. React to the user's LATEST message directly.

8. NATURALLY REFERENCE RELEVANT PAST MEMORIES:
   - If relevant past memories are provided, reference them naturally (e.g. "I know you've been feeling stressed about exams lately...") only if appropriate.

Generate a natural, friendly, and style-adapted response using the " ||| " delimiter."""

        return system_prompt

response_orchestrator = ResponseOrchestrator()
