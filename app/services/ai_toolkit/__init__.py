"""
AI toolkit: read-only fetch tools the chat assistant calls via function-calling.

Public surface:
    openai_tools() — tool schemas for the OpenAI `tools` parameter
    execute(name, args, session) — dispatch a tool call by name
"""

from app.services.ai_toolkit.tools import execute, openai_tools

__all__ = ["openai_tools", "execute"]
