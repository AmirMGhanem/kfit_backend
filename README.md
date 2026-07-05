# Kfit Backend

FastAPI + PostgreSQL backend. Python 3.13, SQLAlchemy 2 async, Alembic.

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env — set DATABASE_URL
```

## Run

```bash
uvicorn app.main:app --reload
# GET /health → {"status": "ok"}
```

## Migrations

```bash
# Apply all migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Rollback everything
alembic downgrade base
```

## Lint / typecheck

```bash
ruff check .
black --check .
mypy app
pytest
```
