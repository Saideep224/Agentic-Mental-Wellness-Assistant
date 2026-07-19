"""
Esona Emotional Intelligence V2 - 100-Scenario Evaluation Suite and Unit Tests.
"""

import pytest
from app.services.emotional_intelligence import (
    build_user_signal,
    select_response_strategy,
    detect_explicit_emotion,
    determine_conversation_stage,
    response_critic
)

def test_detect_explicit_emotion():
    # 1. English matches
    assert "frustration" in detect_explicit_emotion("I am really frustrated right now")
    assert "sadness" in detect_explicit_emotion("feeling so low today")
    assert "anxiety" in detect_explicit_emotion("I feel anxious about the tomorrow exam")
    assert "stress" in detect_explicit_emotion("overwhelmed by work")
    assert "loneliness" in detect_explicit_emotion("I feel all alone")
    assert "joy" in detect_explicit_emotion("so glad that happened")
    assert "confusion" in detect_explicit_emotion("I'm confused about my feelings")

    # 2. Telugu code-mixed transliterated matches
    assert "frustration" in detect_explicit_emotion("naaku chirak ga undi")
    assert "sadness" in detect_explicit_emotion("badhaga undi chaala")
    assert "anxiety" in detect_explicit_emotion("chala bayanga undi next steps")
    assert "anxiety" in detect_explicit_emotion("kangaruga undi exam gurinchi")
    assert "confusion" in detect_explicit_emotion("em ardam kavatam ledu em cheyalo")


def test_determine_conversation_stage():
    # Opening stage
    assert determine_conversation_stage("hey buddy", [], "neutral", 0.4) == "opening"
    
    # Casual
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]
    assert determine_conversation_stage("yo", history, "neutral", 0.3) == "opening"  # small history
    
    history_long = [
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"},
        {"role": "user", "content": "how are you"}, {"role": "assistant", "content": "doing good"},
        {"role": "user", "content": "great"}, {"role": "assistant", "content": "chill"}
    ]
    assert determine_conversation_stage("sup", history_long, "neutral", 0.3) == "casual"

    # Disclosure
    assert determine_conversation_stage("feeling low", [], "sadness", 0.6) == "disclosure"
    
    # Deepening / Escalation
    history_disc = [
        {"role": "user", "content": "feeling low"}, {"role": "assistant", "content": "sorry to hear that"},
    ]
    assert determine_conversation_stage("it's just a lot", history_disc, "sadness", 0.7) == "deepening"
    assert determine_conversation_stage("I hate this", history_disc, "frustration", 0.9) == "escalation"

    # Advice / Action
    assert determine_conversation_stage("what should i do", history_disc, "neutral", 0.4) == "seeking_advice"
    assert determine_conversation_stage("will try that", history_disc, "neutral", 0.4) == "ready_for_action"

    # Crisis
    assert determine_conversation_stage("want to die", [], "sadness", 1.0) == "crisis"


def test_build_user_signal_explicit_override():
    # Test that explicit emotion overrides neutral prediction
    personalization = {"advice_preference": "Friendly and Casual"}
    signal = build_user_signal(
        user_message="I am really frustrated right now",
        history=[],
        personalization=personalization,
        blended_scores=[0.1, 0.7, 0.05, 0.05, 0.05, 0.05, 0.0, 0.0, 0.0]  # neutral is high
    )
    assert signal["primary_emotion"] == "frustration"
    assert signal["emotion_confidence"] == 0.95
    assert signal["valence"] == "negative"


def test_select_response_strategy():
    # 1. Warm grounded / Calming for high anxiety
    signal_anx = {
        "primary_emotion": "anxiety",
        "intensity": 0.8,
        "user_need": "grounding",
        "conversation_stage": "disclosure",
        "risk_level": "low"
    }
    plan = select_response_strategy(signal_anx, {})
    assert plan["tone"] == "calming"
    assert plan["primary_strategy"] == "GROUND"
    assert plan["should_offer_action"] is True

    # 2. Advice preference restriction (listening only)
    signal_prob = {
        "primary_emotion": "sadness",
        "intensity": 0.5,
        "user_need": "exploration",
        "conversation_stage": "seeking_advice",
        "risk_level": "low"
    }
    plan_listen = select_response_strategy(signal_prob, {"advice_preference": "Mostly Listening, Less Advice"})
    assert plan_listen["primary_strategy"] == "LISTEN"
    assert "direct advice" in plan_listen["avoid"]
    assert plan_listen["should_offer_action"] is False


def test_response_critic_audits():
    # 1. Too clinical
    signal = {"primary_emotion": "sadness", "intensity": 0.5}
    plan = {"desired_length": "medium", "avoid": []}
    assert "TOO_CLINICAL" in response_critic.audit("let me unpack that pattern for you", signal, plan, [])

    # 2. Generic empathy opener
    assert "GENERIC_EMPATHY" in response_critic.audit("that sounds tough, let's talk", signal, plan, [])

    # 3. Repetition guard
    past_responses = ["aw sorry about that bro", "that is annoying fr"]
    assert "REPEATED_PHRASE" in response_critic.audit("aw sorry about that bro", signal, plan, past_responses)

    # 4. Multiple questions
    assert "MULTIPLE_QUESTIONS" in response_critic.audit("how are you? want to talk?", signal, plan, [])

    # 5. Robotic list
    assert "ROBOTIC_LIST" in response_critic.audit("here is a list:\n- step 1\n- step 2", signal, plan, [])


def test_100_scenarios_evaluation_suite():
    """
    100-scenario evaluation suite.
    Iterates through 100 distinct user messages covering various scenarios and verifies
    the correctness of emotional parsing, stage tracking, and strategy planning.
    Calculates a final quality score (maximum 100).
    """
    scenarios = [
        # --- Group 1: Greetings & Banter (1-15) ---
        ("hello", "neutral", "opening"),
        ("hey esona!", "neutral", "opening"),
        ("what up bro", "neutral", "opening"),
        ("yo, you there?", "neutral", "opening"),
        ("just saying hi", "neutral", "opening"),
        ("chill day today", "neutral", "opening"),
        ("good morning", "neutral", "opening"),
        ("good night buddy", "neutral", "opening"),
        ("sup esona", "neutral", "opening"),
        ("hi there", "neutral", "opening"),
        ("yeah, agreed", "neutral", "reflection"),
        ("ok cool", "neutral", "casual"),
        ("lmao that's funny", "neutral", "casual"),
        ("haha true", "neutral", "casual"),
        ("thanks buddy", "neutral", "recovery"),
        
        # --- Group 2: Explicit Frustration & Anger (16-30) ---
        ("I am really frustrated right now", "frustration", "disclosure"),
        ("i'm so frustrated with my groupmates", "frustration", "disclosure"),
        ("feeling frustrated because nothing works", "frustration", "disclosure"),
        ("I feel angry and fed up", "frustration", "disclosure"),
        ("i'm pissed off at this boss", "frustration", "disclosure"),
        ("just so mad about my grade", "frustration", "disclosure"),
        ("highly annoyed at the delay", "frustration", "disclosure"),
        ("sick of this routine", "frustration", "disclosure"),
        ("fed up with my partner arguing", "frustration", "disclosure"),
        ("I hate how they treated me", "frustration", "disclosure"),
        ("it is just so annoying", "frustration", "disclosure"),
        ("chirak ga undi chaala", "frustration", "disclosure"),
        ("chiraku ga undi college gurinchi", "frustration", "disclosure"),
        ("chirakga undi roomie tho", "frustration", "disclosure"),
        ("ciraku ga undi life", "frustration", "disclosure"),

        # --- Group 3: Sadness & Loneliness (31-50) ---
        ("feeling low today", "sadness", "disclosure"),
        ("i feel really down", "sadness", "disclosure"),
        ("I am sad because she left", "sadness", "disclosure"),
        ("heartbroken right now", "sadness", "disclosure"),
        ("crying in my room", "sadness", "disclosure"),
        ("feeling sad and empty", "sadness", "disclosure"),
        ("devastated by the bad news", "sadness", "disclosure"),
        ("depressed about placements", "sadness", "disclosure"),
        ("feeling lonely tonight", "loneliness", "disclosure"),
        ("I am all alone in this campus", "loneliness", "disclosure"),
        ("feel lonely and disconnected", "loneliness", "disclosure"),
        ("nobody talks to me here", "loneliness", "disclosure"),
        ("miss my family a lot", "sadness", "disclosure"),
        ("feeling empty inside", "sadness", "disclosure"),
        ("everything feels hopeless", "sadness", "disclosure"),
        ("badhaga undi chaala", "sadness", "disclosure"),
        ("badha ga undi job raledu ani", "sadness", "disclosure"),
        ("baadhaga undi life", "sadness", "disclosure"),
        ("bhada ga undi placement poyindi", "sadness", "disclosure"),
        ("edo feel ga undi badhaga", "sadness", "disclosure"),

        # --- Group 4: Anxiety & Fear (51-70) ---
        ("I am anxious about my presentations", "anxiety", "disclosure"),
        ("feeling anxious for no reason", "anxiety", "disclosure"),
        ("so worried about my future", "anxiety", "disclosure"),
        ("having a panic attack", "anxiety", "disclosure"),
        ("scared of failing this year", "anxiety", "disclosure"),
        ("afraid of what comes next", "anxiety", "disclosure"),
        ("terrified about the results tomorrow", "anxiety", "disclosure"),
        ("nervous about meeting them", "anxiety", "disclosure"),
        ("overthinking everything again", "anxiety", "disclosure"),
        ("tension ga undi exam gurinchi", "anxiety", "disclosure"),
        ("kangaruga undi results ki", "anxiety", "disclosure"),
        ("kangaru ga undi placements", "anxiety", "disclosure"),
        ("kangatuga undi presentation ante", "anxiety", "disclosure"),
        ("bhayam ga undi future gurinchi", "anxiety", "disclosure"),
        ("bhayamga undi interview ante", "anxiety", "disclosure"),
        ("bayanga undi fail avthana ani", "anxiety", "disclosure"),
        ("bayan ga undi life", "anxiety", "disclosure"),
        ("so scared of being alone", "anxiety", "disclosure"),
        ("dread going to college", "anxiety", "disclosure"),
        ("panicking right now", "anxiety", "disclosure"),

        # --- Group 5: Stress & Overwhelm (71-85) ---
        ("I am stressed out", "stress", "disclosure"),
        ("feeling stressed about deadline", "stress", "disclosure"),
        ("too much pressure from parents", "stress", "disclosure"),
        ("overwhelmed by all these tasks", "stress", "disclosure"),
        ("exhausted after a long day", "stress", "disclosure"),
        ("completely burned out", "stress", "disclosure"),
        ("burnt out with coding", "stress", "disclosure"),
        ("stress ga undi exams", "stress", "disclosure"),
        ("struggling with finances", "stress", "disclosure"),
        ("debt is stressing me out", "stress", "disclosure"),
        ("cannot cope with this schedule", "stress", "disclosure"),
        ("tired of everything", "stress", "disclosure"),
        ("deadlines are swamping me", "stress", "disclosure"),
        ("too busy to breathe", "stress", "disclosure"),
        ("pressure is high", "stress", "disclosure"),

        # --- Group 6: Mixed, Confused & Crisis (86-100) ---
        ("confused about my career path", "confusion", "disclosure"),
        ("dont know what to feel", "confusion", "disclosure"),
        ("em ardam kavatam ledu next step", "confusion", "disclosure"),
        ("em ardamga ledu chirakga undi", "confusion", "disclosure"),
        ("not sure what is wrong", "confusion", "disclosure"),
        ("em ardamkavatledu em cheyalo", "confusion", "disclosure"),
        ("what should i do about this?", "neutral", "seeking_advice"),
        ("how to solve this fight?", "neutral", "seeking_advice"),
        ("can you suggest something?", "neutral", "seeking_advice"),
        ("will try this grounding exercise", "neutral", "ready_for_action"),
        ("makes sense, i will do it", "neutral", "ready_for_action"),
        ("I want to die", "sadness", "crisis"),
        ("kill myself", "sadness", "crisis"),
        ("suicidal thoughts", "sadness", "crisis"),
        ("planning to end it", "sadness", "crisis"),
    ]

    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    personalization = {"advice_preference": "Friendly and Casual"}
    
    passed_scenarios = 0
    
    for idx, (message, expected_emo, expected_stage) in enumerate(scenarios):
        # We simulate build_user_signal
        # (blended scores mock: 8th index is neutral, all others zero)
        blended_scores = [0.0] * 9
        blended_scores[8] = 1.0  # mock classifier defaults to neutral
        
        signal = build_user_signal(
            user_message=message,
            history=history if expected_stage != "opening" else [],
            personalization=personalization,
            blended_scores=blended_scores
        )
        
        # Verify emotion detection matches expected (case-insensitive)
        pred_emo = signal["primary_emotion"].lower()
        if expected_emo == "crisis":
            is_emo_correct = signal["risk_level"] == "crisis"
        else:
            is_emo_correct = pred_emo == expected_emo or (expected_emo == "stress" and pred_emo == "stress")
            
        is_stage_correct = signal["conversation_stage"] == expected_stage
        
        if is_emo_correct and is_stage_correct:
            passed_scenarios += 1
        else:
            # Log failure details for debugging
            print(
                f"[Scenario {idx+1} Failed] Message: '{message}' | "
                f"Expected Emotion: {expected_emo}, Got: {pred_emo} ({'CORRECT' if is_emo_correct else 'FAIL'}) | "
                f"Expected Stage: {expected_stage}, Got: {signal['conversation_stage']} ({'CORRECT' if is_stage_correct else 'FAIL'})"
            )
            
    quality_score = int((passed_scenarios / len(scenarios)) * 100)
    print(f"Total scenarios passed: {passed_scenarios}/100. V2 Quality Score: {quality_score}/100")
    
    # Assert quality threshold: V2 must pass at least 95/100 of these complex test cases
    assert quality_score >= 95


def test_v4_rules_engine():
    import os
    os.environ["FORCE_SEMANTIC_RULES"] = "true"
    try:
        from app.services.emotion_service import detect_semantic_emotion
        res = detect_semantic_emotion("I stopped talking to my reshma. I feel like she is not feeling the same way as I do in our bond . I pretty say abt it")
        assert res is not None
        assert res["primary"] == "Heartbreak"
        assert res["secondary"] == "Loneliness"
        assert res["third"] == "Sadness"
        assert res["confidence"] >= 0.95
    finally:
        os.environ.pop("FORCE_SEMANTIC_RULES", None)


def test_never_neutral_overrides():
    import os
    os.environ["FORCE_SEMANTIC_RULES"] = "true"
    try:
        from app.services.emotion_service import detect_semantic_emotion
        
        # Test "I miss her."
        res1 = detect_semantic_emotion("I miss her.")
        assert res1 is not None
        assert res1["primary"] == "Sadness"
        
        # Test "My parents are disappointed."
        res2 = detect_semantic_emotion("My parents are disappointed.")
        assert res2 is not None
        assert res2["primary"] == "Family Pressure"
        
        # Test "I failed."
        res3 = detect_semantic_emotion("I failed.")
        assert res3 is not None
        assert res3["primary"] == "Academic Stress"
        
        # Test "I don't know why I'm alive."
        res4 = detect_semantic_emotion("I don't know why I'm alive.")
        assert res4 is not None
        assert res4["primary"] == "Hopelessness"
        
        # Test "I feel empty."
        res5 = detect_semantic_emotion("I feel empty.")
        assert res5 is not None
        assert res5["primary"] == "Emotional Numbness"
        
        # Test "I'm scared."
        res6 = detect_semantic_emotion("I'm scared.")
        assert res6 is not None
        assert res6["primary"] == "Fear"
        
        # Test "I can't sleep."
        res7 = detect_semantic_emotion("I can't sleep.")
        assert res7 is not None
        assert res7["primary"] == "Anxiety"
        
        # Test "I keep thinking."
        res8 = detect_semantic_emotion("I keep thinking.")
        assert res8 is not None
        assert res8["primary"] == "Overthinking"
        
        # Test "I'm tired of everything."
        res9 = detect_semantic_emotion("I'm tired of everything.")
        assert res9 is not None
        assert res9["primary"] == "Hopelessness"
    finally:
        os.environ.pop("FORCE_SEMANTIC_RULES", None)
