from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_admin
from app.models.client import Client

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientOut(BaseModel):
    id: str
    full_name: str
    email: str | None
    phone: str | None
    gender: str | None
    status: str
    source: str | None
    date_of_birth: str | None
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/", dependencies=[Depends(require_admin)])
async def list_clients(
    session: AsyncSession = Depends(get_session),
) -> list[ClientOut]:
    result = await session.execute(select(Client).order_by(Client.created_at.desc()))
    clients = result.scalars().all()
    return [
        ClientOut(
            id=str(c.id),
            full_name=c.full_name,
            email=c.email,
            phone=c.phone,
            gender=c.gender.value if c.gender else None,
            status=c.status.value,
            source=c.source,
            date_of_birth=c.date_of_birth.isoformat() if c.date_of_birth else None,
            created_at=c.created_at.isoformat(),
        )
        for c in clients
    ]
