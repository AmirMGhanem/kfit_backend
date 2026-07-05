from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_staff
from app.models.meal_plan import MealPlan

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


class MealPlanOut(BaseModel):
    id: str
    client_id: str
    calculation_id: str
    status: str
    min_calories: int
    max_calories: int
    meals_count: int
    include_snack: bool
    total_calories: int | None
    total_protein_calories: int | None
    model: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/", dependencies=[Depends(require_staff)])
async def list_meal_plans(
    session: AsyncSession = Depends(get_session),
) -> list[MealPlanOut]:
    result = await session.execute(
        select(MealPlan).order_by(MealPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [
        MealPlanOut(
            id=str(p.id),
            client_id=str(p.client_id),
            calculation_id=str(p.calculation_id),
            status=p.status.value,
            min_calories=p.min_calories,
            max_calories=p.max_calories,
            meals_count=p.meals_count,
            include_snack=p.include_snack,
            total_calories=p.total_calories,
            total_protein_calories=p.total_protein_calories,
            model=p.model,
            created_at=p.created_at.isoformat(),
        )
        for p in plans
    ]
