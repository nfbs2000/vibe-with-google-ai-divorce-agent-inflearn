from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from google.genai import types as genai_types

from .sessions import ensure_session
from .workflows.divorce import get_runner


def _serialize_event(event: Any) -> Dict[str, Any]:
    try:
        payload = event.model_dump(by_alias=True, exclude_none=True)
    except AttributeError:  # pragma: no cover - defensive
        payload = json.loads(json.dumps(event, default=str))
    payload["_meta"] = {"timestamp": time.time()}
    return payload


def format_sse_message(message: Dict[str, Any]) -> str:
    event_name = message.get("event", "message")
    data = message.get("data", {})
    lines: List[str] = []
    if "id" in message:
        lines.append(f"id: {message['id']}")
    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False, default=str)}")
    return "\n".join(lines) + "\n\n"


@dataclass(slots=True)
class RunContext:
    session_id: str
    user_id: str
    prompt: str
    created_at: float = field(default_factory=time.time)


class LiveRunManager:
    """Manage live ADK runs and SSE subscribers."""

    def __init__(self, *, max_history: int = 500) -> None:
        self._contexts: Dict[str, RunContext] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._sequence = 0

    async def start_run(
        self,
        *,
        prompt: str,
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> Tuple[str, str]:
        runner = get_runner()
        session = await ensure_session(user_id, session_id)
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        context = RunContext(session_id=session.id, user_id=session.user_id, prompt=prompt)

        async with self._lock:
            self._contexts[run_id] = context
            self._subscribers[run_id] = set()
            self._history[run_id] = []

        task = asyncio.create_task(self._execute(run_id, context, runner))
        async with self._lock:
            self._tasks[run_id] = task

        await self._publish(
            run_id,
            {
                "event": "run.status",
                "data": {
                    "status": "started",
                    "runId": run_id,
                    "sessionId": context.session_id,
                    "timestamp": time.time(),
                },
            },
        )
        return run_id, context.session_id

    async def _execute(self, run_id: str, context: RunContext, runner) -> None:
        message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=context.prompt)],
        )
        try:
            async for event in runner.run_async(
                user_id=context.user_id,
                session_id=context.session_id,
                new_message=message,
            ):
                await self._publish(
                    run_id,
                    {
                        "event": "adk.event",
                        "data": _serialize_event(event),
                    },
                )
            await self._publish(
                run_id,
                {
                    "event": "run.status",
                    "data": {
                        "status": "completed",
                        "runId": run_id,
                        "sessionId": context.session_id,
                        "timestamp": time.time(),
                    },
                },
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            await self._publish(
                run_id,
                {
                    "event": "run.status",
                    "data": {
                        "status": "error",
                        "runId": run_id,
                        "sessionId": context.session_id,
                        "error": str(exc),
                        "timestamp": time.time(),
                    },
                },
            )
        finally:
            async with self._lock:
                self._tasks.pop(run_id, None)

    async def _publish(self, run_id: str, message: Dict[str, Any]) -> None:
        async with self._lock:
            if run_id not in self._history:
                return
            self._sequence += 1
            message = dict(message)
            timestamp = message.setdefault("timestamp", time.time())
            sequence = self._sequence
            message["id"] = sequence
            data = message.get("data")
            if isinstance(data, dict):
                meta = data.get("_meta")
                if not isinstance(meta, dict):
                    meta = {}
                meta.setdefault("timestamp", timestamp)
                meta.setdefault("sequence", sequence)
                data["_meta"] = meta
            history = self._history.setdefault(run_id, [])
            history.append(message)
            if len(history) > self._max_history:
                del history[0 : len(history) - self._max_history]
            subscribers: Iterable[asyncio.Queue] = list(self._subscribers.get(run_id, set()))

        for queue in subscribers:
            await queue.put(message)

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        async with self._lock:
            if run_id not in self._history:
                raise KeyError(f"Unknown run_id: {run_id}")
            queue: asyncio.Queue = asyncio.Queue()
            subscribers = self._subscribers.setdefault(run_id, set())
            subscribers.add(queue)
            history = list(self._history.get(run_id, []))
        for message in history:
            await queue.put(message)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(run_id)
            if not subscribers:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(run_id, None)

    async def ensure_task_done(self, run_id: str) -> None:
        async with self._lock:
            task = self._tasks.get(run_id)
        if task:
            await task
