"""Fast final response agent for real-time Buddy chat."""
import logging
import re
from app.utils.llm import generate_chat_completion_with_fallback

logger = logging.getLogger(__name__)


class ResponseAgent:
    """Generate exactly one final LLM response and sanitize hidden reasoning."""

    async def generate(self, messages: list, temperature: float = 0.7, max_tokens: int = 350, recent_responses: list = None) -> dict:
        response_text = await generate_chat_completion_with_fallback(
            messages=messages, temperature=temperature, max_tokens=min(max_tokens, 350)
        )
        raw = response_text or ""
        reasoning = ""
        normalized = re.sub(r'(?<![</])reasoning>', '<reasoning>', raw, flags=re.IGNORECASE)
        normalized = re.sub(r'(?<!<)/reasoning>', '</reasoning>', normalized, flags=re.IGNORECASE)
        pattern = re.compile(r'<(?:reasoning|thinking|analysis|reflection)>(.*?)</(?:reasoning|thinking|analysis|reflection)>', re.I | re.S)
        match = pattern.search(normalized)
        if match:
            reasoning = match.group(1).strip()
            clean = (normalized[:match.start()] + normalized[match.end():]).strip()
        else:
            clean = raw.strip()
        clean = re.sub(r'</?(?:reasoning|thinking|analysis|reflection)>', '', clean, flags=re.I).strip()

        hidden_markers = re.compile(
            r'^(The user (?:responded|is |said|seems|appears|mentioned)|This indicates|My goal is|I should|I will|I need to|Let me|Hidden Strategy:|Emotional Understanding:|Conversational Intent:)', re.I
        )
        visible = []
        for line in clean.splitlines():
            if line.strip() and hidden_markers.match(line.strip()):
                reasoning += "\n" + line.strip()
            else:
                visible.append(line)
        clean = "\n".join(visible).strip()
        if not clean:
            clean = "hey — I’m with you. say that again?"
        return {"text": clean, "reasoning": reasoning}

    @staticmethod
    def _similarity_score(a: str, b: str) -> float:
        if not a or not b: return 0.0
        aa, bb = set(a.lower().split()), set(b.lower().split())
        return len(aa & bb) / len(aa | bb) if aa | bb else 0.0

    def check_response_quality(self, text: str) -> bool:
        return bool(text and len(text.strip()) >= 3)


response_agent = ResponseAgent()
