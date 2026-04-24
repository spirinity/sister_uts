from __future__ import annotations

import asyncio

from src.models import Event


class QueueManager:
    """Wrapper asyncio.Queue sebagai internal Pub-Sub channel."""

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)

    async def enqueue(self, event: Event) -> None:
        await self._queue.put(event)

    async def dequeue(self) -> Event:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    @property
    def size(self) -> int:
        return self._queue.qsize()

    async def join(self) -> None:
        """Tunggu sampai semua item di queue selesai diproses."""
        await self._queue.join()
