"""Free (standalone) calculator routes.

  POST /free-calculations/   run + persist a calculation (staff auth)
  GET  /free-calculations/   list history, newest first (staff auth)

Unlike /calculations, these are not bound to a submission/client — a consultant
runs the calculator for any named prospect. Each row records who ran it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_staff
from app.models.calculation import NutritionGoal, WorkType
from app.models.client import Gender
from app.models.free_calculation import FreeCalculation
from app.models.user import User
from app.services.nutrition_calculator import (
    CalculatorInputs,
    TrainingInput,
    calculate,
)

router = APIRouter(prefix="/free-calculations", tags=["free-calculations"])


# ── I/O schemas ──────────────────────────────────────────────────────────────


class TrainingIn(BaseModel):
    type: Literal["aerobic", "resistance", "hiit", "none"]
    sessions: float = 0.0
    time: float = 0.0


class FreeCalculationCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=255)
    weight_kg: float = Field(gt=0, le=500)
    gender: Literal["male", "female"]
    work_type: Literal["daily", "partial", "none"]
    goal: Literal["weight_loss", "muscle_gain"]
    training_types: list[TrainingIn] = Field(min_length=1)


class FreeCalculationOut(BaseModel):
    id: str
    customer_name: str
    created_by_user_id: str
    created_by_name: str | None
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


def _to_out(calc: FreeCalculation, creator_name: str | None) -> FreeCalculationOut:
    return FreeCalculationOut(
        id=str(calc.id),
        customer_name=calc.customer_name,
        created_by_user_id=str(calc.created_by_user_id),
        created_by_name=creator_name,
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


@router.post("/", response_model=FreeCalculationOut, status_code=201)
async def create_free_calculation(
    body: FreeCalculationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_staff),
) -> FreeCalculationOut:
    result = calculate(
        CalculatorInputs(
            weight=body.weight_kg,
            gender=body.gender,
            work_type=body.work_type,
            goal=body.goal,
            training_types=[
                TrainingInput(**t.model_dump()) for t in body.training_types
            ],
        )
    )

    calc = FreeCalculation(
        id=uuid.uuid4(),
        customer_name=body.customer_name.strip(),
        created_by_user_id=user.id,
        weight_kg=Decimal(str(body.weight_kg)),
        gender=Gender(body.gender),
        work_type=WorkType(body.work_type),
        goal=NutritionGoal(body.goal),
        training_types=[t.model_dump() for t in body.training_types],
        bmr=result.bmr,
        bmr_with_paf=result.bmr_with_paf,
        tee=result.tee,
        min_calories=result.min_calories,
        max_calories=result.max_calories,
    )
    session.add(calc)
    await session.commit()
    await session.refresh(calc)
    return _to_out(calc, user.name)


@router.get("/", response_model=list[FreeCalculationOut])
async def list_free_calculations(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> list[FreeCalculationOut]:
    result = await session.execute(
        select(FreeCalculation, User.name)
        .join(User, User.id == FreeCalculation.created_by_user_id)
        .order_by(FreeCalculation.created_at.desc())
    )
    return [_to_out(calc, name) for calc, name in result.all()]
