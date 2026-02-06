from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------


class CommentBase(BaseModel):
    document_id: UUID
    body: str
    author_id: UUID
    parent_id: UUID | None = None
    status: str = "active"
    is_active: bool = True


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    body: str | None = None
    status: str | None = None
    is_active: bool | None = None


class CommentRead(CommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# DocumentSubscription
# ---------------------------------------------------------------------------


class DocumentSubscriptionBase(BaseModel):
    document_id: UUID
    person_id: UUID
    event_types: list[str]
    is_active: bool = True


class DocumentSubscriptionCreate(DocumentSubscriptionBase):
    pass


class DocumentSubscriptionUpdate(BaseModel):
    event_types: list[str] | None = None
    is_active: bool | None = None


class DocumentSubscriptionRead(DocumentSubscriptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
