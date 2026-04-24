"""test_dedup.py — Idempotency, deduplication, dan persistensi dedup store."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.dedup_store import DedupStore
from src.main import create_app
from tests.conftest import wait_for_consumer


# ---------------------------------------------------------------------------
# TC-D1: Event yang sama dikirim 2x → hanya diproses sekali
# ---------------------------------------------------------------------------
async def test_duplicate_rejection(client: AsyncClient, make_event):
    """Acceptance Criteria: unique_processed += 1, duplicate_dropped += 1."""
    payload = make_event(topic="dedup-topic")

    # Kirim pertama kali
    r1 = await client.post("/publish", json=payload)
    assert r1.status_code == 202

    # Kirim event SAMA lagi (simulasi at-least-once delivery)
    r2 = await client.post("/publish", json=payload)
    assert r2.status_code == 202

    # Tunggu consumer memproses keduanya
    await wait_for_consumer(client)

    stats = (await client.get("/stats")).json()
    assert stats["received"] == 2
    assert stats["unique_processed"] == 1
    assert stats["duplicate_dropped"] == 1


# ---------------------------------------------------------------------------
# TC-D2: Batch dengan event duplikat di dalamnya
# ---------------------------------------------------------------------------
async def test_batch_with_internal_duplicate(client: AsyncClient, make_event):
    """Batch berisi 2 event unik + 1 duplikat → unique=2, dropped=1."""
    ev1 = make_event(topic="batch-dedup")
    ev2 = make_event(topic="batch-dedup")
    ev1_dup = dict(ev1)  # salinan identik

    await client.post("/publish", json=[ev1, ev2, ev1_dup])
    await wait_for_consumer(client)

    stats = (await client.get("/stats")).json()
    assert stats["unique_processed"] == 2
    assert stats["duplicate_dropped"] == 1


# ---------------------------------------------------------------------------
# TC-D3: Persistensi dedup store — simulasi restart
# ---------------------------------------------------------------------------
async def test_persistence_after_restart(tmp_path: Path, make_event):
    """Setelah app restart dengan DB file yang sama, event lama tetap ter-dedup."""
    db_path = tmp_path / "persist_test.db"
    payload = make_event(topic="persist-topic")

    # --- Sesi pertama: proses event ---
    app1 = create_app(db_path=db_path)
    async with app1.router.lifespan_context(app1):
        async with AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as c1:
            await c1.post("/publish", json=payload)
            await wait_for_consumer(c1)
            stats1 = (await c1.get("/stats")).json()
            assert stats1["unique_processed"] == 1

    # --- Simulasi restart: buat app baru dengan DB file yang SAMA ---
    app2 = create_app(db_path=db_path)
    async with app2.router.lifespan_context(app2):
        async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as c2:
            # Kirim event yang sama ke instance baru
            await c2.post("/publish", json=payload)
            await wait_for_consumer(c2)
            stats2 = (await c2.get("/stats")).json()

            # unique_processed harus 0 (event sudah ada di DB dari sesi sebelumnya)
            assert stats2["unique_processed"] == 0
            assert stats2["duplicate_dropped"] == 1
