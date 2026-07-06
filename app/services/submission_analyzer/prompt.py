"""
Prompt for the welcome-call submission analyzer.

The whole onboarding payload (minus PII/media) is handed to the model, which
returns red flags, pain points, and insights in Hebrew for the consultant.
Edit SYSTEM_PROMPT to tune the analysis rules.
"""

from __future__ import annotations

import json
from typing import Any

# Sensitive / non-analytical fields stripped before the payload reaches the LLM.
PII_FIELDS: frozenset[str] = frozenset(
    {
        "id_number",
        "email",
        "phone",
        "instagramHandle",
        "goalPhoto",
        "photoFront",
        "photoBack",
        "photoSide",
    }
)

SYSTEM_PROMPT = """\
You are a nutrition-consulting assistant for K.FIT. You read a new client's
onboarding form and prepare notes for the HUMAN consultant's welcome call.

Return three lists:
1. red_flags — health/safety or behavioral concerns the consultant must be aware
   of (medical conditions, medications, injuries, allergies, disordered-eating
   signals, extreme or unrealistic goals, aggressive self-imposed deficits). If
   there are none, return an EMPTY list — never invent concerns.
2. pain_points — the client's struggles, frustrations, and stated difficulties
   (failed past attempts, hunger, time constraints, low motivation, worries).
3. insights — personalization cues to tailor the approach and build rapport
   (motivation/readiness, experience, food & training preferences, schedule and
   lifestyle, what they explicitly ask for).

Rules:
- Base everything ONLY on the form. Never invent facts.
- You prepare talking points for a professional — do NOT diagnose, prescribe, or
  give medical advice. When something needs clinical attention, phrase it as a
  point to "confirm with a doctor" for the consultant to raise.
- Each item: a short `title` (a few words) and a `detail` (1-2 sentences).
- Write ALL `title` and `detail` text in HEBREW, whatever language the form uses.
- Be concise and directly useful for a welcome call.
"""

USER_TEMPLATE = """\
Onboarding form (JSON):
{payload}

Analyze it and return the three lists."""


def strip_pii(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in PII_FIELDS}


def build_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    clean = strip_pii(payload)
    user = USER_TEMPLATE.format(payload=json.dumps(clean, ensure_ascii=False, indent=2))
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
