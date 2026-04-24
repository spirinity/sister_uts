"""test_stress.py — Stress test: >= 5000 event dengan >= 20% duplikasi."""
from __future__ import annotations

import asyncio
import time
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import wait_for_consumer

TOTAL_EVENTS = 5000
DUPLICATE_RATIO = 0.20  # 20% duplikat
MAX_DURATION_SECONDS = 120  # batas waktu wajar


async def test_stress_5000_events_with_duplicates(client: AsyncClient):
    """
    Kirim 5000 event (20% di antaranya duplikat).
    Sistem harus:
    - Tetap responsif (selesai < MAX_DURATION_SECONDS detik)
    - Tidak crash
    - unique_processed + duplicate_dropped == received
    - duplicate_dropped >= 20% dari total
    """
    # Buat pool event unik
    unique_count = int(TOTAL_EVENTS * (1 - DUPLICATE_RATIO))
    dup_count = TOTAL_EVENTS - unique_count

    unique_ids = [str(uuid.uuid4()) for _ in range(unique_count)]
    # Duplikat diambil dari unique_ids yang sudah ada
    dup_ids = [unique_ids[i % unique_count] for i in range(dup_count)]

    all_ids = unique_ids + dup_ids

    def make_payload(eid: str) -> dict:
        return {
            "topic": "stress-topic",
            "event_id": eid,
            "timestamp": "2024-06-01T00:00:00Z",
            "source": "stress-tester",
            "payload": {"seq": eid},
        }

    # Kirim dalam batch 100 event untuk efisiensi
    BATCH_SIZE = 100
    start = time.monotonic()

    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = [make_payload(eid) for eid in all_ids[i : i + BATCH_SIZE]]
        resp = await client.post("/publish", json=batch)
        assert resp.status_code == 202, f"Batch {i//BATCH_SIZE} gagal: {resp.text}"

    publish_duration = time.monotonic() - start

    # Tunggu consumer selesai memproses semua
    await wait_for_consumer(client, timeout=MAX_DURATION_SECONDS)

    total_duration = time.monotonic() - start
    assert total_duration < MAX_DURATION_SECONDS, (
        f"Stress test melebihi batas waktu: {total_duration:.1f}s > {MAX_DURATION_SECONDS}s"
    )

    # Validasi statistik akhir
    stats = (await client.get("/stats")).json()

    assert stats["received"] == TOTAL_EVENTS, (
        f"received={stats['received']} != {TOTAL_EVENTS}"
    )
    assert stats["unique_processed"] + stats["duplicate_dropped"] == TOTAL_EVENTS, (
        "Total processed + dropped harus sama dengan received"
    )
    assert stats["unique_processed"] == unique_count, (
        f"unique_processed={stats['unique_processed']} != {unique_count}"
    )
    assert stats["duplicate_dropped"] >= dup_count, (
        f"duplicate_dropped={stats['duplicate_dropped']} < {dup_count}"
    )

    print(
        f"\n[Stress] publish={publish_duration:.2f}s total={total_duration:.2f}s "
        f"unique={stats['unique_processed']} dup={stats['duplicate_dropped']}"
    )
