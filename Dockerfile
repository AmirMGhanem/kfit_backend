FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.34.0" \
    "sqlalchemy>=2.0.40" \
    "alembic>=1.14.0" \
    "asyncpg>=0.30.0" \
    "pydantic>=2.11.0" \
    "pydantic-settings>=2.9.0" \
    "boto3>=1.34.0" \
    "pyjwt>=2.8.0" \
    "bcrypt>=4.0.0" \
    "openai>=1.50.0" \
    "pgvector>=0.3.0" \
    "tiktoken>=0.7.0" \
    "pypdf>=5.0.0" \
    "python-docx>=1.1.0" \
    "python-multipart>=0.0.9" \
    "httpx>=0.28.0" \
    "trafilatura>=1.12.0"

COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
