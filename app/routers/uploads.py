import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.storage import presigned_put_url

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


class PresignRequest(BaseModel):
    filename: str
    content_type: str


class PresignResponse(BaseModel):
    url: str
    key: str
    expires_in: int


@router.post("/presigned-url", response_model=PresignResponse)
async def get_presigned_upload_url(body: PresignRequest) -> PresignResponse:
    """
    Return a short-lived presigned PUT URL.

    The caller uploads the file directly to MinIO using HTTP PUT on this URL.
    The backend is never in the upload path — only the signed key is stored.

    Example client usage:
        PUT <url>
        Content-Type: <content_type>
        Body: <raw file bytes>
    """
    suffix = PurePosixPath(body.filename).suffix.lstrip(".")
    key = f"images/{uuid.uuid4()}.{suffix}" if suffix else f"images/{uuid.uuid4()}"
    expires = 3600

    url = presigned_put_url(key, body.content_type, expires)
    return PresignResponse(url=url, key=key, expires_in=expires)
