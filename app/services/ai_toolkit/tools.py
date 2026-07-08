"""
AI toolkit — read-only "fetch" tools the chat assistant can call.

Every tool is a parameterized SQLAlchemy query (never LLM-written SQL), returns
plain JSON-able data, is bounded, and never exposes secrets/PII beyond names.
The LLM chooses which to call via OpenAI function-calling; the pipeline dispatches
by name through ``execute``.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.calculation import Calculation
from app.models.client import Client
from app.models.knowledge import KnowledgeDocument
from app.models.meal import Meal
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.submission import Submission
from app.services import notifications as notifications_service
from app.services.chat_assistant.client_context import load_client_context

MAX_ROWS = 50
_CLIENT_STATUSES = ["lead", "onboarding", "active", "paused", "churned"]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _now() -> datetime:
    return datetime.now(UTC)


def _clamp_limit(limit: Any) -> int:
    try:
        return max(1, min(int(limit), MAX_ROWS))
    except (TypeError, ValueError):
        return 20


# ── Tool handlers ───────────────────────────────────────────────────────────
async def count_clients(
    session: AsyncSession, status: str | None = None
) -> dict[str, Any]:
    stmt = select(func.count()).select_from(Client)
    if status:
        stmt = stmt.where(cast(Client.status, String) == status)
    total = (await session.execute(stmt)).scalar_one()
    return {"count": total, "status": status or "all"}


async def clients_by_status(session: AsyncSession) -> dict[str, Any]:
    rows = (
        await session.execute(
            select(cast(Client.status, String), func.count()).group_by(Client.status)
        )
    ).all()
    return {"by_status": {r[0]: r[1] for r in rows}}


async def list_clients(
    session: AsyncSession, status: str | None = None, limit: Any = 20
) -> dict[str, Any]:
    stmt = select(Client).order_by(Client.created_at.desc()).limit(_clamp_limit(limit))
    if status:
        stmt = stmt.where(cast(Client.status, String) == status)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "clients": [
            {
                "id": str(c.id),
                "name": c.full_name,
                "status": c.status.value,
                "created_at": c.created_at.date().isoformat(),
            }
            for c in rows
        ]
    }


async def find_client(session: AsyncSession, name: str) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(Client)
                .where(Client.full_name.ilike(f"%{name}%"))
                .limit(_clamp_limit(10))
            )
        )
        .scalars()
        .all()
    )
    return {
        "matches": [
            {"id": str(c.id), "name": c.full_name, "status": c.status.value}
            for c in rows
        ]
    }


async def get_client_details(session: AsyncSession, client_id: str) -> dict[str, Any]:
    try:
        cid = uuid.UUID(client_id)
    except (ValueError, TypeError):
        return {"error": "invalid client_id"}
    ctx = await load_client_context(session, cid)
    if ctx is None:
        return {"error": "client not found"}
    return {"details": ctx}


async def get_meal_plan(
    session: AsyncSession,
    client_id: str | None = None,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """The client's meal plan with its actual meals + the food content of each."""
    plan: MealPlan | None = None
    if plan_id:
        try:
            plan = await session.get(MealPlan, uuid.UUID(plan_id))
        except (ValueError, TypeError):
            return {"error": "invalid plan_id"}
    elif client_id:
        try:
            cid = uuid.UUID(client_id)
        except (ValueError, TypeError):
            return {"error": "invalid client_id"}
        plan = (
            await session.execute(
                select(MealPlan)
                .where(MealPlan.client_id == cid)
                .order_by(MealPlan.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    else:
        return {"error": "provide client_id or plan_id (or scope the chat to a client)"}

    if plan is None:
        return {"note": "no meal plan found for this client"}

    items = (
        (
            await session.execute(
                select(MealPlanItem)
                .where(MealPlanItem.meal_plan_id == plan.id)
                .order_by(MealPlanItem.position)
            )
        )
        .scalars()
        .all()
    )

    out_items = []
    for it in items:
        meal = await session.get(Meal, it.meal_id)
        payload = (meal.payload if meal else None) or {}
        out_items.append(
            {
                "position": it.position,
                "type": it.meal_type.value,  # generic | snack | free
                "calories": it.calories,
                "protein_calories": it.protein_calories,
                "protein_grams": meal.total_protein_grams if meal else None,
                "fat_source": meal.fat_source if meal else None,
                "name": meal.name if meal else None,
                # The actual food options the client can eat for this meal.
                "foods": payload.get("content"),
            }
        )

    return {
        "plan": {
            "created": plan.created_at.date().isoformat(),
            "status": plan.status.value,
            "calorie_window": f"{plan.min_calories}-{plan.max_calories}",
            "free_calories": plan.free_calories,
            "total_calories": plan.total_calories,
            "meals_count": plan.meals_count,
            "include_snack": plan.include_snack,
        },
        "items": out_items,
    }


async def count_submissions(
    session: AsyncSession, since_days: int | None = None
) -> dict[str, Any]:
    stmt = select(func.count()).select_from(Submission)
    if since_days:
        stmt = stmt.where(
            Submission.submitted_at >= _now() - timedelta(days=since_days)
        )
    total = (await session.execute(stmt)).scalar_one()
    return {"count": total, "since_days": since_days}


async def count_meal_plans(
    session: AsyncSession, status: str | None = None
) -> dict[str, Any]:
    stmt = select(func.count()).select_from(MealPlan)
    if status:
        stmt = stmt.where(cast(MealPlan.status, String) == status)
    total = (await session.execute(stmt)).scalar_one()
    return {"count": total, "status": status or "all"}


async def count_calculations(session: AsyncSession) -> dict[str, Any]:
    total = (
        await session.execute(select(func.count()).select_from(Calculation))
    ).scalar_one()
    return {"count": total}


async def count_knowledge_documents(session: AsyncSession) -> dict[str, Any]:
    total = (
        await session.execute(select(func.count()).select_from(KnowledgeDocument))
    ).scalar_one()
    return {"count": total}


async def recent_activity(session: AsyncSession, days: int = 7) -> dict[str, Any]:
    since = _now() - timedelta(days=max(1, min(int(days or 7), 90)))

    async def _c(model, col) -> int:  # type: ignore[no-untyped-def]
        return (
            await session.execute(
                select(func.count()).select_from(model).where(col >= since)
            )
        ).scalar_one()

    return {
        "window_days": max(1, min(int(days or 7), 90)),
        "new_clients": await _c(Client, Client.created_at),
        "new_submissions": await _c(Submission, Submission.submitted_at),
        "new_meal_plans": await _c(MealPlan, MealPlan.created_at),
    }


async def create_alert(
    _session: AsyncSession,
    *,
    title: str,
    body: str | None = None,
    severity: str = "warning",
    type: str = "ai_insight",
    client_id: str | None = None,
    dedup_key: str | None = None,
) -> dict[str, Any]:
    """Raise an alert/notification to the clinic staff. The one WRITE tool.

    Persists on its own session/commit so the alert survives regardless of the
    chat transaction, and broadcasts to all active staff. ``dedup_key`` collapses
    repeats so the same alert isn't raised twice.
    """
    cid: uuid.UUID | None = None
    if client_id:
        try:
            cid = uuid.UUID(client_id)
        except (ValueError, TypeError):
            cid = None
    async with AsyncSessionLocal() as session:
        notification = await notifications_service.create_notification(
            session,
            type=type,
            title=title,
            body=body,
            severity=severity,
            client_id=cid,
            source="ai_assistant",
            dedup_key=dedup_key,
        )
        await session.commit()
        return {
            "created": True,
            "notification_id": str(notification.id),
            "severity": notification.severity,
            "title": notification.title,
        }


# ── Registry ────────────────────────────────────────────────────────────────
_TOOLS: list[Tool] = [
    Tool(
        "count_clients",
        "Count clients, optionally filtered by status.",
        {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": _CLIENT_STATUSES}},
        },
        count_clients,
    ),
    Tool(
        "clients_by_status",
        "Breakdown of how many clients are in each status (lead/onboarding/active/paused/churned).",
        {"type": "object", "properties": {}},
        clients_by_status,
    ),
    Tool(
        "list_clients",
        "List recent clients (name, status, created date), optionally filtered by status.",
        {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": _CLIENT_STATUSES},
                "limit": {"type": "integer", "description": "max rows (<=50)"},
            },
        },
        list_clients,
    ),
    Tool(
        "find_client",
        "Find clients whose name matches the given text. Returns their ids so you can then get details.",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        find_client,
    ),
    Tool(
        "get_client_details",
        "Get a specific client's full record (submission, calculation, meal plans, insights) by client_id.",
        {
            "type": "object",
            "properties": {"client_id": {"type": "string"}},
            "required": ["client_id"],
        },
        get_client_details,
    ),
    Tool(
        "get_meal_plan",
        "Get the client's meal plan with the ACTUAL meals and the food options of "
        "each (calories, protein, meal type, and the foods the client can eat). Use "
        "this for any question about what/when/which food the client should eat, "
        "carbs, snacks, pre/post-workout, substitutions, or 'what does the plan say'. "
        "Defaults to the client the chat is scoped to.",
        {
            "type": "object",
            "properties": {
                "client_id": {"type": "string"},
                "plan_id": {"type": "string"},
            },
        },
        get_meal_plan,
    ),
    Tool(
        "count_submissions",
        "Count onboarding submissions, optionally within the last N days.",
        {
            "type": "object",
            "properties": {"since_days": {"type": "integer"}},
        },
        count_submissions,
    ),
    Tool(
        "count_meal_plans",
        "Count generated meal plans, optionally filtered by status (pending/generating/ready/failed).",
        {
            "type": "object",
            "properties": {"status": {"type": "string"}},
        },
        count_meal_plans,
    ),
    Tool(
        "count_calculations",
        "Count nutrition calculations performed.",
        {"type": "object", "properties": {}},
        count_calculations,
    ),
    Tool(
        "count_knowledge_documents",
        "Count documents in the knowledge base.",
        {"type": "object", "properties": {}},
        count_knowledge_documents,
    ),
    Tool(
        "recent_activity",
        "Summary of new clients, submissions and meal plans in the last N days (default 7).",
        {
            "type": "object",
            "properties": {"days": {"type": "integer"}},
        },
        recent_activity,
    ),
    Tool(
        "create_alert",
        "Raise an ALERT/notification to the clinic staff about something that needs "
        "attention — e.g. a client at churn risk, losing motivation, or a weight "
        "plateau. Use it ONCE when you identify something actionable, and pass a "
        "stable dedup_key (e.g. 'churn:<client_id>') so the same alert isn't raised "
        "twice. In a client-scoped chat it attaches to that client automatically.",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "short alert headline"},
                "body": {
                    "type": "string",
                    "description": "1-2 sentences: the detail and recommended action",
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                },
                "type": {
                    "type": "string",
                    "description": "category, e.g. churn_risk / low_motivation / "
                    "weight_plateau / ai_insight",
                },
                "dedup_key": {
                    "type": "string",
                    "description": "stable key to prevent duplicate alerts",
                },
                "client_id": {"type": "string"},
            },
            "required": ["title"],
        },
        create_alert,
    ),
]

_BY_NAME: dict[str, Tool] = {t.name: t for t in _TOOLS}

# Tools that operate on "the current client" — default their client_id to the
# client the chat is scoped to when the model doesn't pass one.
_CLIENT_DEFAULT_TOOLS = {"get_meal_plan", "get_client_details", "create_alert"}


def openai_tools() -> list[dict[str, Any]]:
    """All tool schemas for the OpenAI `tools` parameter."""
    return [t.schema() for t in _TOOLS]


async def execute(
    name: str,
    args: dict[str, Any],
    session: AsyncSession,
    scoped_client_id: str | None = None,
) -> Any:
    """Dispatch a tool call by name. Unknown tool → error dict (model recovers)."""
    tool = _BY_NAME.get(name)
    if tool is None:
        return {"error": f"unknown tool: {name}"}
    call_args = dict(args or {})
    # In a client-scoped chat, these tools always operate on the scoped client:
    # force the id (the model can't know UUIDs and often passes the client's
    # name instead) — this also prevents cross-client access.
    if name in _CLIENT_DEFAULT_TOOLS and scoped_client_id:
        call_args["client_id"] = scoped_client_id
    return await tool.handler(session, **call_args)
