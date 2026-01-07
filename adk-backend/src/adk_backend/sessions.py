from __future__ import annotations

from typing import Optional

from .workflows.divorce import APP_NAME, get_runner


async def ensure_session(user_id: Optional[str], session_id: Optional[str]):
    """Ensure an ADK session exists and return it."""
    runner = get_runner()
    resolved_user = user_id or "web-user"
    if session_id:
        session = await runner.session_service.get_session(
            app_name=APP_NAME, user_id=resolved_user, session_id=session_id
        )
        if session:
            return session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=resolved_user,
        session_id=session_id,
    )
    return session
