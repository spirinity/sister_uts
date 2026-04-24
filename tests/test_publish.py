"""test_publish.py — Validasi schema dan perilaku POST /publish."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# TC-P1: Event valid → diterima dengan HTTP 202
# ---------------------------------------------------------------------------
async def test_publish_valid_single_event(client: AsyncClient, make_event):
    payload = make_event()
    resp = await client.post("/publish", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["accepted_count"] == 1
    assert payload["event_id"] in data["accepted_event_ids"]


# ---------------------------------------------------------------------------
# TC-P2: Batch event (list) valid → semua diterima
# ---------------------------------------------------------------------------
async def test_publish_valid_batch(client: AsyncClient, make_event):
    batch = [make_event(topic="batch-topic") for _ in range(5)]
    resp = await client.post("/publish", json=batch)
    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted_count"] == 5


# ---------------------------------------------------------------------------
# TC-P3: Hilang field `timestamp` → HTTP 422
# ---------------------------------------------------------------------------
async def test_publish_missing_timestamp(client: AsyncClient, make_event):
    payload = make_event()
    del payload["timestamp"]
    resp = await client.post("/publish", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TC-P4: Hilang field `event_id` → HTTP 422
# ---------------------------------------------------------------------------
async def test_publish_missing_event_id(client: AsyncClient, make_event):
    payload = make_event()
    del payload["event_id"]
    resp = await client.post("/publish", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TC-P5: Hilang field `topic` → HTTP 422
# ---------------------------------------------------------------------------
async def test_publish_missing_topic(client: AsyncClient, make_event):
    payload = make_event()
    del payload["topic"]
    resp = await client.post("/publish", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TC-P6: Body bukan JSON → HTTP 400
# ---------------------------------------------------------------------------
async def test_publish_invalid_json(client: AsyncClient):
    resp = await client.post(
        "/publish",
        content=b"not-json-at-all",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 422)
