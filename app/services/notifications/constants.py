"""Constants for the notifications service."""

from __future__ import annotations

SEVERITIES = frozenset({"info", "warning", "critical"})
SOURCES = frozenset({"ai_assistant", "analyzer", "system", "manual"})
KNOWN_TYPES = frozenset(
    {
        "churn_risk",
        "low_motivation",
        "weight_plateau",
        "ai_insight",
        "system",
        "manual",
    }
)
