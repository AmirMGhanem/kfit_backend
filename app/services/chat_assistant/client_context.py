"""
Load a client's structured records into a compact context block for the chat.

Deterministic SQL (never the LLM): pulls the client, their latest submission
(PII-stripped), latest calculation, recent meal plans, and welcome-call insights.
This is the "knows everything around the user" half of the hybrid RAG — the
knowledge base supplies methodology, this supplies the specific person.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation import Calculation
from app.models.client import Client
from app.models.meal_plan import MealPlan
from app.models.submission import Submission
from app.models.submission_insight import SubmissionInsight
from app.services.submission_analyzer.prompt import strip_pii


async def load_client_context(
    session: AsyncSession, client_id: uuid.UUID
) -> str | None:
    """Return a formatted context block, or None if the client is unknown."""
    client = await session.get(Client, client_id)
    if client is None:
        return None

    lines: list[str] = ["=== CLIENT CONTEXT ==="]
    lines.append(
        f"Name: {client.full_name} | gender: {client.gender.value if client.gender else '—'} "
        f"| status: {client.status.value} | since: {client.created_at.date()}"
    )

    submission = (
        await session.execute(
            select(Submission)
            .where(Submission.client_id == client_id)
            .order_by(Submission.submitted_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if submission is not None:
        clean = strip_pii(submission.payload)
        lines.append("Onboarding answers (PII-stripped):")
        lines.append(json.dumps(clean, ensure_ascii=False, indent=1))

    calc = (
        await session.execute(
            select(Calculation)
            .where(Calculation.client_id == client_id)
            .order_by(Calculation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if calc is not None:
        lines.append(
            f"Calculation: {calc.min_calories}-{calc.max_calories} kcal/day | "
            f"BMR {calc.bmr} | TEE {calc.tee} | goal {calc.goal.value} | "
            f"work {calc.work_type.value}"
        )

    plans = (
        (
            await session.execute(
                select(MealPlan)
                .where(MealPlan.client_id == client_id)
                .order_by(MealPlan.created_at.desc())
                .limit(3)
            )
        )
        .scalars()
        .all()
    )
    if plans:
        lines.append("Recent meal plans:")
        for p in plans:
            lines.append(
                f"  - {p.created_at.date()} status={p.status.value} "
                f"window {p.min_calories}-{p.max_calories} free={p.free_calories} "
                f"total={p.total_calories} meals={p.meals_count} snack={p.include_snack}"
            )

    insight = (
        await session.execute(
            select(SubmissionInsight)
            .where(SubmissionInsight.client_id == client_id)
            .order_by(SubmissionInsight.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if insight is not None and insight.status.value == "ready":

        def _titles(items: list[dict[str, Any]]) -> str:
            return "; ".join(i.get("title", "") for i in items) or "—"

        lines.append(f"Red flags: {_titles(insight.red_flags)}")
        lines.append(f"Pain points: {_titles(insight.pain_points)}")

    return "\n".join(lines)
