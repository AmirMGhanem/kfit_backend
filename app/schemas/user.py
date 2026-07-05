import uuid
from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsultantCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str
    password: str


class ConsultantUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    password: str | None = None
    is_active: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
