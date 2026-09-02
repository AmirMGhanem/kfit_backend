import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def notify_new_submission(phone: str | None) -> None:
    """Fire-and-forget: tell the Make.com scenario a new submission arrived.

    Runs as a FastAPI background task after the response is sent, so it never
    slows the client's submit. Never raises — a webhook failure must not affect
    the submission itself.
    """
    url = settings.SUBMISSION_WEBHOOK_URL
    if not url or not phone:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={"x-make-apikey": settings.SUBMISSION_WEBHOOK_APIKEY},
                json={"customer_phone": phone},
            )
        logger.info(
            "submission webhook sent phone=%s status=%s", phone, resp.status_code
        )
    except Exception:
        logger.warning("submission webhook failed phone=%s", phone, exc_info=True)
