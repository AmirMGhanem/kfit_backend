"""
Data contracts that flow between meal-planner pipeline steps.

These are plain Pydantic models — no SQLAlchemy, no framework types — so every
step is pure and unit-testable, and the LLM boundary has an explicit schema to
validate structured output against.

Flow of objects:

    build_context  ─▶ PlanContext ─▶ propose ─▶ MealProposal
                                        │            │
                                        ▼            ▼
                                     validate ─▶ ValidationResult
                                        │
                                        ▼
                                     persist  ─▶ PlanOutcome
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


# ── Inputs the agent reasons about ──────────────────────────────────────────
class PlanTargets(BaseModel):
    """The constraint window + what the client asked for."""

    min_calories: int
    max_calories: int
    # Number of generic (main) meals requested; a snack is added on top.
    meals_count: int
    include_snack: bool
    # Soft target — prefer selections that meet or exceed it. May be None.
    protein_calories_target: int | None = None


class MealCandidate(BaseModel):
    """One catalog row, reduced to what the agent needs to choose."""

    meal_id: uuid.UUID
    name: str
    calories: int
    protein_calories: int | None
    meal_type: str  # "generic" | "snack"


class PlanContext(BaseModel):
    """Everything one generation run needs. Built by step 01, read by all."""

    client_id: uuid.UUID
    calculation_id: uuid.UUID
    targets: PlanTargets
    candidates: list[MealCandidate]

    def candidate_index(self) -> dict[uuid.UUID, MealCandidate]:
        return {c.meal_id: c for c in self.candidates}


# ── The LLM's structured output ─────────────────────────────────────────────
class ProposedPick(BaseModel):
    """A single meal the agent chose, with its slot order."""

    meal_id: uuid.UUID
    position: int = Field(ge=1)


class MealProposal(BaseModel):
    """What the LLM returns. IDs only — never numbers we trust for the sum."""

    picks: list[ProposedPick]
    rationale: str = ""


# ── Deterministic validation output ─────────────────────────────────────────
class ValidationResult(BaseModel):
    """Verdict + computed totals. Totals are authoritative (computed in code)."""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    total_calories: int = 0
    total_protein_calories: int = 0


# ── Final result of a run ───────────────────────────────────────────────────
class PlanOutcome(BaseModel):
    """Returned by the pipeline. Mirrors what got persisted."""

    status: str  # "ready" | "failed"
    meal_plan_id: uuid.UUID | None = None
    total_calories: int | None = None
    total_protein_calories: int | None = None
    attempts: int = 0
    error: str | None = None
