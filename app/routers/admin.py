from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.deps import require_admin
from app.models.submission import Submission

router = APIRouter(prefix="/submissions", tags=["admin"])


@router.get("/", dependencies=[Depends(require_admin)])
async def list_submissions(
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Submission).order_by(Submission.submitted_at.desc())
    )
    subs = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "client_id": str(s.client_id) if s.client_id else None,
            "type": s.type.value,
            "payload": s.payload,
            "submitted_at": s.submitted_at.isoformat(),
        }
        for s in subs
    ]
