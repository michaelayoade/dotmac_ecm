from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# LegalHold
# ---------------------------------------------------------------------------


class LegalHoldBase(BaseModel):
    name: str
    description: str | None = None
    reference_number: str | None = None
    created_by: UUID
    is_active: bool = True


class LegalHoldCreate(LegalHoldBase):
    pass


class LegalHoldUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    reference_number: str | None = None
    is_active: bool | None = None


class LegalHoldRead(LegalHoldBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# LegalHoldDocument
# ---------------------------------------------------------------------------


class LegalHoldDocumentBase(BaseModel):
    legal_hold_id: UUID
    document_id: UUID
    added_by: UUID


class LegalHoldDocumentCreate(LegalHoldDocumentBase):
    pass


class LegalHoldDocumentRead(LegalHoldDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
