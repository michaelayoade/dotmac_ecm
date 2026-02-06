from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    title: str
    body: str
    event_type: str
    entity_type: str
    entity_id: str
    is_read: bool
    read_at: datetime | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata_")
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID]


class MarkAllReadRequest(BaseModel):
    person_id: UUID


class UnreadCountResponse(BaseModel):
    count: int
