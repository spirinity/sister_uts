"""Shared fixtures untuk seluruh test suite.

Setiap test mendapatkan:
- `client`   : httpx.AsyncClient yang terhubung ke app dengan DB terisolasi (tmp_path)
- `event_factory` : helper untuk membuat Event dict unik per-test
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import create_app


# ---------------------------------------------------------------------------
# Fixtures utama
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(tmp_path: Path):
    """Async HTTP client dengan app fresh + DB terisolasi per test."""
    db_path = tmp_path / "test.db"
    app = create_app(db_path=db_path)

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest.fixture
def make_event():
    """Factory untuk membuat payload event valid dengan event_id unik."""

    def _factory(
        topic: str = "test-topic",
        event_id: str | None = None,
        source: str = "test-service",
        payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "topic": topic,
            "event_id": event_id or str(uuid.uuid4()),
            "timestamp": "2024-06-01T10:00:00Z",
            "source": source,
            "payload": payload or {"key": "value"},
        }

    return _factory


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def wait_for_consumer(client: AsyncClient, timeout: float = 2.0) -> None:
    """Polling /stats sampai queue kosong (unique_processed + duplicate_dropped == received)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get("/stats")
        s = resp.json()
        if s["received"] > 0 and (
            s["unique_processed"] + s["duplicate_dropped"] >= s["received"]
        ):
            return
        await asyncio.sleep(0.05)
