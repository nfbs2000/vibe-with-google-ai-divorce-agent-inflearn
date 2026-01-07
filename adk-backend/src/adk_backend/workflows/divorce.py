from __future__ import annotations

from functools import lru_cache

from google.adk.runners import InMemoryRunner

from ..agents import divorce_case_agent


APP_NAME = "Unified Divorce Intelligence Platform"


@lru_cache()
def get_runner() -> InMemoryRunner:
    """Create a singleton InMemoryRunner for the application."""
    return InMemoryRunner(app_name=APP_NAME, agent=divorce_case_agent)
