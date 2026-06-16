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

    async def generate(self, messages: list, temperature: float = 0.7, max_tokens: int = 800) -> dict:
        """
        Generate chat response with fallback and quality checking. Returns a dict with 'text' and 'reasoning'.
        """
        retries = 2
        current_temp = temperature
        
        for attempt in range(retries + 1):
            try:
                response_text = await generate_chat_completion_with_fallback(
                    messages=messages,
                    temperature=current_temp,
                    max_tokens=max_tokens,
                    preferred_model=settings.OLLAMA_MODEL,
                )
                
                # Parse reasoning and clean text
                import re
                raw_text = response_text
                reasoning = ""
                clean_text = ""
                
                if "<reasoning>" in raw_text.lower():
                    parts = re.split(r"(?i)<reasoning>", raw_text, maxsplit=1)
                    before_reasoning = parts[0].strip()
                    after_reasoning = parts[1]
                    
                    if "</reasoning>" in after_reasoning.lower():
                        sub_parts = re.split(r"(?i)</reasoning>", after_reasoning, maxsplit=1)
                        reasoning = sub_parts[0].strip()
                        clean_text = (before_reasoning + "\n\n" + sub_parts[1].strip()).strip()
                    else:
                        # Fallback for missing closing tag
                        lines_split = after_reasoning.split("\n\n")
                        if len(lines_split) > 1:
                            reasoning = "\n\n".join(lines_split[:-1]).strip()
                            clean_text = (before_reasoning + "\n\n" + lines_split[-1].strip()).strip()
                        else:
                            reasoning = after_reasoning.strip()
                            clean_text = before_reasoning.strip()
                else:
                    clean_text = raw_text.strip()
                
                # Clean up any residual tags
                clean_text = re.sub(r"(?i)</?reasoning>", "", clean_text).strip()
                
                # Check response quality on the clean text
                if self.check_response_quality(clean_text) or attempt == retries:
                    return {"text": clean_text, "reasoning": reasoning}
                
                logger.warning(f"Response failed quality check on attempt {attempt + 1}. Retrying with adjusted temperature...")
                current_temp = min(1.0, current_temp + 0.15)
            except Exception as e:
                logger.error(f"ResponseAgent generation failed: {e}", exc_info=True)
                if attempt == retries:
                    raise e
                    
        return {
            "text": "I'm here for you. ||| Things sound a bit heavy right now... ||| What's on your mind?",
            "reasoning": "Fallback response triggered due to error or poor quality."
        }

    def check_response_quality(self, text: str) -> bool:
        """
        Check if the generated response is generic, robotic, or too short.
        """
        if not text or len(text.strip()) < 10:
            return False
            
        robotic_phrases = [
            "as an ai", 
            "language model", 
            "virtual assistant", 
            "how can i help you today", 
            "i am here to assist", 
            "i am an ai"
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
