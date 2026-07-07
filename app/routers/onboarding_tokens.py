"""
Stateless onboarding token routes.

  POST /onboarding-tokens/   generate a signed token (staff auth)
  GET  /onboarding-tokens/{token}   verify a token (public)

Token format: {exp_hex}.{hmac_hex}
  exp_hex  — 8-char hex unix timestamp (4 bytes big-endian)
  hmac_hex — first 8 bytes of HMAC-SHA256(ONBOARDING_SECRET, exp_hex), hex = 16 chars

Total: 25 chars. No database, no state.
"""

from __future__ import annotations

import hashlib
import hmac
import struct
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import require_staff

router = APIRouter(prefix="/onboarding-tokens", tags=["onboarding-tokens"])

TTL_SECONDS = 48 * 3600


def _sign(exp_hex: str) -> str:
    raw = hmac.new(
        settings.ONBOARDING_SECRET.encode(),
        exp_hex.encode(),
        hashlib.sha256,
    ).digest()
    return raw[:8].hex()


def _build_token(now: int) -> str:
    exp = now + TTL_SECONDS
    exp_hex = struct.pack(">I", exp).hex()
    return f"{exp_hex}.{_sign(exp_hex)}"


def _verify_token(token: str) -> int:
    """Return expiry unix timestamp, or raise HTTPException."""
    try:
        exp_hex, sig_hex = token.split(".")
    except ValueError:
        raise HTTPException(400, "malformed token")

    expected = _sign(exp_hex)
    if not hmac.compare_digest(expected, sig_hex):
        raise HTTPException(400, "invalid token")

    try:
        exp = struct.unpack(">I", bytes.fromhex(exp_hex))[0]
    except Exception:
        raise HTTPException(400, "malformed token")

    if int(time.time()) > exp:
        raise HTTPException(410, "token expired")

    return exp


# ── I/O schemas ──────────────────────────────────────────────────────────────

class GenerateOut(BaseModel):
    token: str
    url: str
    expires_at: int


class VerifyOut(BaseModel):
    valid: bool
    expires_at: int


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=GenerateOut, dependencies=[Depends(require_staff)])
def generate_token() -> GenerateOut:
    now = int(time.time())
    token = _build_token(now)
    exp = now + TTL_SECONDS
    base = settings.LANDING_BASE_URL.rstrip("/")
    return GenerateOut(token=token, url=f"{base}/onboarding?t={token}", expires_at=exp)


@router.get("/{token}", response_model=VerifyOut)
def verify_token(token: str) -> VerifyOut:
    exp = _verify_token(token)
    return VerifyOut(valid=True, expires_at=exp)
