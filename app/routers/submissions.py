import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_staff
from app.services.submission_analyzer import repository as insight_repo
from app.services.submission_analyzer import run_analysis
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
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> OnboardingSubmissionOut:
    submission_id, client_id, calculation_id = await create_onboarding_submission(
        session, body.answers
    )
    # Fire-and-forget: analyze the submission for welcome-call notes after the
    # response is sent, so the client's submit stays instant.
    background_tasks.add_task(run_analysis, submission_id)
    return OnboardingSubmissionOut(
        submission_id=submission_id,
        client_id=client_id,
        calculation_id=calculation_id,
    )


class InsightItemOut(BaseModel):
    title: str
    detail: str


class SubmissionInsightOut(BaseModel):
    submission_id: uuid.UUID
    client_id: uuid.UUID
    status: str  # pending | ready | failed
    red_flags: list[InsightItemOut]
    pain_points: list[InsightItemOut]
    insights: list[InsightItemOut]
    model: str | None
    error: str | None


@router.get(
    "/{submission_id}/insights",
    response_model=SubmissionInsightOut,
    dependencies=[Depends(require_staff)],
)
async def get_submission_insights(
    submission_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> SubmissionInsightOut:
    row = await insight_repo.latest_for_submission(session, submission_id)
    if row is None:
        raise HTTPException(404, "insights not generated yet")
    return SubmissionInsightOut(
        submission_id=row.submission_id,
        client_id=row.client_id,
        status=row.status.value,
        red_flags=[InsightItemOut(**i) for i in row.red_flags],
        pain_points=[InsightItemOut(**i) for i in row.pain_points],
        insights=[InsightItemOut(**i) for i in row.insights],
        model=row.model,
        error=row.error,
    )
