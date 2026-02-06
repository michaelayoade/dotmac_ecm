from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    folder_id: UUID | None = None
    content_type_id: UUID | None = None
    classification: str
    status: str
    file_name: str
    file_size: int
    mime_type: str
    created_by: UUID
    is_active: bool
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class SearchResponse(BaseModel):
    items: list[SearchResult]
    count: int
    limit: int
    offset: int
