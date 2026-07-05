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

    # MinIO / S3-compatible storage
    MINIO_INTERNAL_URL: str = "http://minio:9000"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "kfit"


settings = Settings()
