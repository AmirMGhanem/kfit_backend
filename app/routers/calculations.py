from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_staff
from app.models.calculation import Calculation

router = APIRouter(prefix="/calculations", tags=["calculations"])


class CalculationOut(BaseModel):
    id: str
    client_id: str
    submission_id: str
    weight_kg: float
    gender: str
    work_type: str
    goal: str
    bmr: int
    bmr_with_paf: int
    tee: int
    min_calories: int
    max_calories: int
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/", dependencies=[Depends(require_staff)])
async def list_calculations(
    session: AsyncSession = Depends(get_session),
) -> list[CalculationOut]:
    result = await session.execute(
        select(Calculation).order_by(Calculation.created_at.desc())
    )
    calcs = result.scalars().all()
    return [
        CalculationOut(
            id=str(c.id),
            client_id=str(c.client_id),
            submission_id=str(c.submission_id),
            weight_kg=float(c.weight_kg),
            gender=c.gender.value,
            work_type=c.work_type.value,
            goal=c.goal.value,
            bmr=c.bmr,
            bmr_with_paf=c.bmr_with_paf,
            tee=c.tee,
            min_calories=c.min_calories,
            max_calories=c.max_calories,
            created_at=c.created_at.isoformat(),
        )
        for c in calcs
    ]
