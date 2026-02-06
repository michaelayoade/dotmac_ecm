from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Folder
# ---------------------------------------------------------------------------


class FolderBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    parent_id: UUID | None = None
    created_by: UUID
    is_active: bool = True
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata_")


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    parent_id: UUID | None = None
    is_active: bool | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata_")


class FolderRead(FolderBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    path: str
    depth: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class DocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    folder_id: UUID | None = None
    content_type_id: UUID | None = None
    classification: str = "internal"
    status: str = "draft"
    file_name: str = Field(min_length=1, max_length=500)
    file_size: int = Field(ge=0)
    mime_type: str = Field(min_length=1, max_length=255)
    storage_key: str | None = None
    checksum_sha256: str | None = None
    created_by: UUID
    is_active: bool = True
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata_")


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    folder_id: UUID | None = None
    content_type_id: UUID | None = None
    classification: str | None = None
    status: str | None = None
    is_active: bool | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata_")


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    current_version_id: UUID | None = None
    version_number: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# DocumentVersion (immutable — create + read only)
# ---------------------------------------------------------------------------


class DocumentVersionCreate(BaseModel):
    document_id: UUID
    file_name: str = Field(min_length=1, max_length=500)
    file_size: int = Field(ge=0)
    mime_type: str = Field(min_length=1, max_length=255)
    storage_key: str = Field(min_length=1, max_length=1024)
    checksum_sha256: str = Field(min_length=1, max_length=64)
    change_summary: str | None = None
    created_by: UUID


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version_number: int
    file_name: str
    file_size: int
    mime_type: str
    storage_key: str
    checksum_sha256: str
    change_summary: str | None = None
    created_by: UUID
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# ContentType
# ---------------------------------------------------------------------------


class ContentTypeBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    is_active: bool = True


class ContentTypeCreate(ContentTypeBase):
    pass


class ContentTypeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    is_active: bool | None = None


class ContentTypeRead(ContentTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    is_active: bool = True


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    is_active: bool | None = None


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# DocumentTag (junction — create + read only)
# ---------------------------------------------------------------------------


class DocumentTagCreate(BaseModel):
    document_id: UUID
    tag_id: UUID


class DocumentTagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    tag_id: UUID


# ---------------------------------------------------------------------------
# Category (hierarchical)
# ---------------------------------------------------------------------------


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    parent_id: UUID | None = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = None
    parent_id: UUID | None = None
    is_active: bool | None = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    path: str
    depth: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# DocumentCategory (junction — create + read only)
# ---------------------------------------------------------------------------


class DocumentCategoryCreate(BaseModel):
    document_id: UUID
    category_id: UUID


class DocumentCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    category_id: UUID


# ---------------------------------------------------------------------------
# Storage presigned-URL schemas
# ---------------------------------------------------------------------------


class UploadURLRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=500)
    mime_type: str = Field(min_length=1, max_length=255)
    file_size: int = Field(ge=0)


class UploadURLResponse(BaseModel):
    upload_url: str
    storage_key: str


class DownloadURLResponse(BaseModel):
    download_url: str
