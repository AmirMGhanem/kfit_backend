"""
Structured output for the submission analyzer.

The model returns three lists of ``{title, detail}`` items (in Hebrew). All
fields are required so OpenAI structured output stays strict; a bucket may be an
empty list (e.g. no red flags).
"""

from __future__ import annotations

from pydantic import BaseModel


class InsightItem(BaseModel):
    title: str
    detail: str


class SubmissionAnalysis(BaseModel):
    red_flags: list[InsightItem]
    pain_points: list[InsightItem]
    insights: list[InsightItem]
