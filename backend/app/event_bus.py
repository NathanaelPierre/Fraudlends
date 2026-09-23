"""
A small in-process pub/sub hub that powers the admin dashboard's live
feed (GET /admin/stream). No message broker needed for a single-process
demo deployment: every event that matters for the security console —
logins, lockouts, signups, settings changes, checks, rate-limit hits,
admin actions — already flows through one of a handful of call sites
(mainly app/audit_log.py), so hooking in here is enough to get a real
live stream rather than a polling illusion.

Thread-safety note: FastAPI runs sync `def` endpoints in a worker
thread pool, but `asyncio.Queue` is not thread-safe. `publish()` is
called from those worker threads, so it hands delivery off to the
event loop via `call_soon_threadsafe` rather than touching the queues
directly.
"""
import asyncio
import time
from collections import deque, Counter
from threading import Lock
from typing import Optional

MAX_HISTORY = 300
MAX_QUEUE_PER_SUBSCRIBER = 100


class EventBus:
    def __init__(self):
        self._subscribers = set()
        self._history = deque(maxlen=MAX_HISTORY)
        self._counters = Counter()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = Lock()
        self.started_at = time.time()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def publish(self, event_type: str, data: Optional[dict] = None) -> dict:
        event = {"type": event_type, "data": data or {}, "ts": time.time()}
        with self._lock:
            self._history.append(event)
            self._counters[event_type] += 1
            subscribers = list(self._subscribers)

        for q in subscribers:
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._safe_put, q, event)
            else:
                self._safe_put(q, event)
        return event

    def _safe_put(self, q: asyncio.Queue, event: dict) -> None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            try:
                q.get_nowait()
            except Exception:
                pass
            try:
                q.put_nowait(event)
            except Exception:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_PER_SUBSCRIBER)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def recent(self, limit: int = 50) -> list:
        with self._lock:
            items = list(self._history)
        return items[-limit:]

    def counters(self) -> dict:
        with self._lock:
            return dict(self._counters)

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


bus = EventBus()
