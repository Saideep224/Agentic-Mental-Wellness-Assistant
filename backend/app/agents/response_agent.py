"""Fast final response agent for real-time Buddy chat."""
import logging
import re
from app.utils.llm import generate_chat_completion_with_fallback

logger = logging.getLogger(__name__)


class ResponseAgent:
    """Generate exactly one final LLM response, validate with critic, and sanitize hidden reasoning."""

    async def generate(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 350,
        recent_responses: list = None,
        user_signal: dict = None,
        response_plan: dict = None
    ) -> dict:
        response_text = await generate_chat_completion_with_fallback(
            messages=messages, temperature=temperature, max_tokens=min(max_tokens, 350)
        )
        raw = response_text or ""
        clean, reasoning = self._sanitize_response(raw)

        # ── Run Deterministic Quality Critic ─────────────────────────────
        from app.services.emotional_intelligence import response_critic
        
        # Fallbacks to prevent AttributeError
        active_signal = user_signal or {"primary_emotion": "neutral", "intensity": 0.5, "user_need": "listening"}
        active_plan = response_plan or {"desired_length": "medium", "avoid": []}
        
        failed_checks = response_critic.audit(clean, active_signal, active_plan, recent_responses)
        
        if failed_checks:
            logger.warning(
                f"[Critic Rejected] Response failed validations: {failed_checks}. "
                f"Candidate: '{clean[:60]}...'. Retrying once with critic feedback."
            )
            
            feedback_msg = (
                "CRITIC FEEDBACK (REJECTED CANDIDATE RESPONSE):\n"
                f"Your previous candidate response: \"{clean}\"\n"
                f"It was rejected due to these quality violations: {', '.join(failed_checks)}.\n"
                "Please regenerate a fresh response. Follow all rules: write in lowercase Gen Z WhatsApp style, "
                "ensure context-aware friend empathy, limit slang to 1-2 words max, omit terminal punctuation, "
                "strictly avoid forbidden phrases (like 'unpack that', 'that sounds tough', 'explore that', 'as an AI', "
                "'i understand', 'sorry to hear that'), and do not ask multiple questions."
            )
            
            # Make a copy of messages and append feedback
            regeneration_messages = list(messages)
            regeneration_messages.append({"role": "system", "content": feedback_msg})
            
            retry_raw = await generate_chat_completion_with_fallback(
                messages=regeneration_messages, temperature=0.5, max_tokens=min(max_tokens, 350)
            )
            clean, reasoning_retry = self._sanitize_response(retry_raw or "")
            reasoning = f"{reasoning}\n[Critic retry reasoning]: {reasoning_retry}"

        if not clean:
            clean = "hey — I’m with you. say that again?"
            
        return {"text": clean, "reasoning": reasoning}

    def _sanitize_response(self, raw: str) -> tuple[str, str]:
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
        return clean, reasoning

    @staticmethod
    def _similarity_score(a: str, b: str) -> float:
        if not a or not b: return 0.0
        aa, bb = set(a.lower().split()), set(b.lower().split())
        return len(aa & bb) / len(aa | bb) if aa | bb else 0.0

    def check_response_quality(self, text: str) -> bool:
        return bool(text and len(text.strip()) >= 3)


response_agent = ResponseAgent()
