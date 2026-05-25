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
    """Save an individual onboarding answer live to the database (user_answers table)."""
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

    # 2. Delete existing onboarding responses if they exist for a clean slate
    from sqlalchemy import delete
    await db.execute(
        delete(UserAnswer).where(UserAnswer.user_id == current_user.id)
    )
    await db.flush()

    # 3. Insert responses
    db_responses = []
    answers_to_analyze = []
    for ans in body.answers:
        db_ans = UserAnswer(
            user_id=current_user.id,
            question_id=ans.question_id,
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
        completed=current_user.onboarding_completed,
        questions_answered=count,
    )
