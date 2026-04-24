from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/data.db")


class DedupStore:
    """Persistent deduplication store berbasis SQLite.

    Menyimpan pasangan (topic, event_id) yang sudah diproses ke disk
    sehingga tahan terhadap crash dan restart container.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Buat koneksi DB dan tabel jika belum ada."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        # WAL mode: lebih efisien untuk concurrent read/write
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                topic        TEXT NOT NULL,
                event_id     TEXT NOT NULL,
                source       TEXT NOT NULL,
                payload      TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                PRIMARY KEY (topic, event_id)
            )
            """
        )
        await self._db.commit()
        logger.info("DedupStore initialized: %s", self.db_path.resolve())

    async def close(self) -> None:
        """Tutup koneksi database."""
        if self._db:
            await self._db.close()
            self._db = None

    async def is_duplicate(self, topic: str, event_id: str) -> bool:
        """Kembalikan True jika event sudah pernah diproses."""
        async with self._db.execute(
            "SELECT 1 FROM processed_events WHERE topic = ? AND event_id = ?",
            (topic, event_id),
        ) as cursor:
            return await cursor.fetchone() is not None

    async def mark_processed(self, event) -> None:
        """Tandai event sebagai sudah diproses (atomic, idempotent via INSERT OR IGNORE)."""
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            """
            INSERT OR IGNORE INTO processed_events
                (topic, event_id, source, payload, processed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event.topic, event.event_id, event.source, json.dumps(event.payload), now),
        )
        await self._db.commit()

    async def get_all_events(self, topic: Optional[str] = None) -> list[dict]:
        """Kembalikan semua event unik yang sudah diproses, opsional filter by topic."""
        if topic:
            query = (
                "SELECT topic, event_id, source, payload, processed_at "
                "FROM processed_events WHERE topic = ? ORDER BY processed_at"
            )
            params = (topic,)
        else:
            query = (
                "SELECT topic, event_id, source, payload, processed_at "
                "FROM processed_events ORDER BY processed_at"
            )
            params = ()

        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                "topic": r[0],
                "event_id": r[1],
                "source": r[2],
                "payload": json.loads(r[3]),
                "processed_at": r[4],
            }
            for r in rows
        ]
