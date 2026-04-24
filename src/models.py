from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Schema minimal untuk satu event/log yang masuk ke sistem."""

    topic: str = Field(..., description="Topic/channel event")
    event_id: str = Field(..., description="Identifier unik event (UUID direkomendasikan)")
    timestamp: datetime = Field(..., description="Waktu event dalam format ISO8601")
    source: str = Field(..., description="Sistem/service asal event")
    payload: dict[str, Any] = Field(default_factory=dict, description="Data payload event")

    model_config = {
        "json_schema_extra": {
            "example": {
                "topic": "user-events",
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2024-01-15T10:30:00Z",
                "source": "auth-service",
                "payload": {"user_id": 42, "action": "login"},
            }
        }
    }
