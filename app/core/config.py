from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    APP_ENV: str = "development"

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS — JSON array in env (e.g. '["http://localhost:3000","https://kfit.tech"]')
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:4000"]

    # OpenAI / LLM (meal-planner agent). Empty until wired; the pipeline only
    # reads these when an LLM client is constructed.
    OPENAI_API_KEY: str = ""
    # Two-model split: a fast model builds the first proposal; a stronger
    # reasoning model only runs on repair (rare — the validator gates it).
    OPENAI_BUILDER_MODEL: str = "gpt-4o"
    OPENAI_REPAIR_MODEL: str = "o4-mini"
    # Submission analyzer (red flags / pain points / insights) — single call.
    OPENAI_ANALYZER_MODEL: str = "gpt-4o"

    # MinIO / S3-compatible storage
    MINIO_INTERNAL_URL: str = "http://minio:9000"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "kfit"


settings = Settings()
