import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import ConsultantCreate, ConsultantUpdate, UserOut

router = APIRouter(tags=["consultants"])


@router.get("/", response_model=list[UserOut])
async def list_consultants(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> list[UserOut]:
    result = await session.execute(select(User).where(User.role == "consultant"))
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.post("/", response_model=UserOut, status_code=201)
async def create_consultant(
    body: ConsultantCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserOut:
    user = User(
        id=uuid.uuid4(),
        name=body.name,
        email=body.email,
        phone=body.phone,
        password_hash=hash_password(body.password),
        role="consultant",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_consultant(
    user_id: uuid.UUID,
    body: ConsultantUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> UserOut:
    result = await session.execute(
        select(User).where(User.id == user_id, User.role == "consultant")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Consultant not found")
    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        user.email = body.email
    if body.phone is not None:
        user.phone = body.phone
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.is_active is not None:
        user.is_active = body.is_active
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_consultant(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> None:
    result = await session.execute(
        select(User).where(User.id == user_id, User.role == "consultant")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Consultant not found")
    user.is_active = False
    await session.commit()
