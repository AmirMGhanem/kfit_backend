"""
Step 04 — Repair (LLM). Only runs when step 03 rejected a proposal.

Hands the model its previous picks and the exact reasons they failed, and asks
for a corrected selection. The pipeline calls this up to MAX_REPAIR_ATTEMPTS
times; each retry gets fresh validation feedback.

Prompt at the top of the file.
"""

from __future__ import annotations

from app.services.meal_planner.llm.base import LLMClient, Message
from app.services.meal_planner.schemas import (
    MealProposal,
    PlanContext,
    ValidationResult,
)
from app.services.meal_planner.steps.step_02_propose import build_messages

REPAIR_PROMPT = """\
Your previous selection was REJECTED. Fix it.

What you picked:
{previous_picks}

Why it was rejected:
{errors}

Re-select meals from the SAME catalog above so that every constraint is
satisfied — the calorie total must land inside the window, and the main-meal
count and snack rule must match exactly. Return the corrected `picks` and a
short `rationale`. meal_ids only; no numbers you computed.
"""


def _format_previous(proposal: MealProposal) -> str:
    if not proposal.picks:
        return "(nothing)"
    return "\n".join(f"- position {p.position}: {p.meal_id}" for p in proposal.picks)


def build_repair_messages(
    ctx: PlanContext, proposal: MealProposal, result: ValidationResult
) -> list[Message]:
    # Reuse the propose messages (system + catalog) so the model keeps full
    # context, then append the correction turn.
    messages = build_messages(ctx)
    messages.append(
        Message(
            role="user",
            content=REPAIR_PROMPT.format(
                previous_picks=_format_previous(proposal),
                errors="\n".join(f"- {e}" for e in result.errors),
            ),
        )
    )
    return messages


async def repair(
    ctx: PlanContext,
    proposal: MealProposal,
    result: ValidationResult,
    llm: LLMClient,
    *,
    model: str,
) -> MealProposal:
    messages = build_repair_messages(ctx, proposal, result)
    return await llm.complete_structured(messages, MealProposal, model=model)
