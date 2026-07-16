"""
Esona Emotional Intelligence V2 Engine.
Manages the structured UserSignal, ResponsePlan, explicit emotion detection,
Telugu code-mixed parsing, conversation stage movement, response strategist, and response critic.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, TypedDict

logger = logging.getLogger(__name__)

# --- Structured Signal Definitions ---

class UserSignal(TypedDict, total=False):
    explicit_emotions: List[str]
    implicit_emotions: List[str]
    primary_emotion: str
    secondary_emotion: Optional[str]
    emotion_confidence: float
    intensity: float  # 0.0 to 1.0
    valence: str  # positive, negative, neutral
    arousal: str  # high, moderate, low
    situation: str  # relationship, financial, academic, health, work, general
    target: Optional[str]  # partner, self, parents, work, none
    user_need: str  # validation, exploration, grounding, problem_solving, celebration, listening
    conversation_stage: str
    risk_level: str  # low, medium, high, crisis
    uncertainty: float  # 0.0 to 1.0


class ResponsePlan(TypedDict, total=False):
    primary_strategy: str  # LISTEN, REFLECT, VALIDATE, GROUND, CELEBRATE, PROBLEM_SOLVE, SAFETY
    secondary_strategy: Optional[str]
    should_ask_question: bool
    should_offer_action: bool
    should_use_memory: bool
    desired_length: str  # short, medium, long
    tone: str  # warm_grounded, calming, empathetic, motivational, reflective, energetic, casual
    avoid: List[str]


SITUATION_KEYWORDS = {
    "relationship": ["gf", "girlfriend", "bf", "boyfriend", "ex", "partner", "spouse", "wife", "husband", "fight", "argued", "argument"],
    "financial": ["money", "cash", "debt", "loan", "bills", "rent", "broke", "afford", "salary"],
    "academic": ["exam", "exams", "test", "fail", "failed", "grade", "college", "study", "studying", "placement", "interview"],
    "work": ["job", "work", "boss", "manager", "fired", "colleague"]
}


# --- Core Analysis Methods ---

def analyze_phrase_assertions(message: str) -> List[Dict[str, Any]]:
    """
    Parses a user message into distinct clauses by splitting on conjunctions
    and identifies negation, past tense, and third-person references.
    """
    text_clean = message.lower().strip()
    # Normalize punctuation, keeping apostrophes for don't/isn't etc.
    text_clean = re.sub(r"[^\w\s']", " ", text_clean)
    
    # Split on clause boundaries
    clauses = re.split(r"\b(?:but|however|yet|although|though|except)\b", text_clean)
    
    parsed_clauses = []
    for clause in clauses:
        words = clause.split()
        if not words:
            continue
            
        clause_str = " ".join(words)
        
        # Negation check: ignore "no reason", "no idea", "no clue", "no choice"
        clean_for_negation = re.sub(r"\bno\s+(?:reason|idea|clue|choice|option|way)\b", " ", clause_str)
        negation_regex = r"\b(?:not|no|dont|don't|never|aint|isnt|isn't|arent|aren't|wasnt|wasn't|no\s+longer|anymore|nomore|em\s+ledu|ledu|kadu|kaadu|kavatle|kavatledu|cheppatledu|em|kaadu|kavatam)\b"
        negated = bool(re.search(negation_regex, clean_for_negation))
        
        past_regex = r"\b(?:was|were|yesterday|earlier|before|past|previously|ninna|unde)\b"
        past_tense = bool(re.search(past_regex, clause_str))
        
        # Experiencer checks
        strong_third_regex = r"\b(?:she|he|they|vadiki|vaadi|vaadu|ame|ataniki|amedi|variki)\b"
        first_person_regex = r"\b(?:i|im|i'm|naku|naaku|me|my|unna)\b"
        
        third_person = False
        
        # Check index of first person vs strong third person
        has_first = bool(re.search(first_person_regex, clause_str))
        has_strong_third = bool(re.search(strong_third_regex, clause_str))
        
        if has_strong_third:
            if has_first:
                # Find positions
                first_pos = re.search(first_person_regex, clause_str).start()
                third_pos = re.search(strong_third_regex, clause_str).start()
                if third_pos < first_pos:
                    third_person = True
            else:
                third_person = True
                
        soft_third_regex = r"\b(?:boss|friend|wife|gf|girlfriend|bf|boyfriend|husband|partner|someone|roomie|roommate)\b"
        if re.search(soft_third_regex, clause_str) and not has_first:
            third_person = True
            
        # Telugu ga undi / ga unna overrides third person unless strong third person subject is before it
        is_telugu_self_report = any(w.endswith(("ga", "giri", "unna", "undi")) for w in words) or any(w.startswith(("chirak", "badha", "bayam", "kangaru", "ardham")) for w in words)
        if is_telugu_self_report:
            # Only count as third person if strong Telugu third person is present
            strong_telugu_third = r"\b(?:vadiki|vaadi|vaadu|ame|ataniki|amedi|variki)\b"
            if not re.search(strong_telugu_third, clause_str):
                third_person = False
            
        parsed_clauses.append({
            "text": clause,
            "words": words,
            "negated": negated,
            "past_tense": past_tense,
            "third_person": third_person
        })
        
    return parsed_clauses




def detect_explicit_emotion(message: str) -> List[str]:
    """Matches the clean user message against explicit English and Telugu emotion patterns with structural filters."""
    clauses = analyze_phrase_assertions(message)
    detected = []
    
    # 1. Frustration / Anger
    frust_words = {"frustrated", "frustration", "pissed", "annoyed", "annoyance", "furious", "enraged", "mad", "angry", "anger", "hate", "hates", "hating", "annoy", "annoying", "irritated", "irritating", "patience"}
    # 2. Sadness
    sad_words = {"sad", "sadness", "depressed", "depression", "heartbroken", "heartbreak", "crying", "cry", "hopeless", "hopelessness", "devastated", "miserable", "hurt", "grief", "grieving", "miss", "missing"}
    # 3. Anxiety / Fear
    anx_words = {"anxious", "anxiety", "worried", "worry", "panic", "panicking", "scared", "afraid", "terrified", "dread", "overthinking", "nervous", "tension", "tense"}
    # 4. Stress
    stress_words = {"stressed", "stress", "stressing", "overwhelmed", "exhausted", "burnout", "burnt", "burned", "tired", "exhausting", "pressure", "struggling", "struggle", "cope", "deadline", "deadlines", "swamped", "busy", "disturb", "disturbed"}
    # 5. Loneliness
    lonely_words = {"lonely", "loneliness", "isolated", "isolation", "alone", "nobody"}
    # 6. Joy
    joy_words = {"happy", "joy", "excited", "grateful", "blessed", "glad"}
    # 7. Confusion
    conf_words = {"confused", "confusion", "weird", "nothing", "explain", "off", "feeling", "know", "sure"}


    for clause in clauses:
        words = clause["words"]
        text_clause = " ".join(words)
        
        def has_match(words_set, prefix_tuple=None):
            if words_set & set(words):
                return True
            if prefix_tuple:
                return any(w.startswith(prefix_tuple) for w in words)
            return False
            
        # Frustration
        is_frust = False
        if has_match(frust_words, ("chirak", "cirak", "irritat")):
            is_frust = True
        if "fed up" in text_clause or "sick of" in text_clause or "patience is gone" in text_clause or "done with" in text_clause:
            is_frust = True
        if is_frust and not (clause["negated"] or clause["past_tense"] or clause["third_person"]):
            detected.append("frustration")
                
        # Sadness
        is_sad = False
        if has_match(sad_words, ("badha", "baadha", "bhada")) or "baledu" in words:
            is_sad = True
        for i, w in enumerate(words):
            if w in ("feel", "feeling", "feelingso", "feelso"):
                for offset in (1, 2, 3):
                    if i + offset < len(words) and words[i + offset] in ("low", "down", "empty"):
                        is_sad = True
        if is_sad:
            is_negated = clause["negated"]
            if "baledu" in words and not ("cheppatledu" in words or "fine" in words or "okay" in words):
                is_negated = False
            if not (is_negated or clause["past_tense"] or clause["third_person"]):
                detected.append("sadness")
                    
        # Anxiety
        is_anx = False
        if has_match(anx_words, ("bhayam", "bayam", "bhayan", "bayan", "kangaru", "kangaaru", "kangat")):
            is_anx = True
        if "panic attack" in text_clause:
            is_anx = True
        if is_anx and not (clause["negated"] or clause["past_tense"] or clause["third_person"]):
            detected.append("anxiety")
                
        # Stress
        is_stress = False
        if has_match(stress_words):
            is_stress = True
        if "too much pressure" in text_clause:
            is_stress = True
        if is_stress and not (clause["negated"] or clause["past_tense"] or clause["third_person"]):
            detected.append("stress")
                
        # Loneliness
        is_lonely = False
        if has_match(lonely_words):
            is_lonely = True
        if "all alone" in text_clause or "no one" in text_clause:
            is_lonely = True
        if is_lonely and not (clause["negated"] or clause["past_tense"] or clause["third_person"]):
            detected.append("loneliness")
                
        # Joy
        is_joy = False
        if has_match(joy_words):
            is_joy = True
        if "so glad" in text_clause:
            is_joy = True
        if is_joy and not (clause["negated"] or clause["past_tense"] or clause["third_person"]):
            detected.append("joy")
                
        # Confusion
        is_conf = False
        if {"confused", "confusion"} & set(words):
            is_conf = True
        if any(w.startswith(("ardham", "ardam")) for w in words):
            if clause["negated"] or "kavatle" in words or "kavatledu" in words:
                is_conf = True
        if has_match(conf_words):
            if "don't know what" in text_clause or "dont know what" in text_clause or "not sure" in text_clause:
                is_conf = True
            elif "feel nothing" in text_clause or "feel weird" in text_clause or "feels off" in text_clause or "explain it" in text_clause:
                is_conf = True
            elif "don't even know" in text_clause or "dont even know" in text_clause:
                is_conf = True
        if is_conf and not (clause["past_tense"] or clause["third_person"]):
            detected.append("confusion")


            
    return list(set(detected))



def determine_conversation_stage(
    message: str, history: List[dict], primary_emotion: str, intensity: float
) -> str:
    """Classifies the conversation movement stage based on history and current inputs."""
    msg = message.lower().strip()
    msg_clean = re.sub(r"[^\w\s']", " ", msg)
    words = msg_clean.split()
    
    # Crisis overrides
    crisis_keywords = ["want to die", "kill myself", "end my life", "suicide", "hurt myself", "self-harm", "suicidal", "end it", "die", "kill me", "planning to end"]
    if any(k in msg for k in crisis_keywords):
        return "crisis"

    # Opening/casual chat
    if not history:
        if primary_emotion != "neutral":
            return "disclosure"
        return "opening"

    # Seeking advice or action
    advice_triggers = ["what should i do", "how to solve", "help me fix", "give me advice", "suggest", "what do i do"]
    if any(t in msg for t in advice_triggers):
        return "seeking_advice"
    
    action_triggers = ["will try", "okay i will", "let's do it", "sounds like a plan", "i can try that", "i will", "i'll do", "i will do"]
    if any(t in msg for t in action_triggers):
        return "ready_for_action"

    # Progress/recovery
    recovery_triggers = ["thanks", "thank you", "feel better", "helpful", "makes sense", "thank u"]
    if any(t in msg for t in recovery_triggers) and primary_emotion == "neutral":
        return "recovery"
    
    # Split greeting words and banter words
    greeting_words = ["hi", "hey", "hello", "yo", "sup", "whats up", "good morning", "good night"]
    banter_words = ["ok", "okay", "cool", "nice", "fine", "lol", "lmao", "haha", "thanks", "thank you", "thank u"]
    
    if len(words) <= 3:
        if any(w in greeting_words for w in words):
            if len(history) <= 2:
                return "opening"
            return "casual"
        if any(w in banter_words for w in words):
            return "casual"


    # Normal transitions: check history depth
    # Count how many historical user messages disclosed an emotion
    history_disclosures = 0
    for h in history:
        if h.get("role") == "user":
            if detect_explicit_emotion(h.get("content", "")):
                history_disclosures += 1
                
    # First serious disclosure
    if primary_emotion != "neutral" and history_disclosures == 0:
        return "disclosure"
    
    # Continued emotional sharing
    if primary_emotion != "neutral":
        if intensity >= 0.8:
            return "escalation"
        return "deepening"

    return "reflection"


def build_user_signal(
    user_message: str,
    history: List[dict],
    personalization: dict,
    blended_scores: Optional[List[float]] = None
) -> UserSignal:
    """Compiles the unified UserSignal from explicit statements, neural predictions, and history context."""
    # 1. Parse Explicit Emotions
    explicits = detect_explicit_emotion(user_message)
    
    # Sort by priority to ensure correct primary emotion matching
    priority = ["anxiety", "frustration", "sadness", "stress", "loneliness", "confusion", "joy"]
    explicits = sorted(explicits, key=lambda e: priority.index(e) if e in priority else 99)


    # 2. Extract Classifier Winner
    emotions_order = ["sadness", "anger", "fear", "anxiety", "happy", "excitement", "frustration", "loneliness", "neutral"]
    primary_class = "neutral"
    confidence = 0.5
    secondary = None
    
    if blended_scores and len(blended_scores) == 9:
        sorted_indices = sorted(range(9), key=lambda i: blended_scores[i], reverse=True)
        primary_class = emotions_order[sorted_indices[0]]
        confidence = blended_scores[sorted_indices[0]]
        secondary = emotions_order[sorted_indices[1]] if blended_scores[sorted_indices[1]] >= 0.10 else None
        
    # Map raw emotions names to match taxonomy
    if primary_class == "happy":
        primary_class = "joy"
    if secondary == "happy":
        secondary = "joy"

    # 3. Apply Explicit Override Rules (Phase 2)
    final_primary = primary_class
    final_confidence = confidence
    
    if explicits:
        explicit_winner = explicits[0]
        # Always override if explicitly declared and matches differently
        if primary_class != explicit_winner:
            final_primary = explicit_winner
            final_confidence = 0.95
            logger.info(f"[EI V2 Override] Overriding classifier '{primary_class}' with explicit '{explicit_winner}'")

    # Check for crisis override
    msg_lower = user_message.lower()
    crisis_keywords = ["want to die", "kill myself", "end my life", "suicide", "hurt myself", "self-harm", "suicidal", "end it", "die", "kill me", "planning to end"]
    if any(k in msg_lower for k in crisis_keywords):
        final_primary = "sadness"
        final_confidence = 0.95

    # 4. Inferred / Implicit Emotions
    implicits = []
    if final_primary in ("frustration", "anger"):
        implicits.append("regret") if "silly" in user_message.lower() or "sorry" in user_message.lower() else implicits.append("resentment")
    elif final_primary == "sadness":
        if "alone" in user_message.lower():
            implicits.append("loneliness")
            
    # 5. Emotional Dimensions
    intensity = 0.4
    if final_primary != "neutral":
        intensity = 0.6
        if user_message.isupper():
            intensity += 0.2
        if "!" in user_message or "really" in user_message.lower() or "very" in user_message.lower():
            intensity += 0.15
        intensity = min(1.0, intensity)
        
    valence = "neutral"
    if final_primary in ("sadness", "frustration", "anger", "anxiety", "fear", "loneliness", "stress"):
        valence = "negative"
    elif final_primary in ("joy", "excitement", "relief"):
        valence = "positive"
        
    arousal = "moderate"
    if final_primary in ("frustration", "anger", "excitement", "panic"):
        arousal = "high"
    elif final_primary in ("sadness", "loneliness", "neutral"):
        arousal = "low"

    # 6. Situation and Target Analysis
    situation = "general"
    msg_clean = re.sub(r"[^\w\s]", "", user_message.lower())
    for sit, keywords in SITUATION_KEYWORDS.items():
        if any(k in msg_clean.split() or k in user_message.lower() for k in keywords):
            situation = sit
            break
            
    target = None
    if situation == "relationship":
        target = "girlfriend" if "gf" in user_message.lower() or "girlfriend" in user_message.lower() else "boyfriend" if "bf" in user_message.lower() or "boyfriend" in user_message.lower() else "partner"
    elif "i" in msg_clean.split() and final_primary in ("sadness", "frustration"):
        target = "self"

    # 7. User Need & Stage
    user_need = "listening"
    if final_primary in ("sadness", "loneliness"):
        user_need = "validation"
    elif final_primary in ("anxiety", "stress"):
        user_need = "grounding" if intensity >= 0.7 else "exploration"
    elif final_primary in ("joy", "excitement"):
        user_need = "celebration"

    stage = determine_conversation_stage(user_message, history, final_primary, intensity)

    risk_level = "low"
    if stage == "crisis":
        risk_level = "crisis"
    elif final_primary in ("sadness", "anxiety") and intensity >= 0.85:
        risk_level = "medium"

    # Uncertainty
    uncertainty = 0.5
    if explicits:
        uncertainty = 0.1
    elif final_primary == "neutral":
        uncertainty = 0.8

    return {
        "explicit_emotions": explicits,
        "implicit_emotions": implicits,
        "primary_emotion": final_primary,
        "secondary_emotion": secondary,
        "emotion_confidence": round(final_confidence, 2),
        "intensity": round(intensity, 2),
        "valence": valence,
        "arousal": arousal,
        "situation": situation,
        "target": target,
        "user_need": user_need,
        "conversation_stage": stage,
        "risk_level": risk_level,
        "uncertainty": round(uncertainty, 2)
    }


def select_response_strategy(
    signal: UserSignal, personalization: dict
) -> ResponsePlan:
    """Builds the strategic ResponsePlan from the UserSignal and user profile preferences."""
    primary_emo = signal.get("primary_emotion", "neutral")
    need = signal.get("user_need", "listening")
    intensity = signal.get("intensity", 0.4)
    stage = signal.get("conversation_stage", "reflection")
    risk = signal.get("risk_level", "low")

    # Precedence Strategy selection
    primary_strat = "LISTEN"
    secondary_strat = None
    should_ask_q = True
    should_offer_act = False
    
    if risk == "crisis":
        primary_strat = "SAFETY"
        should_ask_q = False
    elif stage == "seeking_advice":
        primary_strat = "PROBLEM_SOLVE"
        should_offer_act = True
    elif primary_emo == "joy":
        primary_strat = "CELEBRATE"
    elif need == "validation":
        primary_strat = "VALIDATE"
        secondary_strat = "REFLECT"
    elif need == "grounding":
        primary_strat = "GROUND"
        secondary_strat = "REGULATE"
        should_offer_act = True
    elif need == "exploration":
        primary_strat = "REFLECT"
        secondary_strat = "EXPLORE"

    # Tone mapping
    tone = "reflective"
    if primary_emo in ("frustration", "anger"):
        tone = "empathetic"
    elif primary_emo in ("anxiety", "stress"):
        tone = "calming" if intensity >= 0.7 else "reassuring"
    elif primary_emo == "sadness":
        tone = "empathetic"
    elif primary_emo == "joy":
        tone = "energetic"
    elif stage == "crisis":
        tone = "calming"

    # Personalization adaptation (Phase 9)
    avoid_list = ["generic reassurance", "therapy framing", "unpacking", "repeated templates"]
    
    advice_pref = str(personalization.get("advice_preference") or "").lower()
    if "listen" in advice_pref or "mostly listening" in advice_pref:
        if primary_strat == "PROBLEM_SOLVE":
            primary_strat = "LISTEN"
            secondary_strat = "REFLECT"
            avoid_list.append("direct advice")
            avoid_list.append("unsolicited suggestions")
        should_offer_act = False

    desired_length = "medium"
    style = str(personalization.get("communication_style") or "").lower()
    if "short" in style or "concise" in style or "brief" in style:
        desired_length = "short"
    elif "detail" in style or "deep" in style or "long" in style:
        desired_length = "long"

    return {
        "primary_strategy": primary_strat,
        "secondary_strategy": secondary_strat,
        "should_ask_question": should_ask_q,
        "should_offer_action": should_offer_act,
        "should_use_memory": len(signal.get("explicit_emotions", [])) > 0,
        "desired_length": desired_length,
        "tone": tone,
        "avoid": avoid_list
    }


# --- Response Quality Critic (Phase 10) ---

class ResponseCritic:
    """Performs deterministic quality audits on candidate responses."""

    FORBIDDEN_THERAPIST_PHRASES = [
        "understand your concern", "empathize with your", "must be difficult",
        "must be challenging", "must be tough", "as an ai", "here to support you",
        "understand how you feel", "let's explore", "let's unpack", "unpack that",
        "explore that", "validate your"
    ]

    GENERIC_EMPATHY_OPENERS = [
        "that sounds tough", "that sounds heavy", "i'm sorry you're feeling",
        "i'm sorry to hear", "that must be really", "i can imagine how"
    ]

    def audit(
        self,
        candidate: str,
        signal: UserSignal,
        plan: ResponsePlan,
        recent_responses: List[str]
    ) -> List[str]:
        """Runs quality checks and returns a list of failed check identifiers."""
        failed = []
        text_lower = candidate.lower().strip()

        # 1. Clinical/Therapist Phrasing Check
        if any(p in text_lower for p in self.FORBIDDEN_THERAPIST_PHRASES):
            failed.append("TOO_CLINICAL")

        # 2. Generic Empathy / Template Check
        if any(text_lower.startswith(op) for op in self.GENERIC_EMPATHY_OPENERS):
            failed.append("GENERIC_EMPATHY")

        # 3. Repetition Check (Phase 8)
        if recent_responses:
            for past in recent_responses[-3:]:
                past_clean = re.sub(r"[^\w\s]", "", past.lower()).strip()
                cand_clean = re.sub(r"[^\w\s]", "", text_lower).strip()
                
                if past_clean and cand_clean:
                    past_words = set(past_clean.split())
                    cand_words = set(cand_clean.split())
                    intersect = past_words & cand_words
                    union = past_words | cand_words
                    if union and (len(intersect) / len(union)) > 0.45:
                        failed.append("REPEATED_PHRASE")
                        break

        # 4. Multiple Questions Check
        if candidate.count("?") > 1:
            failed.append("MULTIPLE_QUESTIONS")

        # 5. Robotic List Check
        if any(line.strip().startswith(("-", "*", "1.", "2.")) for line in candidate.splitlines()):
            failed.append("ROBOTIC_LIST")

        # 6. Length mismatch
        word_count = len(text_lower.split())
        pref_len = plan.get("desired_length", "medium")
        if pref_len == "short" and word_count > 45:
            failed.append("TOO_VERBOSE")

        # 7. Unnecessary disclaimer check
        if "as an ai" in text_lower or "mental health companion" in text_lower or "cannot provide" in text_lower:
            failed.append("UNNECESSARY_DISCLAIMER")

        # 8. Unsupported Inference / Hallucinated Empathy Check
        absolute_assertions = ["always", "obviously", "clearly", "definitely", "stuck in a loop", "treated unfairly", "don't understand you", "hurt you"]
        uncertainty_modifiers = ["maybe", "sounds like", "could be", "seems", "perhaps", "wonder", "might", "potentially", "i hear", "sounds", "like"]
        
        has_absolute = any(a in text_lower for a in absolute_assertions)
        has_uncertainty = any(u in text_lower for u in uncertainty_modifiers)
        
        if has_absolute and not has_uncertainty:
            failed.append("UNSUPPORTED_INFERENCE")

        return failed


response_critic = ResponseCritic()

