"""Rate limit in-memory theo từng user bằng sliding window."""
from __future__ import annotations

import asyncio
import math
from collections import deque
from collections.abc import Callable
from time import monotonic


class RateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        exempt_user_ids: set[int] | None = None,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests phải >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds phải >= 1")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exempt_user_ids = set(exempt_user_ids or set())
        self._time_func = time_func or monotonic
        self._lock = asyncio.Lock()
        self._events: dict[int, deque[float]] = {}

    async def check(self, user_id: int) -> bool:
        if user_id in self.exempt_user_ids:
            return True

        async with self._lock:
            now = self._time_func()
            events = self._prune_user(user_id, now)
            if events is None:
                events = deque()
                self._events[user_id] = events

            if len(events) >= self.max_requests:
                return False

            events.append(now)
            return True

    async def get_retry_after(self, user_id: int) -> int:
        if user_id in self.exempt_user_ids:
            return 0

        async with self._lock:
            now = self._time_func()
            events = self._prune_user(user_id, now)
            if not events or len(events) < self.max_requests:
                return 0

            retry_after = self.window_seconds - (now - events[0])
            return max(1, math.ceil(retry_after))

    def _prune_user(self, user_id: int, now: float) -> deque[float] | None:
        events = self._events.get(user_id)
        if events is None:
            return None

        cutoff = now - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()

        if not events:
            self._events.pop(user_id, None)
            return None

        return events
