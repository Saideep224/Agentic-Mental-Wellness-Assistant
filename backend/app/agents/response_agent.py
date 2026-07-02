"""
Response Agent - coordinates tone, response strategy, compiles final system prompt and makes LLM calls with quality checking.
"""

import logging
from typing import Dict, Any, List
from app.utils.llm import generate_chat_completion_with_fallback
from app.config import settings

logger = logging.getLogger(__name__)

class ResponseAgent:
    """
    Logical agent responsible for:
    - Executing LLM completions with fallback providers
    - Validating output quality
    - Executing retries with temperature scaling
    """

    async def generate(self, messages: list, temperature: float = 0.7, max_tokens: int = 800, recent_responses: list = None) -> dict:
        """
        Generate chat response with fallback and quality checking. Returns a dict with 'text' and 'reasoning'.
        recent_responses: list of recent Buddy response strings (for repetition guard).
        """
        retries = 2
        current_temp = temperature
        
        for attempt in range(retries + 1):
            try:
                response_text = await generate_chat_completion_with_fallback(
                    messages=messages,
                    temperature=current_temp,
                    max_tokens=max_tokens,
                    # preferred_model=None — respect PRIMARY_PROVIDER from settings
                )
                
                # Parse reasoning and clean text — defense-in-depth sanitizer
                import re
                raw_text = response_text
                reasoning = ""
                clean_text = ""
                
                # Normalize variant tag formats: "reasoning>", "<reasoning>", "<thinking>", etc.
                # Some models output tags without the leading "<" bracket
                normalized = raw_text
                normalized = re.sub(r'(?<![</])reasoning>', '<reasoning>', normalized, flags=re.IGNORECASE)
                normalized = re.sub(r'(?<!<)/reasoning>', '</reasoning>', normalized, flags=re.IGNORECASE)
                normalized = re.sub(r'(?<![</])thinking>', '<thinking>', normalized, flags=re.IGNORECASE)
                normalized = re.sub(r'(?<!<)/thinking>', '</thinking>', normalized, flags=re.IGNORECASE)
                
                # Try extracting <reasoning>...</reasoning> or <thinking>...</thinking>
                tag_pattern = re.compile(
                    r'<(?:reasoning|thinking|analysis|reflection)>(.*?)</(?:reasoning|thinking|analysis|reflection)>',
                    re.IGNORECASE | re.DOTALL
                )
                tag_match = tag_pattern.search(normalized)
                
                if tag_match:
                    reasoning = tag_match.group(1).strip()
                    clean_text = normalized[:tag_match.start()] + normalized[tag_match.end():]
                    clean_text = clean_text.strip()
                elif re.search(r'<(?:reasoning|thinking|analysis|reflection)>', normalized, re.IGNORECASE):
                    # Opening tag exists but no closing tag — strip everything from the opening tag to the first double newline
                    parts = re.split(r'<(?:reasoning|thinking|analysis|reflection)>', normalized, maxsplit=1, flags=re.IGNORECASE)
                    before = parts[0].strip()
                    after = parts[1] if len(parts) > 1 else ""
                    # Try to find where the reasoning ends (double newline or end of text)
                    reasoning_end = re.split(r'\n\n', after, maxsplit=1)
                    if len(reasoning_end) > 1:
                        reasoning = reasoning_end[0].strip()
                        clean_text = (before + "\n\n" + reasoning_end[1].strip()).strip()
                    else:
                        reasoning = after.strip()
                        clean_text = before
                else:
                    clean_text = raw_text.strip()
                
                # Final cleanup: strip any residual XML-like tags
                clean_text = re.sub(r'</?(?:reasoning|thinking|analysis|reflection)>', '', clean_text, flags=re.IGNORECASE).strip()
                
                # Strip lines that look like internal reasoning (starts with reasoning markers)
                reasoning_line_patterns = [
                    r'^The user (?:responded|is |said|seems|appears|mentioned)',
                    r'^This indicates',
                    r'^My goal is',
                    r'^I should',
                    r'^I will',
                    r'^I\'ll',
                    r'^I need to',
                    r'^Let me',
                    r'^The user\'s emotion',
                    r'^Hidden Strategy:',
                    r'^Emotional Understanding:',
                    r'^Conversational Intent:',
                ]
                combined_pattern = '|'.join(reasoning_line_patterns)
                lines = clean_text.split('\n')
                filtered_lines = []
                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line and re.match(combined_pattern, stripped_line, re.IGNORECASE):
                        reasoning += "\n" + stripped_line  # preserve for debug
                        continue
                    filtered_lines.append(line)
                clean_text = '\n'.join(filtered_lines).strip()
                
                # Check response quality on the clean text
                quality_ok = self.check_response_quality(clean_text)

                # Repetition guard: reject if too similar to a recent response
                repetition_ok = True
                if recent_responses and clean_text:
                    for prev in recent_responses[-5:]:
                        if self._similarity_score(clean_text, prev) > 0.65:
                            repetition_ok = False
                            logger.warning(
                                f"[RepetitionGuard] Response too similar to a recent one (attempt {attempt + 1}). "
                                "Retrying with higher temperature."
                            )
                            break

                if (quality_ok and repetition_ok) or attempt == retries:
                    if attempt == retries and not (quality_ok and repetition_ok):
                        logger.warning(f"[ResponseAgent] Response did not pass all checks (quality_ok={quality_ok}, repetition_ok={repetition_ok}) on final attempt, but returning the LLM response anyway per architecture requirements: '{clean_text}'")
                    return {"text": clean_text, "reasoning": reasoning}
                
                logger.warning(f"Response failed quality/repetition check on attempt {attempt + 1} (quality_ok={quality_ok}, repetition_ok={repetition_ok}). Retrying with adjusted temperature...")
                current_temp = min(1.0, current_temp + 0.15)
            except Exception as e:
                logger.error(f"ResponseAgent generation failed: {e}", exc_info=True)
                if attempt == retries:
                    raise e
                    
        return {
            "text": "damn... ||| okay talk to me, what's going on?",
            "reasoning": "Fallback response triggered due to complete generation error."
        }

    @staticmethod
    def _similarity_score(a: str, b: str) -> float:
        """Simple token-overlap Jaccard similarity. No external dependencies."""
        if not a or not b:
            return 0.0
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union) if union else 0.0

    def check_response_quality(self, text: str) -> bool:
        """
        Check if the generated response is generic, robotic, or too short.
        """
        if not text or len(text.strip()) < 10:
            return False
            
        robotic_phrases = [
            # Hard AI tells
            "as an ai",
            "language model",
            "virtual assistant",
            "i am an ai",
            "i'm an ai",
            "how can i help you today",
            "i am here to assist",
            "i'm here to assist",
            # Therapist / corporate support language — all banned
            "i understand your concern",
            "i understand your frustration",
            "i understand how you feel",
            "i understand what you're going through",
            "i empathize with your situation",
            "i empathize with",
            "that must be difficult",
            "that must be challenging",
            "that must be tough",
            "that sounds difficult",
            "that sounds challenging",
            "i am here to support you",
            "i'm here to support you",
            "i am here for you",
            "i'm here for you",
            "let's explore that",
            "let's unpack that",
            "let's work through",
            "it's completely understandable",
            "it is completely understandable",
            "it's totally understandable",
            "i hear you",
            "i see you",
            "your feelings are valid",
            "your feelings are completely valid",
            "it's okay to feel",
            "it is okay to feel",
            "i want you to know",
            "please know that",
            "remember that you are not alone",
            "you are not alone in this",
        ]
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in robotic_phrases):
            return False
            
        # Overly generic placeholders
        if text.strip() in [
            "I'm here for you.",
            "What's on your mind?",
            "Tell me more."
        ]:
            return False
            
        return True

response_agent = ResponseAgent()
