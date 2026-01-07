from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from typing import Any, AsyncIterator, Dict, List

import pytest

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")

pytest.importorskip("google.adk")

from adk_backend import live
from adk_backend.live import LiveRunManager, format_sse_message


class FakeEvent:
    def __init__(self, content: Dict[str, Any]):
        self._content = content

    def model_dump(self, *, by_alias: bool = False, exclude_none: bool = False) -> Dict[str, Any]:
        return dict(self._content)


class DummyRunner:
    def __init__(self, events: List[FakeEvent]):
        self._events = events

    async def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        new_message: Any,
    ) -> AsyncIterator[FakeEvent]:
        for event in self._events:
            yield event


@pytest.mark.asyncio
async def test_live_run_manager_streams_events(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        FakeEvent({"author": "agent", "content": {"parts": [{"text": "hello"}]}}),
        FakeEvent({"author": "agent", "content": {"parts": [{"text": "world"}]}, "turnComplete": True}),
    ]
    runner = DummyRunner(events)

    async def fake_ensure_session(user_id, session_id):
        return SimpleNamespace(id="sess-1", user_id=user_id or "tester")

    monkeypatch.setattr(live, "get_runner", lambda: runner)
    monkeypatch.setattr(live, "ensure_session", fake_ensure_session)

    manager = LiveRunManager(max_history=20)
    run_id, session_id = await manager.start_run(prompt="hello", user_id=None, session_id=None)
    assert run_id.startswith("run-")
    assert session_id == "sess-1"

    queue = await manager.subscribe(run_id)

    received: List[Dict[str, Any]] = []
    try:
        while True:
            message = await asyncio.wait_for(queue.get(), timeout=1.0)
            received.append(message)
            if message.get("event") == "run.status" and (
                message.get("data") or {}
            ).get("status") in {"completed", "error"}:
                break
    finally:
        await manager.unsubscribe(run_id, queue)
        await manager.ensure_task_done(run_id)

    event_names = [item.get("event") for item in received]
    assert "adk.event" in event_names
    assert any(
        item.get("event") == "run.status" and (item.get("data") or {}).get("status") == "completed"
        for item in received
    )
    for item in received:
        data = item.get("data") or {}
        if item.get("event") in {"adk.event", "run.status"}:
            meta = data.get("_meta") or {}
            assert meta.get("sequence") == item.get("id")
            assert meta.get("timestamp") is not None


def test_format_sse_message_structure() -> None:
    message = {
        "id": 1,
        "event": "adk.event",
        "data": {"foo": "bar"},
    }
    sse = format_sse_message(message)
    assert "id: 1" in sse
    assert "event: adk.event" in sse
    assert 'data: {"foo": "bar"}' in sse
