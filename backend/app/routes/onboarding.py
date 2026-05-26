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
)
from app.services.onboarding_analyzer import analyze_onboarding

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


QUESTION_TEXT_BY_ID = {
    1: "After a tiring day, what do you usually do?",
    2: "Which line sounds most like you?",
    3: "What drains your energy the most?",
    4: "How do you usually text when you're upset?",
    5: "Your mind's default mode lately?",
    6: "What keeps your mind busy at night?",
    7: "What do you do first when stressed?",
    8: "What affects your mood the fastest?",
    9: "How often do you feel mentally exhausted?",
    10: "If your emotions were weather lately, they'd be...",
    11: "What helps you escape reality?",
    12: "What content do you connect with most?",
    13: "Where do you feel safest emotionally?",
    14: "Which hobby feels most 'you'?",
    15: "What usually improves your mood fastest?",
    16: "How should this AI talk to you?",
    17: "What type of replies annoy you most?",
    18: "When emotionally low, what helps more?",
    19: "Your social battery lately?",
    20: "What do you wish people understood about you?",
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
    Accept 20 questions with selected answers, store them in the DB,
    and trigger the background process to analyze them and create the initial EmotionalProfile.
    """
    # 1. Validation check (must be exactly 20 answers)
    if len(body.answers) != 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected exactly 20 answers, got {len(body.answers)}",
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

    # Mark user onboarding as complete on User table (profiles)
    current_user.onboarding_completed = True
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
    )


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
