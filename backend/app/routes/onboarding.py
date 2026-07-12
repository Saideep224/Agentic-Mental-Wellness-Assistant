import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.onboarding import UserAnswer
from app.routes.auth import get_current_user
from app.schemas.onboarding import (
    OnboardingSubmitRequest,
    OnboardingStatusResponse,
    OnboardingAnswer,
    OnboardingStepRequest,
)
from app.services.onboarding_analyzer import analyze_onboarding

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


QUESTION_TEXT_BY_ID = {
    1: "What is your profession or current occupation?",
    2: "What field are you studying or working in?",
    3: "What is the biggest challenge you are currently facing?",
    4: "How do you prefer to receive advice?",
    5: "What would you like me to help you with the most?",
    6: "After a tiring day, what do you usually do?",
    7: "Which line sounds most like you?",
    8: "What drains your energy the most?",
    9: "How do you usually text when you're upset?",
    10: "Your mind's default mode lately?",
    11: "What keeps your mind busy at night?",
    12: "What do you do first when stressed?",
    13: "What affects your mood the fastest?",
    14: "How often do you feel mentally exhausted?",
    15: "If your emotions were weather lately, they'd be...",
    16: "What helps you escape reality?",
    17: "What content do you connect with most?",
    18: "Where do you feel safest emotionally?",
    19: "Which hobby feels most 'you'?",
    20: "What usually improves your mood fastest?",
    21: "How should this AI talk to you?",
    22: "What type of replies annoy you most?",
    23: "When emotionally low, what helps more?",
    24: "Your social battery lately?",
    25: "What do you wish people understood about you?",
    26: "What is your gender?",
}


def derive_personality_profile(answers: list[dict]) -> dict:
    selected = {
        value
        for answer in answers
        for value in (answer.get("selected_answers") or [])
    }

    def has(*values: str) -> bool:
        return any(value in selected for value in values)

    if has("straightforward", "handle_truth"):
        communication_style = "direct"
    elif has("gentle", "comfort", "listening"):
        communication_style = "gentle"
    elif has("close_friend", "smart_chill"):
        communication_style = "casual"
    else:
        communication_style = "warm"

    if has("overthink", "overthinking", "future", "anxious"):
        stress_pattern = "overthinking"
    elif has("isolate", "go_silent", "need_space"):
        stress_pattern = "shutdown"
    elif has("pressure", "career"):
        stress_pattern = "performance_pressure"
    else:
        stress_pattern = "mixed"

    return {
        "communication_style": communication_style,
        "humor_preference": has("humor_hide", "distraction", "laugh", "memes"),
        "reply_length": "short" if has("short_replies", "long_paragraphs") else "medium",
        "stress_pattern": stress_pattern,
        "support_preference": "practical_advice" if has("advice") else ("listening" if has("listening", "need_space") else "validation"),
        "emotional_tone": "numb" if has("numb") else ("intense" if has("storms", "unpredictable") else ("calm" if has("calm") else "reflective")),
    }


async def analyze_onboarding_background(user_id: uuid.UUID, answers: list):
    """Run onboarding profiling in background with a dedicated DB session context."""
    from app.database import async_session_maker
    async with async_session_maker() as session:
        try:
            await analyze_onboarding(user_id, answers, session)
            await session.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Background onboarding analysis failed: {e}", exc_info=True)


@router.post("/answer", status_code=status.HTTP_200_OK)
async def save_onboarding_answer(
    answer: OnboardingAnswer,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save an individual onboarding answer live to the database (user_question_answers table)."""
    # Check if this answer already exists
    result = await db.execute(
        select(UserAnswer).where(
            UserAnswer.user_id == current_user.id,
            UserAnswer.question_id == answer.question_id,
        )
    )
    db_ans = result.scalar_one_or_none()

    if db_ans:
        db_ans.category = answer.category
        db_ans.selected_answers = answer.selected_answers
        db_ans.custom_answer = answer.custom_answer
    else:
        db_ans = UserAnswer(
            user_id=current_user.id,
            question_id=answer.question_id,
            question_text=QUESTION_TEXT_BY_ID.get(answer.question_id, ""),
            category=answer.category,
            selected_answers=answer.selected_answers,
            custom_answer=answer.custom_answer,
        )
        db.add(db_ans)

    await db.flush()

    # Live save to UserPersonalProfile if it is one of the first 5 background questions
    val = None
    if answer.custom_answer and answer.custom_answer.strip():
        val = answer.custom_answer.strip()
    elif answer.selected_answers:
        val = answer.selected_answers[0]
        if val == "other" and answer.custom_answer:
            val = answer.custom_answer
            
    if val and answer.question_id in (1, 2, 3, 4, 5, 26):
        from app.services.profile_service import profile_service
        profile_map = {
            1: "profession",
            2: "field_of_work",
            3: "current_challenge",
            4: "advice_preference",
            5: "primary_support_need",
            26: "gender"
        }
        field_name = profile_map[answer.question_id]
        await profile_service.update_profile(db, current_user.id, {field_name: val})
        await db.flush()

    await db.commit()
    return {"message": "Answer saved live."}


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_onboarding(
    body: OnboardingSubmitRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept 26 questions with selected answers, store them in the DB,
    and trigger the background process to analyze them and create the initial EmotionalProfile.
    """
    # 1. Validation check (must be exactly 26 answers)
    if len(body.answers) != 26:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected exactly 26 answers, got {len(body.answers)}",
        )

    # 2. Upsert responses so edits update existing answers without duplicates.
    db_responses = []
    answers_to_analyze = []
    for ans in body.answers:
        result = await db.execute(
            select(UserAnswer).where(
                UserAnswer.user_id == current_user.id,
                UserAnswer.question_id == ans.question_id,
            )
        )
        db_ans = result.scalar_one_or_none()
        if db_ans:
            db_ans.question_text = QUESTION_TEXT_BY_ID.get(ans.question_id, db_ans.question_text)
            db_ans.category = ans.category
            db_ans.selected_answers = ans.selected_answers
            db_ans.custom_answer = ans.custom_answer
        else:
            db_ans = UserAnswer(
                user_id=current_user.id,
                question_id=ans.question_id,
                question_text=QUESTION_TEXT_BY_ID.get(ans.question_id, ""),
                category=ans.category,
                selected_answers=ans.selected_answers,
                custom_answer=ans.custom_answer,
            )
            db.add(db_ans)
        db_responses.append(db_ans)
        
        answers_to_analyze.append({
            "question_id": ans.question_id,
            "category": ans.category,
            "selected_answers": ans.selected_answers,
            "custom_answer": ans.custom_answer,
        })

    # Extract background values for UserPersonalProfile
    profile_updates = {}
    for ans in body.answers:
        val = None
        if ans.custom_answer and ans.custom_answer.strip():
            val = ans.custom_answer.strip()
        elif ans.selected_answers:
            val = ans.selected_answers[0]
            if val == "other" and ans.custom_answer:
                val = ans.custom_answer

        if val:
            if ans.question_id == 1:
                profile_updates["profession"] = val
            elif ans.question_id == 2:
                profile_updates["field_of_work"] = val
            elif ans.question_id == 3:
                profile_updates["current_challenge"] = val
            elif ans.question_id == 4:
                profile_updates["advice_preference"] = val
            elif ans.question_id == 5:
                profile_updates["primary_support_need"] = val

    if profile_updates:
        from app.services.profile_service import profile_service
        await profile_service.update_profile(db, current_user.id, profile_updates)
        await db.flush()

    # Mark user onboarding as complete on User table (profiles)
    current_user.onboarding_completed = True
    current_user.personality_profile = derive_personality_profile(answers_to_analyze)
    await db.flush()
    await db.commit()

    # 4. Queue the heavy AI analysis as a background task
    background_tasks.add_task(analyze_onboarding_background, current_user.id, answers_to_analyze)

    return {"message": "Onboarding answers saved successfully. Analysis running in background."}


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the user has completed onboarding and how many questions are answered."""
    result = await db.execute(
        select(func.count(UserAnswer.id)).where(
            UserAnswer.user_id == current_user.id
        )
    )
    count = result.scalar() or 0

    return OnboardingStatusResponse(
        onboarding_completed=current_user.onboarding_completed,
        answers_submitted=count,
        onboarding_step=current_user.onboarding_step or 1,
    )


@router.post("/step", status_code=status.HTTP_200_OK)
async def save_onboarding_step(
    body: OnboardingStepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save the current onboarding step/question_id the user is on."""
    current_user.onboarding_step = body.step
    db.add(current_user)
    await db.commit()
    return {"message": "Onboarding step saved."}


@router.get("/answers")
async def get_onboarding_answers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return saved Knowing Me answers, oldest question first."""
    result = await db.execute(
        select(UserAnswer)
        .where(UserAnswer.user_id == current_user.id)
        .order_by(UserAnswer.question_id.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(row.id),
            "question_id": row.question_id,
            "question_text": row.question_text,
            "category": row.category,
            "selected_answers": row.selected_answers,
            "custom_answer": row.custom_answer,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.post("/skip")
async def skip_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Immediately mark onboarding as completed without requiring any answers.
    Called when user clicks 'Skip Setup' or 'Skip — just chat'.
    """
    from app.models.user_profile import UserProfile
    from app.services.onboarding_service import onboarding_service

    profile_res = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_res.scalar_one_or_none()

    await onboarding_service.auto_complete_onboarding(db, current_user, profile)
    await db.commit()

    return {"success": True, "message": "Onboarding skipped. You can start chatting now!"}


@router.post("/recalculate")
async def recalculate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recalculate the user's emotional and personality profile based on
    their 26 onboarding answers and their latest chat history.
    """
    # 1. Fetch saved onboarding answers
    result = await db.execute(
        select(UserAnswer)
        .where(UserAnswer.user_id == current_user.id)
        .order_by(UserAnswer.question_id.asc())
    )
    rows = result.scalars().all()
    
    if not rows:
        return {"success": True, "message": "No onboarding answers to recalculate."}
        
    answers_to_analyze = [
        {
            "question_id": r.question_id,
            "category": r.category,
            "selected_answers": r.selected_answers,
            "custom_answer": r.custom_answer,
        }
        for r in rows
    ]
    
    # Run the profiling synchronously to ensure it completes
    await analyze_onboarding(current_user.id, answers_to_analyze, db)
    await db.commit()
    
    return {"success": True, "message": "Profile recalculated successfully based on answers and chat history."}


