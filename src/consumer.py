from __future__ import annotations

import asyncio
import logging

from src.dedup_store import DedupStore
from src.models import Event
from src.queue_manager import QueueManager
from src.stats import Stats

logger = logging.getLogger(__name__)


class Consumer:
    """Background consumer yang memproses event dari queue secara idempotent.

    Satu event dengan pasangan (topic, event_id) yang sama hanya diproses
    sekali meski diterima berkali-kali (at-least-once delivery handling).
    """

    def __init__(self, queue: QueueManager, store: DedupStore, stats: Stats) -> None:
        self.queue = queue
        self.store = store
        self.stats = stats
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Jalankan consumer sebagai asyncio background task."""
        self._task = asyncio.create_task(self._process_loop(), name="consumer-loop")
        logger.info("Consumer background task started.")

    def stop(self) -> None:
        """Hentikan consumer secara graceful."""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Consumer background task cancelled.")

    async def _process_loop(self) -> None:
        logger.info("Consumer waiting for events...")
        while True:
            try:
                event: Event = await self.queue.dequeue()
                await self._handle_event(event)
                self.queue.task_done()
            except asyncio.CancelledError:
                logger.info("Consumer loop stopped (CancelledError).")
                break
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Consumer encountered unexpected error: %s", exc, exc_info=True)

    async def _handle_event(self, event: Event) -> None:
        """Proses satu event: cek duplikat, tandai, update stats."""
        if await self.store.is_duplicate(event.topic, event.event_id):
            logger.warning(
                "[DUPLICATE DROPPED] topic=%s event_id=%s source=%s",
                event.topic,
                event.event_id,
                event.source,
            )
            await self.stats.inc_duplicate_dropped()
        else:
            await self.store.mark_processed(event)
            await self.stats.inc_unique_processed()
            logger.info(
                "[PROCESSED] topic=%s event_id=%s source=%s",
                event.topic,
                event.event_id,
                event.source,
            )
