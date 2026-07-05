from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.storage import ensure_bucket
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.calculations import router as calculations_router
from app.routers.clients import router as clients_router
from app.routers.consultants import router as consultants_router
from app.routers.meal_plans import router as meal_plans_router
from app.routers.submissions import router as submissions_router
from app.routers.uploads import router as uploads_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    ensure_bucket()
    yield


app = FastAPI(title="Kfit Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(admin_router)
app.include_router(clients_router)
app.include_router(calculations_router)
app.include_router(consultants_router, prefix="/consultants")
app.include_router(meal_plans_router)
app.include_router(uploads_router)
app.include_router(submissions_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
