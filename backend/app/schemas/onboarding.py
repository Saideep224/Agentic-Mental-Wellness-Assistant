"""
Onboarding request/response schemas.
"""

from pydantic import BaseModel, Field


class OnboardingAnswer(BaseModel):
    """A single answer from the onboarding questionnaire."""
    question_id: int = Field(..., ge=1, le=20)
    category: str = Field(
        ...,
        description="One of: personality, emotions, comfort, communication",
    )
    selected_answers: list[str] = Field(default_factory=list)
    custom_answer: str | None = Field(default=None, max_length=2000)


class OnboardingSubmitRequest(BaseModel):
    """Body for POST /api/onboarding/submit – all 20 answers at once."""
    answers: list[OnboardingAnswer] = Field(
        ..., min_length=20, max_length=20,
        description="Exactly 20 onboarding answers",
    )


class OnboardingStatusResponse(BaseModel):
    """Response for GET /api/onboarding/status."""
    onboarding_completed: bool
    total_questions: int = 20
    answers_submitted: int = 0
