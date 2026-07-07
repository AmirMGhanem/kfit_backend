"""
Meal-plan routes.

  POST /meal-plans/            generate a plan for a client (the button target)
  GET  /meal-plans/            list plans (optionally filtered by client_id)
  GET  /meal-plans/{plan_id}   one plan with its items

POST runs the meal-planner pipeline synchronously (build → propose → validate →
repair → persist) and returns the persisted plan with items, so the caller can
render straight from the response. A "failed" outcome is a normal 201 with
status="failed" + error (the generation ran but couldn't fit the window); only
provider/config problems are 5xx.

The pipeline persists via session.flush(); this router owns the commit.
All routes are staff-gated (admin or consultant).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.core.deps import require_staff
from app.models.calculation import Calculation
from app.models.meal_plan import MealPlan, MealPlanItem
from app.services.meal_planner import run_pipeline
from app.services.meal_planner.llm.openai_client import OpenAIClient

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


# ── I/O schemas ─────────────────────────────────────────────────────────────
class GenerateMealPlanIn(BaseModel):
    client_id: uuid.UUID
    # Number of generic (main) meals; a snack is added on top when requested.
    meals_count: int = Field(ge=1, le=6)
    include_snack: bool = False
    # Optional — defaults to the client's most recent calculation.
    calculation_id: uuid.UUID | None = None


class MealPlanItemOut(BaseModel):
    position: int
    meal_id: str
    name: str
    calories: int
    protein_calories: int | None
    meal_type: str
    protein_group_calories: int | None
    protein_group_grams: int | None
    carb_group_calories: int | None
    carb_group_protein_grams: int | None
    total_protein_grams: int | None
    payload: dict[str, object]


class MealPlanOut(BaseModel):
    """Summary — no items."""

    id: str
    client_id: str
    calculation_id: str
    status: str
    min_calories: int
    max_calories: int
    free_calories: int | None
    meals_count: int
    include_snack: bool
    total_calories: int | None
    total_protein_calories: int | None
    model: str | None
    created_at: str


class MealPlanDetailOut(MealPlanOut):
    """Summary + the selected meals + failure reason."""

    error: str | None
    items: list[MealPlanItemOut]


# ── Serialization ───────────────────────────────────────────────────────────
def _summary(p: MealPlan) -> MealPlanOut:
    return MealPlanOut(
        id=str(p.id),
        client_id=str(p.client_id),
        calculation_id=str(p.calculation_id),
        status=p.status.value,
        min_calories=p.min_calories,
        max_calories=p.max_calories,
        free_calories=p.free_calories,
        meals_count=p.meals_count,
        include_snack=p.include_snack,
        total_calories=p.total_calories,
        total_protein_calories=p.total_protein_calories,
        model=p.model,
        created_at=p.created_at.isoformat(),
    )


def _detail(p: MealPlan) -> MealPlanDetailOut:
    return MealPlanDetailOut(
        **_summary(p).model_dump(),
        error=p.error,
        items=[
            MealPlanItemOut(
                position=i.position,
                meal_id=str(i.meal_id),
                name=i.meal.name,
                calories=i.calories,
                protein_calories=i.protein_calories,
                meal_type=i.meal_type.value,
                protein_group_calories=i.meal.protein_group_calories,
                protein_group_grams=i.meal.protein_group_grams,
                carb_group_calories=i.meal.carb_group_calories,
                carb_group_protein_grams=i.meal.carb_group_protein_grams,
                total_protein_grams=i.meal.total_protein_grams,
                payload=i.meal.payload,
            )
            for i in sorted(p.items, key=lambda x: x.position)
        ],
    )


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _resolve_calculation_id(
    session: AsyncSession, client_id: uuid.UUID, explicit: uuid.UUID | None
) -> uuid.UUID:
    if explicit is not None:
        return explicit
    latest = (
        await session.execute(
            select(Calculation.id)
            .where(Calculation.client_id == client_id)
            .order_by(Calculation.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        raise HTTPException(404, f"no calculation found for client {client_id}")
    return latest


async def _load_detail(session: AsyncSession, plan_id: uuid.UUID) -> MealPlan:
    plan = (
        await session.execute(
            select(MealPlan)
            .where(MealPlan.id == plan_id)
            .options(selectinload(MealPlan.items).selectinload(MealPlanItem.meal))
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(404, f"meal plan {plan_id} not found")
    return plan


# ── Routes ──────────────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=MealPlanDetailOut,
    status_code=201,
    dependencies=[Depends(require_staff)],
)
async def generate_meal_plan(
    body: GenerateMealPlanIn,
    session: AsyncSession = Depends(get_session),
) -> MealPlanDetailOut:
    calc_id = await _resolve_calculation_id(
        session, body.client_id, body.calculation_id
    )

    try:
        llm = OpenAIClient()
    except RuntimeError as exc:  # key not configured
        raise HTTPException(503, str(exc))

    try:
        outcome = await run_pipeline(
            session,
            calc_id,
            meals_count=body.meals_count,
            include_snack=body.include_snack,
            llm=llm,
        )
    except OpenAIError as exc:  # provider down / auth / rate limit
        raise HTTPException(502, f"LLM provider error: {exc}")

    await session.commit()
    if outcome.meal_plan_id is None:  # pipeline always persists, but be explicit
        raise HTTPException(500, "meal plan was not persisted")
    plan = await _load_detail(session, outcome.meal_plan_id)
    return _detail(plan)


@router.get("/", dependencies=[Depends(require_staff)])
async def list_meal_plans(
    client_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[MealPlanOut]:
    stmt = select(MealPlan).order_by(MealPlan.created_at.desc())
    if client_id is not None:
        stmt = stmt.where(MealPlan.client_id == client_id)
    plans = (await session.execute(stmt)).scalars().all()
    return [_summary(p) for p in plans]


@router.get(
    "/{plan_id}",
    response_model=MealPlanDetailOut,
    dependencies=[Depends(require_staff)],
)
async def get_meal_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> MealPlanDetailOut:
    return _detail(await _load_detail(session, plan_id))
