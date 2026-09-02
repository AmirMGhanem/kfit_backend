"""Client-bound calculation routes.

  POST /calculations/   compute + upsert the calculation for a client's
                         submission (staff auth) — used to (re)apply a
                         calculation after onboarding, e.g. after a weight
                         or goal change.
  GET  /calculations/   list all client-bound calculations, newest first
                         (staff auth)

Unlike /free-calculations, these are bound to a submission/client — there is
at most one Calculation row per submission_id; POSTing again for the same
submission updates that row in place rather than creating a duplicate.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_staff
from app.models.calculation import Calculation, NutritionGoal, WorkType
from app.models.client import Client, Gender
from app.models.submission import Submission
from app.models.user import User
from app.services.nutrition_calculator import (
    CalculatorInputs,
    TrainingInput,
    calculate,
)

router = APIRouter(prefix="/calculations", tags=["calculations"])


# ── I/O schemas ──────────────────────────────────────────────────────────────


class TrainingIn(BaseModel):
    type: Literal["aerobic", "resistance", "hiit", "none"]
    sessions: float = 0.0
    time: float = 0.0


class CalculationCreate(BaseModel):
    client_id: uuid.UUID
    submission_id: uuid.UUID
    weight_kg: float = Field(gt=0, le=500)
    gender: Literal["male", "female"]
    work_type: Literal["daily", "partial", "none"]
    goal: Literal["weight_loss", "muscle_gain"]
    training_types: list[TrainingIn] = Field(min_length=1)
    skinny_fat: bool = False


class CalculationOut(BaseModel):
    id: str
    client_id: str
    submission_id: str
    weight_kg: float
    gender: str
    work_type: str
    goal: str
    training_types: list[dict]
    bmr: int
    bmr_with_paf: int
    tee: int
    min_calories: int
    max_calories: int
    created_at: str

    model_config = {"from_attributes": True}


def _to_out(calc: Calculation) -> CalculationOut:
    return CalculationOut(
        id=str(calc.id),
        client_id=str(calc.client_id),
        submission_id=str(calc.submission_id),
        weight_kg=float(calc.weight_kg),
        gender=calc.gender.value,
        work_type=calc.work_type.value,
        goal=calc.goal.value,
        training_types=calc.training_types,
        bmr=calc.bmr,
        bmr_with_paf=calc.bmr_with_paf,
        tee=calc.tee,
        min_calories=calc.min_calories,
        max_calories=calc.max_calories,
        created_at=calc.created_at.isoformat(),
    )


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/", response_model=CalculationOut, status_code=201)
async def create_or_update_calculation(
    body: CalculationCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> CalculationOut:
    client = await session.get(Client, body.client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    submission = await session.get(Submission, body.submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.client_id != body.client_id:
        raise HTTPException(
            status_code=400, detail="Submission does not belong to client"
        )

    result = calculate(
        CalculatorInputs(
            weight=body.weight_kg,
            gender=body.gender,
            work_type=body.work_type,
            goal=body.goal,
            training_types=[
                TrainingInput(**t.model_dump()) for t in body.training_types
            ],
            skinny_fat=body.skinny_fat,
        )
    )

    existing = await session.execute(
        select(Calculation)
        .where(Calculation.submission_id == body.submission_id)
        .order_by(Calculation.created_at.desc())
    )
    calc = existing.scalars().first()

    if calc is None:
        calc = Calculation(
            id=uuid.uuid4(),
            client_id=body.client_id,
            submission_id=body.submission_id,
        )
        session.add(calc)
    else:
        calc.client_id = body.client_id

    calc.weight_kg = Decimal(str(body.weight_kg))
    calc.gender = Gender(body.gender)
    calc.work_type = WorkType(body.work_type)
    calc.goal = NutritionGoal(body.goal)
    calc.training_types = [t.model_dump() for t in body.training_types]
    calc.bmr = result.bmr
    calc.bmr_with_paf = result.bmr_with_paf
    calc.tee = result.tee
    calc.min_calories = result.min_calories
    calc.max_calories = result.max_calories

    await session.commit()
    await session.refresh(calc)
    return _to_out(calc)


@router.get("/", dependencies=[Depends(require_staff)])
async def list_calculations(
    session: AsyncSession = Depends(get_session),
) -> list[CalculationOut]:
    result = await session.execute(
        select(Calculation).order_by(Calculation.created_at.desc())
    )
    calcs = result.scalars().all()
    return [_to_out(c) for c in calcs]
