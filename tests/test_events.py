"""test_events.py — GET /events, filter topic, dan konsistensi dengan GET /stats."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import wait_for_consumer


# ---------------------------------------------------------------------------
# TC-E1: GET /events tanpa filter → kembalikan semua event unik
# ---------------------------------------------------------------------------
async def test_get_events_returns_processed(client: AsyncClient, make_event):
    events = [make_event(topic="events-test") for _ in range(3)]
    await client.post("/publish", json=events)
    await wait_for_consumer(client)

    resp = await client.get("/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3
    assert len(data["events"]) == 3


# ---------------------------------------------------------------------------
# TC-E2: GET /events?topic=X → hanya event topic X
# ---------------------------------------------------------------------------
async def test_get_events_topic_filter(client: AsyncClient, make_event):
    ev_a = [make_event(topic="topic-A") for _ in range(2)]
    ev_b = [make_event(topic="topic-B") for _ in range(3)]
    await client.post("/publish", json=ev_a + ev_b)
    await wait_for_consumer(client)

    resp_a = await client.get("/events", params={"topic": "topic-A"})
    assert resp_a.json()["count"] == 2

    resp_b = await client.get("/events", params={"topic": "topic-B"})
    assert resp_b.json()["count"] == 3


# ---------------------------------------------------------------------------
# TC-E3: Stats consistency — len(GET /events) == unique_processed
# ---------------------------------------------------------------------------
async def test_stats_consistency(client: AsyncClient, make_event):
    """Acceptance Criteria: GET /events count == stats.unique_processed."""
    # Campuran unik dan duplikat
    ev1 = make_event(topic="consist-topic")
    ev2 = make_event(topic="consist-topic")
    duplicate = dict(ev1)  # duplikat ev1

    await client.post("/publish", json=[ev1, ev2, duplicate])
    await wait_for_consumer(client)

    events_resp = await client.get("/events")
    stats_resp = await client.get("/stats")

    count_events = events_resp.json()["count"]
    unique_processed = stats_resp.json()["unique_processed"]

    assert count_events == unique_processed, (
        f"GET /events count ({count_events}) != unique_processed ({unique_processed})"
    )


# ---------------------------------------------------------------------------
# TC-E4: GET /events saat belum ada event → list kosong
# ---------------------------------------------------------------------------
async def test_get_events_empty(client: AsyncClient):
    resp = await client.get("/events")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
    assert resp.json()["events"] == []


# ---------------------------------------------------------------------------
# TC-E5: GET /stats struktur response lengkap
# ---------------------------------------------------------------------------
async def test_stats_response_structure(client: AsyncClient):
    resp = await client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    required_keys = {"received", "unique_processed", "duplicate_dropped", "topics", "uptime_seconds"}
    assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}"
    assert isinstance(data["uptime_seconds"], float)
    assert data["received"] == 0
