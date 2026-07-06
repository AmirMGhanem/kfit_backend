"""
Submission analyzer: turns an onboarding submission into welcome-call notes
(red flags / pain points / insights) for the consultant.
"""

from app.services.submission_analyzer.analyzer import run_analysis

__all__ = ["run_analysis"]
