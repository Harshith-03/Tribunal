"""Per-engagement event bus for SSE streaming.

Each engagement has an asyncio.Queue. The orchestrator pushes StageEvents; the
SSE endpoint drains the queue. Events are also buffered so a client that
connects slightly late still sees history.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from .schemas import StageEvent


class EngagementBus:
    def __init__(self):
        self.queue: asyncio.Queue[StageEvent] = asyncio.Queue()
        self.history: list[StageEvent] = []
        self.done = False

    def emit(self, type: str, engagement_id: str, payload: dict[str, Any] | None = None):
        evt = StageEvent(
            type=type, engagement_id=engagement_id, payload=payload or {}, ts=time.time()
        )
        self.history.append(evt)
        self.queue.put_nowait(evt)
        if type in ("complete", "error"):
            self.done = True


class BusRegistry:
    def __init__(self):
        self._buses: dict[str, EngagementBus] = {}

    def create(self, engagement_id: str) -> EngagementBus:
        bus = EngagementBus()
        self._buses[engagement_id] = bus
        return bus

    def get(self, engagement_id: str) -> Optional[EngagementBus]:
        return self._buses.get(engagement_id)


registry = BusRegistry()
