from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Set


class Stats:
    """Thread-safe in-memory counter untuk metrik sistem."""

    def __init__(self) -> None:
        self.received: int = 0
        self.unique_processed: int = 0
        self.duplicate_dropped: int = 0
        self.topics: Set[str] = set()
        self.start_time: datetime = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    async def inc_received(self, topic: str) -> None:
        async with self._lock:
            self.received += 1
            self.topics.add(topic)

    async def inc_unique_processed(self) -> None:
        async with self._lock:
            self.unique_processed += 1

    async def inc_duplicate_dropped(self) -> None:
        async with self._lock:
            self.duplicate_dropped += 1

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        return {
            "received": self.received,
            "unique_processed": self.unique_processed,
            "duplicate_dropped": self.duplicate_dropped,
            "topics": sorted(self.topics),
            "uptime_seconds": round(self.uptime_seconds, 2),
        }
