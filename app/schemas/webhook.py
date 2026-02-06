from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookEndpointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    secret: str | None = Field(default=None, max_length=255)
    event_types: list[str]
    created_by: UUID


class WebhookEndpointUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2048)
    secret: str | None = Field(default=None, max_length=255)
    event_types: list[str] | None = None
    is_active: bool | None = None


class WebhookEndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    secret: str | None = None
    event_types: list[str]
    created_by: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    endpoint_id: UUID
    event_type: str
    payload: dict[str, Any]
    status: str
    response_status_code: int | None = None
    response_body: str | None = None
    attempts: int
    last_attempt_at: datetime | None = None
    is_active: bool
    created_at: datetime
