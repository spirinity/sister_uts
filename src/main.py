from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, List, Optional, Union

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from src.consumer import Consumer
from src.dedup_store import DedupStore
from src.models import Event
from src.queue_manager import QueueManager
from src.stats import Stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App factory — dipakai juga oleh test fixtures
# ---------------------------------------------------------------------------

def create_app(db_path: Path = Path("data/data.db")) -> FastAPI:
    """Buat instance FastAPI dengan semua dependency terisolasi."""

    dedup_store = DedupStore(db_path=db_path)
    stats = Stats()
    queue = QueueManager()
    consumer = Consumer(queue=queue, store=dedup_store, stats=stats)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await dedup_store.initialize()
        consumer.start()
        logger.info("Pub-Sub Log Aggregator started. DB: %s", db_path)
        yield
        # Shutdown
        consumer.stop()
        await dedup_store.close()
        logger.info("Pub-Sub Log Aggregator stopped.")

    app = FastAPI(
        title="Pub-Sub Log Aggregator",
        description=(
            "Layanan aggregator berbasis Publish-Subscribe dengan "
            "idempotent consumer dan persistent deduplication store."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # POST /publish  — terima single event ATAU batch (list of events)
    # ------------------------------------------------------------------
    @app.post("/publish", status_code=202)
    async def publish_event(
        request: Request,
        example_body: Union[dict, list] = Body(
            None,
            openapi_examples={
                "single_event": {
                    "summary": "Contoh Single Event",
                    "description": "Mengirim satu event tunggal.",
                    "value": {
                        "topic": "user-events",
                        "event_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2026-04-25T10:00:00Z",
                        "source": "auth-service",
                        "payload": {"user_id": 1, "action": "login_success"}
                    }
                },
                "batch_events": {
                    "summary": "Contoh Batch Events (Array)",
                    "description": "Mengirim banyak event sekaligus dalam satu request. Semua event diproses secara independen.",
                    "value": [
                        {
                            "topic": "order-events",
                            "event_id": "aaa-001",
                            "timestamp": "2026-04-25T10:01:00Z",
                            "source": "order-service",
                            "payload": {"order_id": "ORD-001", "status": "created"}
                        },
                        {
                            "topic": "order-events",
                            "event_id": "aaa-002",
                            "timestamp": "2026-04-25T10:01:05Z",
                            "source": "order-service",
                            "payload": {"order_id": "ORD-002", "status": "paid"}
                        },
                        {
                            "topic": "order-events",
                            "event_id": "aaa-003",
                            "timestamp": "2026-04-25T10:01:10Z",
                            "source": "order-service",
                            "payload": {"order_id": "ORD-003", "status": "shipped"}
                        }
                    ]
                },
                "duplicate_event": {
                    "summary": "Contoh Duplicate Event (Tes Idempotency)",
                    "description": "Kirim event dengan event_id yang SAMA seperti yang sudah pernah dikirim. Sistem harus menolaknya (duplicate_dropped bertambah, unique_processed TIDAK bertambah).",
                    "value": {
                        "topic": "user-events",
                        "event_id": "123e4567-e89b-12d3-a456-426614174000",
                        "timestamp": "2026-04-25T10:00:00Z",
                        "source": "auth-service",
                        "payload": {"user_id": 1, "action": "login_success"}
                    }
                }
            }
        )
    ) -> dict:
        """Terima single event atau batch events dan masukkan ke queue."""
        try:
            body: Any = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Request body harus JSON valid.")

        # Normalisasi: single dict → list
        if isinstance(body, dict):
            raw_events = [body]
        elif isinstance(body, list):
            raw_events = body
        else:
            raise HTTPException(status_code=400, detail="Body harus object atau array of objects.")

        accepted: list[str] = []
        errors: list[str] = []

        for raw in raw_events:
            try:
                event = Event.model_validate(raw)
                await stats.inc_received(event.topic)
                await queue.enqueue(event)
                accepted.append(event.event_id)
            except Exception as exc:
                errors.append(str(exc))

        if errors and not accepted:
            # Semua gagal validasi
            raise HTTPException(status_code=422, detail=errors)

        return {
            "status": "accepted",
            "accepted_count": len(accepted),
            "accepted_event_ids": accepted,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # GET /events?topic=...
    # ------------------------------------------------------------------
    @app.get("/events")
    async def get_events(topic: Optional[str] = Query(None, description="Filter by topic")) -> dict:
        """Kembalikan daftar event unik yang sudah diproses."""
        events = await dedup_store.get_all_events(topic=topic)
        return {"events": events, "count": len(events)}

    # ------------------------------------------------------------------
    # GET /stats
    # ------------------------------------------------------------------
    @app.get("/stats")
    async def get_stats() -> dict:
        """Kembalikan metrik kesehatan sistem secara real-time."""
        return stats.to_dict()

    return app


# ---------------------------------------------------------------------------
# Entry point produksi
# ---------------------------------------------------------------------------
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, reload=False)
