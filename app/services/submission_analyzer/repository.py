"""Database access for the submission analyzer."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.submission import Submission
from app.models.submission_insight import InsightStatus, SubmissionInsight
from app.services.submission_analyzer.schemas import SubmissionAnalysis


async def fetch_submission(
    session: AsyncSession, submission_id: uuid.UUID
) -> Submission | None:
    return await session.get(Submission, submission_id)


async def save_ready(
    session: AsyncSession,
    submission: Submission,
    analysis: SubmissionAnalysis,
    model: str,
) -> uuid.UUID:
    row = SubmissionInsight(
        submission_id=submission.id,
        client_id=submission.client_id,
        status=InsightStatus.ready,
        red_flags=[i.model_dump() for i in analysis.red_flags],
        pain_points=[i.model_dump() for i in analysis.pain_points],
        insights=[i.model_dump() for i in analysis.insights],
        model=model,
    )
    session.add(row)
    await session.flush()
    return row.id


async def save_failed(
    session: AsyncSession,
    submission: Submission,
    model: str,
    error: str,
) -> uuid.UUID:
    row = SubmissionInsight(
        submission_id=submission.id,
        client_id=submission.client_id,
        status=InsightStatus.failed,
        model=model,
        error=error,
    )
    session.add(row)
    await session.flush()
    return row.id


async def latest_for_submission(
    session: AsyncSession, submission_id: uuid.UUID
) -> SubmissionInsight | None:
    return (
        await session.execute(
            select(SubmissionInsight)
            .where(SubmissionInsight.submission_id == submission_id)
            .order_by(SubmissionInsight.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
