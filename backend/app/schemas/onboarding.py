"""
Onboarding request/response schemas.
"""

from pydantic import BaseModel, Field


class OnboardingAnswer(BaseModel):
    """A single answer from the onboarding questionnaire."""
    question_id: int = Field(..., ge=1, le=27)
    category: str = Field(
        ...,
        description="One of: background, personality, emotions, comfort, communication",
    )
    selected_answers: list[str] = Field(default_factory=list)
    custom_answer: str | None = Field(default=None, max_length=2000)


class OnboardingSubmitRequest(BaseModel):
    """Body for POST /api/onboarding/submit – all answers at once."""
    answers: list[OnboardingAnswer] = Field(
        ..., min_length=25, max_length=27,
        description="Onboarding answers",
    )


class OnboardingStepRequest(BaseModel):
    """Request for POST /api/onboarding/step."""
    step: int = Field(..., ge=1, le=27)


class OnboardingStatusResponse(BaseModel):
    """Response for GET /api/onboarding/status."""
    onboarding_completed: bool
    total_questions: int = 27
    answers_submitted: int = 0
    onboarding_step: int | None = 1
