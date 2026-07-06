# Meal Planner

Selects meals from the catalog to fit a client's calorie window. **Selection +
validation, not generation** — the LLM chooses *which* meals; deterministic code
owns *correctness* (the calorie sum is never trusted to the model).

## Flow

```
 calculation (min/max cal)
        │
        ▼
 ┌─────────────────┐  step 01  build_context    query targets + active catalog
 │  PlanContext    │◀──────────────────────────  (deterministic)
 └────────┬────────┘
          ▼
 ┌─────────────────┐  step 02  propose          LLM picks meal_ids
 │  MealProposal   │◀──────────────────────────  (PROMPT in step file)
 └────────┬────────┘
          ▼
 ┌─────────────────┐  step 03  validate         recompute totals, check window /
 │ ValidationResult│◀──────────────────────────  count / snack (deterministic)
 └────────┬────────┘
     ok?  │
   ┌──────┴───────┐
   │ no           │ yes
   ▼              ▼
 step 04       step 05  persist_success  →  meal_plans + items, status=ready
 repair          (deterministic)
 (PROMPT)      step 05  persist_failure  →  meal_plans, status=failed + error
   │
   └── loop back to validate, up to MAX_REPAIR_ATTEMPTS, then persist_failure
```

## Files

| File | Role | Prompt? |
|---|---|---|
| `pipeline.py` | orchestrates the loop; **single entry point** `run_pipeline` | — |
| `schemas.py` | Pydantic DTOs passed between steps | — |
| `repository.py` | the only ORM access (targets, catalog, save) | — |
| `config.py` | tunables (retries, model, temperature) | — |
| `llm/base.py` | `LLMClient` Protocol — the wiring seam | — |
| `llm/stub.py` | `NotWiredLLMClient` (raises) + `FixtureLLMClient` (tests) | — |
| `steps/step_01_build_context.py` | gather targets + catalog | no (deterministic) |
| `steps/step_02_propose.py` | LLM selects meals | **yes** |
| `steps/step_03_validate.py` | the correctness guarantee | no (deterministic) |
| `steps/step_04_repair.py` | LLM fixes a rejected proposal | **yes** |
| `steps/step_05_persist.py` | write outcome | no (deterministic) |

Prompts live at the top of the two LLM step files (02, 04). The deterministic
steps carry no prompt by design — the calorie window is enforced by arithmetic
we control, not by the model.

## Wiring (later — everything below is the ONLY work left)

1. **LLM adapter** — add `llm/openai_client.py` implementing `LLMClient`
   (one method: `complete_structured(messages, schema, *, model)`), using
   `settings.OPENAI_API_KEY`. `model` is passed per call, so one client serves
   both the builder and repair models. Ask OpenAI for structured output
   validated into `MealProposal`.
2. **Trigger** — call `run_pipeline(session, calculation_id, meals_count=…,
   include_snack=…, llm=OpenAIClient())` from a router or a post-calculation
   hook. Builder/repair models default from settings
   (`OPENAI_BUILDER_MODEL` → gpt-4o, `OPENAI_REPAIR_MODEL` → o4-mini) and can be
   overridden per call via `builder_model=` / `repair_model=`.
3. **Operator rules** — fill `AGENT_RULES` at the top of `step_02_propose.py`.

Nothing in the pipeline reaches the network on its own; the client is injected,
so tests run with `FixtureLLMClient` and no key.

## Note on the current catalog

All 41 seeded meals are `generic` (no snacks marked yet). So `include_snack=True`
can't be satisfied until snack meals exist — the validator will correctly reject
it. Mark snacks first when you want snack support.
