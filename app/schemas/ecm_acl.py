from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# DocumentACL
# ---------------------------------------------------------------------------


class DocumentACLBase(BaseModel):
    document_id: UUID
    principal_type: str
    principal_id: UUID
    permission: str
    granted_by: UUID
    is_active: bool = True


class DocumentACLCreate(DocumentACLBase):
    pass


class DocumentACLUpdate(BaseModel):
    principal_type: str | None = None
    principal_id: UUID | None = None
    permission: str | None = None
    granted_by: UUID | None = None
    is_active: bool | None = None


class DocumentACLRead(DocumentACLBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# FolderACL
# ---------------------------------------------------------------------------


class FolderACLBase(BaseModel):
    folder_id: UUID
    principal_type: str
    principal_id: UUID
    permission: str
    is_inherited: bool = False
    granted_by: UUID
    is_active: bool = True


class FolderACLCreate(FolderACLBase):
    pass


class FolderACLUpdate(BaseModel):
    principal_type: str | None = None
    principal_id: UUID | None = None
    permission: str | None = None
    is_inherited: bool | None = None
    granted_by: UUID | None = None
    is_active: bool | None = None


class FolderACLRead(FolderACLBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# DocumentCheckout
# ---------------------------------------------------------------------------


class DocumentCheckoutCreate(BaseModel):
    document_id: UUID
    checked_out_by: UUID
    reason: str | None = None


class DocumentCheckoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    checked_out_by: UUID
    checked_out_at: datetime
    reason: str | None = None


# ---------------------------------------------------------------------------
# CheckinRequest
# ---------------------------------------------------------------------------


class CheckinRequest(BaseModel):
    change_summary: str | None = None
