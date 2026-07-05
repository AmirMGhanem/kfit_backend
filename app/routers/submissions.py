import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.submissions import create_onboarding_submission

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

_REQUIRED_IDENTITY_GROUPS = (
    ("firstname", "firstName"),  # accept either casing
    ("lastname", "lastName"),
    ("phone",),
)


class OnboardingSubmissionIn(BaseModel):
    form_slug: Literal["onboarding"]
    form_version: int = Field(ge=1)
    client_submitted_at: datetime | None = None
    answers: dict[str, str | list[str]]

    @field_validator("answers")
    @classmethod
    def _require_identity(
        cls, v: dict[str, str | list[str]]
    ) -> dict[str, str | list[str]]:
        missing = [
            group[0]
            for group in _REQUIRED_IDENTITY_GROUPS
            if not any(v.get(k) for k in group)
        ]
        if missing:
            raise ValueError(f"missing required identity fields: {missing}")
        return v


class OnboardingSubmissionOut(BaseModel):
    submission_id: uuid.UUID
    client_id: uuid.UUID
    calculation_id: uuid.UUID | None = None


@router.post(
    "/onboarding",
    response_model=OnboardingSubmissionOut,
    status_code=201,
)
async def submit_onboarding(
    body: OnboardingSubmissionIn,
    session: AsyncSession = Depends(get_session),
) -> OnboardingSubmissionOut:
    submission_id, client_id, calculation_id = await create_onboarding_submission(
        session, body.answers
    )
    return OnboardingSubmissionOut(
        submission_id=submission_id,
        client_id=client_id,
        calculation_id=calculation_id,
    )
