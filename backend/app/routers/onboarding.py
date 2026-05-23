"""
Onboarding router – submit questionnaire answers and check status.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.onboarding import OnboardingResponse
from app.routers.auth import get_current_user
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
    Submit all 20 onboarding answers.

    Persists the responses, runs the AI-powered onboarding analyzer
    to build the emotional profile, and marks onboarding as complete.
    """
    if current_user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed",
        )

    # Delete any partial previous attempts
    existing = await db.execute(
        select(OnboardingResponse).where(
            OnboardingResponse.user_id == current_user.id
        )
    )
    for old in existing.scalars().all():
        await db.delete(old)
    await db.flush()

    # Persist all 20 answers
    for answer in body.answers:
        response = OnboardingResponse(
            user_id=current_user.id,
            question_id=answer.question_id,
            category=answer.category,
            selected_option=answer.selected_option,
            custom_text=answer.custom_text,
            custom_answer=answer.custom_text,
        )
        db.add(response)

    await db.flush()

    # Build emotional profile via the analyzer service
    answers_dicts = [a.model_dump() for a in body.answers]
    await analyze_onboarding(
        user_id=current_user.id,
        answers=answers_dicts,
        db=db,
    )

    # Mark onboarding as complete
    current_user.onboarding_completed = True
    await db.flush()

    return {"status": "success", "message": "Onboarding completed successfully"}


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check the current onboarding completion status."""
    result = await db.execute(
        select(func.count(OnboardingResponse.id)).where(
            OnboardingResponse.user_id == current_user.id
        )
    )
    count = result.scalar() or 0

    return OnboardingStatusResponse(
        onboarding_completed=current_user.onboarding_completed,
        total_questions=20,
        answers_submitted=count,
    )
