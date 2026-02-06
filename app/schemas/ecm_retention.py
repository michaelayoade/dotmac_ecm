from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------


class RetentionPolicyBase(BaseModel):
    name: str
    description: str | None = None
    retention_days: int
    disposition_action: str
    content_type_id: UUID | None = None
    category_id: UUID | None = None
    is_active: bool = True


class RetentionPolicyCreate(RetentionPolicyBase):
    pass


class RetentionPolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    retention_days: int | None = None
    disposition_action: str | None = None
    content_type_id: UUID | None = None
    category_id: UUID | None = None
    is_active: bool | None = None


class RetentionPolicyRead(RetentionPolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# DocumentRetention
# ---------------------------------------------------------------------------


class DocumentRetentionBase(BaseModel):
    document_id: UUID
    policy_id: UUID
    retention_expires_at: datetime
    disposition_status: str = "pending"
    is_active: bool = True


class DocumentRetentionCreate(DocumentRetentionBase):
    pass


class DocumentRetentionUpdate(BaseModel):
    disposition_status: str | None = None
    disposed_at: datetime | None = None
    disposed_by: UUID | None = None
    is_active: bool | None = None


class DocumentRetentionRead(DocumentRetentionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    disposed_at: datetime | None = None
    disposed_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# DisposeRequest
# ---------------------------------------------------------------------------


class DisposeRequest(BaseModel):
    disposed_by: UUID
