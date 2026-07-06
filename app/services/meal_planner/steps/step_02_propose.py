"""
Step 02 — Propose meals (LLM).

The agent SELECTS meals from the catalog to fit the calorie window. It returns
meal IDs only; the system computes and validates the totals (step 03). The model
is never trusted for arithmetic.

The prompt lives at the top of this file. Operator-specific selection rules get
injected into the {rules} slot — fill AGENT_RULES when ready.
"""

from __future__ import annotations

from app.services.meal_planner.llm.base import LLMClient, Message
from app.services.meal_planner.schemas import MealProposal, PlanContext

# ── Operator rules ──────────────────────────────────────────────────────────
# Free-text nutrition/selection guidance from the K.FIT team. Injected verbatim
# into the system prompt. Leave empty until the rules are defined.
AGENT_RULES: str = """
(no additional rules yet)
""".strip()


# ── Prompt ──────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are the K.FIT meal-planning agent. You build one day's meal plan for a
client by SELECTING meals from a fixed catalog. You never invent meals and never
alter their calories or protein.

Your objective:
  • Choose meals whose TOTAL calories fall within [{min_calories}, {max_calories}].
  • Use EXACTLY {meals_count} meal(s) of type "generic" as the main meals.
  • {snack_rule}
  • Prefer selections with good variety and higher protein.

Hard constraints (a plan that breaks any of these will be rejected):
  • Only choose meal_id values that appear in the catalog below.
  • Respect the exact main-meal count and the snack rule above.
  • The calorie total must land inside the window — not under, not over.

Output: structured JSON with `picks` (each an object of `meal_id` and 1-based
`position`) and a short `rationale`. Do NOT output any calorie or protein numbers
you computed yourself — return meal_ids only; the system does the math.

Additional rules from the K.FIT team:
{rules}
"""

USER_PROMPT = """\
Target window: {min_calories}–{max_calories} kcal
Main meals to pick: {meals_count}
Snack: {snack_word}

Catalog (meal_id | kcal | protein_kcal | type | name):
{catalog}

Select the meals now.
"""


def _snack_rule(include_snack: bool) -> str:
    if include_snack:
        return 'Additionally choose EXACTLY ONE meal of type "snack".'
    return 'Do NOT choose any meal of type "snack".'


def _format_catalog(ctx: PlanContext) -> str:
    lines = []
    for c in ctx.candidates:
        protein = "—" if c.protein_calories is None else str(c.protein_calories)
        lines.append(
            f"{c.meal_id} | {c.calories} | {protein} | {c.meal_type} | {c.name}"
        )
    return "\n".join(lines)


def build_messages(ctx: PlanContext) -> list[Message]:
    t = ctx.targets
    system = SYSTEM_PROMPT.format(
        min_calories=t.min_calories,
        max_calories=t.max_calories,
        meals_count=t.meals_count,
        snack_rule=_snack_rule(t.include_snack),
        rules=AGENT_RULES,
    )
    user = USER_PROMPT.format(
        min_calories=t.min_calories,
        max_calories=t.max_calories,
        meals_count=t.meals_count,
        snack_word="yes (one snack)" if t.include_snack else "no",
        catalog=_format_catalog(ctx),
    )
    return [
        Message(role="system", content=system),
        Message(role="user", content=user),
    ]


async def propose(ctx: PlanContext, llm: LLMClient, *, model: str) -> MealProposal:
    messages = build_messages(ctx)
    return await llm.complete_structured(messages, MealProposal, model=model)
