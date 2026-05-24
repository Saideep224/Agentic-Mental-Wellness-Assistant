"""
Onboarding route – submit questionnaire answers and check status.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.onboarding import OnboardingResponse
from app.routes.auth import get_current_user
from app.schemas.onboarding import (
    OnboardingSubmitRequest,
    OnboardingStatusResponse,
)
from app.services.onboarding_analyzer import analyze_onboarding

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_onboarding(
    body: OnboardingSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept 20 questions with selected answers, store them in the DB,
    and trigger the async process to analyze them and create the initial EmotionalProfile.
    """
    # 1. Validation check (must be exactly 20 answers)
    if len(body.answers) != 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected exactly 20 answers, got {len(body.answers)}",
        )

    # 2. Delete existing onboarding responses if they exist for a clean slate
    await db.execute(
        select(OnboardingResponse).where(OnboardingResponse.user_id == current_user.id)
    )
    # SQLAlchemy ORM cascading delete works or manually clearing:
    # (Since we overwrite, we delete first)
    from sqlalchemy import delete
    await db.execute(
        delete(OnboardingResponse).where(OnboardingResponse.user_id == current_user.id)
    )
    await db.flush()

    # 3. Insert responses
    db_responses = []
    answers_to_analyze = []
    for ans in body.answers:
        db_ans = OnboardingResponse(
            user_id=current_user.id,
            question_id=ans.question_id,
            category=ans.category,
            selected_option=ans.selected_option,
            custom_text=ans.custom_text,
        )
        db.add(db_ans)
        db_responses.append(db_ans)
        
        answers_to_analyze.append({
            "question_id": ans.question_id,
            "category": ans.category,
            "selected_option": ans.selected_option,
            "custom_text": ans.custom_text,
        })

    # Mark user onboarding as complete
    current_user.onboarding_completed = True
    
    await db.flush()

    # 4. Analyze onboarding responses using OpenAI/Gemini to build the EmotionalProfile
    try:
        await analyze_onboarding(current_user.id, answers_to_analyze, db)
    except Exception as e:
        # Log error but don't fail registration
        import logging
        logging.getLogger(__name__).error(f"Failed to analyze onboarding: {e}", exc_info=True)

    await db.commit()
    return {"message": "Onboarding answers saved successfully. Profile built."}


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the user has completed onboarding and how many questions are answered."""
    result = await db.execute(
        select(func.count(OnboardingResponse.id)).where(
            OnboardingResponse.user_id == current_user.id
        )
    )
    count = result.scalar() or 0

    return OnboardingStatusResponse(
        completed=current_user.onboarding_completed,
        questions_answered=count,
    )
