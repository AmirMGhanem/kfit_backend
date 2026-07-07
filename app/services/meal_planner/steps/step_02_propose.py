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

# ── Operator rules (K.FIT nutrition rules — the judgment layer) ──────────────
# The arithmetic (free calories, the ⅓/⅔ split, snack subtraction, per-meal
# tolerance, the fat-in-big-meal gate) is computed and ENFORCED in code. These
# rules guide the LLM's selection *within* those targets.
AGENT_RULES: str = """
1. MAXIMIZE total daily protein. Among meals that fit a calorie target, always
   prefer the one with more protein (grams).
2. Protein tiebreaker: if two options are within ~50 kcal of each other and the
   higher one adds at least ~5 g protein, choose the higher-protein option.
3. Healthy fat and vegetables do NOT count toward the protein target — they are
   for satiety and quality only. Judge protein by the protein grams shown.
4. Snack as a protein source (when a snack is included): an energy bar never
   counts as protein. A protein bar counts only if it has ~10 g+ protein; a
   yogurt / protein drink only if it has ~15 g+ protein.
5. Priority order when trading off: (1) hit each meal's calorie target, then
   (2) meet protein, then (3) maximize protein, then (4) big meal has a fat
   source, then (5) variety and the client's routine/preferences.
""".strip()


# ── Prompt ──────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are the K.FIT meal-planning agent. You build one day's meal plan for a
client by SELECTING meals from a fixed catalog. You never invent meals and never
alter their calories or protein.

The day's calories are pre-computed for you. The client also has a separate
"free calorie" budget of {free_calories} kcal that they spend on their own — do
NOT pick meals to fill it; your meals must hit the per-meal targets below, which
already exclude the free calories.

Meals to choose (return one meal per position):
{meal_plan_spec}

Hard constraints (a plan breaking any of these is rejected and you'll be asked
to fix it):
  • Only choose meal_id values from the catalog below.
  • Each meal's calories must be within ±{tolerance} kcal of its target.
  • {big_meal_rule}
  • {snack_rule}

Output: structured JSON with `picks` (each `meal_id` + 1-based `position`
matching the spec above) and a short `rationale`. Return meal_ids only — never
numbers you computed; the system does the math.

K.FIT nutrition rules:
{rules}
"""

USER_PROMPT = """\
Client targets:
{meal_plan_spec}
Snack: {snack_word}
{fruit_line}

Catalog (meal_id | kcal | protein_kcal | protein_g | fat_source | type | name):
{catalog}

Select the meals now.
"""


def _meal_plan_spec(ctx: PlanContext) -> str:
    t = ctx.targets
    lines = []
    for pos in sorted(t.meal_targets):
        target = t.meal_targets[pos]
        role = "BIG meal" if pos == t.big_meal_position else "main meal"
        note = ""
        if pos == t.big_meal_position:
            note = " — must contain a fat source; if a snack is added its calories come out of THIS meal's budget"
        lines.append(f"  • position {pos} ({role}): ~{target} kcal{note}")
    if t.include_snack:
        lines.append(
            f"  • position {len(t.meal_targets) + 1} (snack): one snack; its "
            "calories are already accounted for inside the big meal's budget"
        )
    return "\n".join(lines)


def _big_meal_rule(ctx: PlanContext) -> str:
    if ctx.targets.big_meal_position is None:
        return "No designated big meal for this plan."
    return (
        f"The BIG meal (position {ctx.targets.big_meal_position}) MUST have "
        '"yes" in the fat_source column.'
    )


def _snack_clause(ctx: PlanContext) -> str:
    if ctx.targets.include_snack:
        return 'Choose EXACTLY ONE meal of type "snack".'
    return 'Do NOT choose any meal of type "snack".'


def _fruit_line(ctx: PlanContext) -> str:
    pref = (ctx.targets.fruit_preference or "").lower()
    if not ctx.targets.include_snack:
        return ""
    mapping = {
        "daily": "Fruit preference: wants fruit daily — strongly prefer a snack that includes a fruit / carb source.",
        "sometimes": "Fruit preference: fruit is okay occasionally — a fruit snack is acceptable but not required.",
        "no": "Fruit preference: does NOT want fruit — pick a non-fruit snack (yogurt / protein drink / cheese / pastrama / etc.).",
        "no-preference": "Fruit preference: no preference — pick the most suitable snack for the targets and protein.",
    }
    return mapping.get(pref, mapping["no-preference"])


def _format_catalog(ctx: PlanContext) -> str:
    lines = []
    for c in ctx.candidates:
        protein = "—" if c.protein_calories is None else str(c.protein_calories)
        grams = "—" if c.total_protein_grams is None else str(c.total_protein_grams)
        fat = "yes" if c.has_fat_source else "no"
        lines.append(
            f"{c.meal_id} | {c.calories} | {protein} | {grams} | {fat} | "
            f"{c.meal_type} | {c.name}"
        )
    return "\n".join(lines)


def build_messages(ctx: PlanContext) -> list[Message]:
    t = ctx.targets
    spec = _meal_plan_spec(ctx)
    system = SYSTEM_PROMPT.format(
        free_calories=t.free_calories,
        meal_plan_spec=spec,
        tolerance=t.tolerance,
        big_meal_rule=_big_meal_rule(ctx),
        snack_rule=_snack_clause(ctx),
        rules=AGENT_RULES,
    )
    user = USER_PROMPT.format(
        meal_plan_spec=spec,
        snack_word="yes (one snack)" if t.include_snack else "no",
        fruit_line=_fruit_line(ctx),
        catalog=_format_catalog(ctx),
    )
    return [
        Message(role="system", content=system),
        Message(role="user", content=user),
    ]


async def propose(ctx: PlanContext, llm: LLMClient, *, model: str) -> MealProposal:
    messages = build_messages(ctx)
    return await llm.complete_structured(messages, MealProposal, model=model)
