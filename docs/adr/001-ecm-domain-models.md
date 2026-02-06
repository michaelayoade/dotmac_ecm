# ADR-001: ECM Domain Models

**Status:** Accepted
**Date:** 2026-02-06
**Author:** DotMac ECM Team

## Context

DotMac ECM is a general-purpose Electronic Content Management system built on FastAPI, SQLAlchemy 2.0, PostgreSQL, and Celery. The existing starter template provides foundational modules:

- **People** (`people`) — identity records
- **Auth** (`user_credentials`, `mfa_methods`, `sessions`, `api_keys`) — authentication
- **RBAC** (`roles`, `permissions`, `role_permissions`, `person_roles`) — authorization
- **Audit** (`audit_events`) — event logging
- **Settings** (`domain_settings`) — configuration
- **Scheduler** (`scheduled_tasks`) — background jobs

The ECM domain must add document management, folder hierarchy, versioning, metadata/classification, check-in/check-out, workflows, access control, retention/compliance, and collaboration. All new models follow the established codebase conventions:

- **UUID primary keys** via `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
- **SQLAlchemy 2.0** `Mapped[]` type annotations with `mapped_column()`
- **Timestamps** `created_at` / `updated_at` with `DateTime(timezone=True)` and `lambda: datetime.now(timezone.utc)`
- **Soft delete** via `is_active: Mapped[bool]` (no hard deletes except `document_checkouts`)
- **Python `enum.Enum`** mapped to PostgreSQL `Enum()` columns
- **`metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)`** for extensible metadata
- **`UniqueConstraint`** in `__table_args__` tuples for compound uniqueness
- **`relationship()`** for ORM navigation; FKs use `ForeignKey("tablename.id")`
- **All models** in `app/models/`, imported via `app/models/__init__.py`, registered in `alembic/env.py`
- **File storage** via S3/MinIO (presigned URLs for upload/download — no file proxying through API)

---

## Entity Relationship Diagram

```
                          ┌──────────────────┐
                          │     people       │  (existing)
                          │  id: UUID (PK)   │
                          └──────┬───────────┘
                                 │
          ┌──────────────────────┼──────────────────────────┐
          │                      │                          │
          ▼                      ▼                          ▼
┌─────────────────┐  ┌───────────────────┐      ┌──────────────────┐
│    folders      │  │    documents      │      │     roles        │ (existing)
│  id: UUID (PK)  │  │  id: UUID (PK)    │      │  id: UUID (PK)   │
│  parent_id (FK) │  │  folder_id (FK)   │      └────────┬─────────┘
│  path (mat.)    │  │  created_by (FK)  │               │
│  created_by(FK) │  │  current_ver (FK) │               │
└────────┬────────┘  └───────┬───────────┘               │
         │                   │                            │
         │         ┌─────────┼──────────┐                 │
         │         ▼         │          ▼                 │
         │  ┌────────────┐   │  ┌────────────────┐        │
         │  │ document_  │   │  │ document_      │        │
         │  │ versions   │   │  │ checkouts      │        │
         │  │ id: UUID   │   │  │ id: UUID       │        │
         │  │ doc_id(FK) │   │  │ doc_id (FK,UQ) │        │
         │  │ storage_key│   │  │ person_id (FK) │        │
         │  └────────────┘   │  └────────────────┘        │
         │                   │                            │
         │         ┌─────────┼──────────┐                 │
         │         ▼         ▼          ▼                 │
         │  ┌──────────┐ ┌──────────┐ ┌────────────┐      │
         │  │ doc_tags │ │ doc_cats │ │ comments   │      │
         │  │ (junction)│ │(junction)│ │ doc_id(FK) │      │
         │  └─────┬────┘ └────┬─────┘ │ person(FK) │      │
         │        ▼           ▼       └────────────┘      │
         │  ┌──────────┐ ┌──────────┐                     │
         │  │  tags    │ │categories│                     │
         │  └──────────┘ └──────────┘                     │
         │                   │                            │
    ┌────┴───────┐    ┌──────┴──────┐    ┌───────────────┐│
    │folder_acls │    │document_acls│    │ doc_          ││
    │folder_id   │    │document_id  │    │ subscriptions ││
    │principal_id│    │principal_id │    │ document_id   ││
    │principal_  │    │principal_   │    │ person_id     ││
    │  type      │    │  type       │    └───────────────┘│
    └────────────┘    └─────────────┘                     │
                                                          │
    ┌──────────────────┐  ┌───────────────────┐           │
    │workflow_         │  │ workflow_         │           │
    │ definitions      │  │  instances        │           │
    │ id: UUID         │  │  id: UUID         │           │
    │ states (JSON)    │  │  document_id (FK) │           │
    └────────┬─────────┘  │  definition_id(FK)│           │
             │            └────────┬──────────┘           │
             │                     │                      │
             │            ┌────────▼──────────┐           │
             │            │ workflow_tasks    │           │
             │            │ instance_id (FK)  │           │
             │            │ assignee_id (FK)──┼──►people  │
             │            └───────────────────┘           │
             │                                            │
    ┌────────┴────────────────────────────────────────────┤
    │         Retention & Compliance                      │
    ├─────────────────┐  ┌────────────────┐               │
    │retention_       │  │legal_holds     │               │
    │ policies        │  │ id: UUID       │               │
    │ id: UUID        │  │ created_by(FK) │               │
    └────────┬────────┘  └───────┬────────┘               │
             │                   │                        │
    ┌────────▼────────┐  ┌───────▼────────────┐           │
    │document_        │  │legal_hold_         │           │
    │ retentions      │  │ documents          │           │
    │ document_id(FK) │  │ legal_hold_id (FK) │           │
    │ policy_id (FK)  │  │ document_id (FK)   │           │
    └─────────────────┘  └────────────────────┘           │
                                                          │
    ┌─────────────────┐                                   │
    │ content_types   │                                   │
    │ id: UUID        │                                   │
    │ schema (JSON)   │                                   │
    └─────────────────┘                                   │
```

---

## Enum Definitions

All enums are Python `enum.Enum` subclasses following the existing pattern (e.g., `PersonStatus`, `AuthProvider`). Values are lowercase snake_case strings.

```python
# app/models/ecm.py

class DocumentStatus(enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"
    deleted = "deleted"          # soft-delete state


class ClassificationLevel(enum.Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class ACLPermission(enum.Enum):
    read = "read"
    write = "write"
    delete = "delete"
    manage = "manage"            # grant/revoke ACLs


class PrincipalType(enum.Enum):
    person = "person"
    role = "role"


class WorkflowTaskStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class WorkflowTaskType(enum.Enum):
    approval = "approval"
    review = "review"
    sign_off = "sign_off"


class WorkflowInstanceStatus(enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class DispositionAction(enum.Enum):
    retain = "retain"            # keep indefinitely
    archive = "archive"          # move to archive storage
    destroy = "destroy"          # permanent deletion


class DispositionStatus(enum.Enum):
    pending = "pending"          # retention period not yet expired
    eligible = "eligible"        # ready for disposition
    held = "held"                # blocked by legal hold
    completed = "completed"      # disposition action executed


class CommentStatus(enum.Enum):
    active = "active"
    deleted = "deleted"
```

---

## Core Content Entities

### `folders`

Self-referential hierarchy using materialized path for O(1) subtree queries.

```python
class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_folders_parent_name"),
        Index("ix_folders_path", "path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folders.id")
    )
    path: Mapped[str] = mapped_column(
        String(4000), nullable=False, default="/"
    )  # e.g. "/root-uuid/child-uuid/this-uuid/"
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent")
    documents = relationship("Document", back_populates="folder")
    creator = relationship("Person", foreign_keys=[created_by])
    acls = relationship("FolderACL", back_populates="folder")
```

**Materialized path format:** `/<uuid>/<uuid>/<uuid>/`
- Root folders: `/<own-uuid>/`
- Child: `/<parent-path><own-uuid>/`
- Subtree query: `WHERE path LIKE '/<ancestor-uuid>/%'`
- Move operation: UPDATE path prefix for subtree (rare in ECM)

### `documents`

Root content object. Denormalized fields from current version avoid JOINs on list queries.

```python
class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_folder_id", "folder_id"),
        Index("ix_documents_created_by", "created_by"),
        Index("ix_documents_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folders.id")
    )
    content_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_types.id")
    )
    classification: Mapped[ClassificationLevel] = mapped_column(
        Enum(ClassificationLevel), default=ClassificationLevel.internal
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.draft
    )

    # Denormalized from current version (updated on new version creation)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id")
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    folder = relationship("Folder", back_populates="documents")
    current_version = relationship(
        "DocumentVersion", foreign_keys=[current_version_id]
    )
    versions = relationship(
        "DocumentVersion",
        foreign_keys="DocumentVersion.document_id",
        back_populates="document",
        order_by="DocumentVersion.version_number.desc()",
    )
    creator = relationship("Person", foreign_keys=[created_by])
    content_type = relationship("ContentType")
    tags = relationship("DocumentTag", back_populates="document")
    categories = relationship("DocumentCategory", back_populates="document")
    comments = relationship("Comment", back_populates="document")
    acls = relationship("DocumentACL", back_populates="document")
    subscriptions = relationship("DocumentSubscription", back_populates="document")
```

### `document_versions`

Immutable version records. **No `updated_at` column** — versions are append-only. The only mutation is soft-delete via `is_active`.

```python
class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number",
            name="uq_document_versions_doc_version"
        ),
        Index("ix_document_versions_document_id", "document_id"),
        Index("ix_document_versions_storage_key", "storage_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # No updated_at — immutable record

    document = relationship(
        "Document",
        foreign_keys=[document_id],
        back_populates="versions",
    )
    creator = relationship("Person", foreign_keys=[created_by])
```

---

## Metadata & Classification Entities

### `content_types`

Document type definitions with a JSON schema that is validated in the service layer (not at the DB level). Avoids the EAV antipattern.

```python
class ContentType(Base):
    __tablename__ = "content_types"
    __table_args__ = (
        UniqueConstraint("name", name="uq_content_types_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    schema: Mapped[dict | None] = mapped_column(
        JSON
    )  # JSON Schema defining allowed metadata fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

### `tags` + `document_tags`

Flat labeling system — simple key-value tags applied to documents.

```python
class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("name", name="uq_tags_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    documents = relationship("DocumentTag", back_populates="tag")


class DocumentTag(Base):
    __tablename__ = "document_tags"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "tag_id", name="uq_document_tags_doc_tag"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False
    )

    document = relationship("Document", back_populates="tags")
    tag = relationship("Tag", back_populates="documents")
```

### `categories` + `document_categories`

Hierarchical classification using materialized path (same pattern as folders).

```python
class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_categories_parent_name"),
        Index("ix_categories_path", "path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    path: Mapped[str] = mapped_column(String(4000), nullable=False, default="/")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent")
    documents = relationship("DocumentCategory", back_populates="category")


class DocumentCategory(Base):
    __tablename__ = "document_categories"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "category_id",
            name="uq_document_categories_doc_cat",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )

    document = relationship("Document", back_populates="categories")
    category = relationship("Category", back_populates="documents")
```

---

## Check-in / Check-out

### `document_checkouts`

Exclusive editing lock enforced at the database level via a `UNIQUE` constraint on `document_id`. Only one person can check out a document at a time. Rows are **hard-deleted** on check-in (not soft-deleted) — this is the only table that uses hard delete.

```python
class DocumentCheckout(Base):
    __tablename__ = "document_checkouts"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_document_checkouts_document"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    checked_out_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    checked_out_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reason: Mapped[str | None] = mapped_column(Text)

    document = relationship("Document")
    person = relationship("Person", foreign_keys=[checked_out_by])
```

**Flow:**
1. **Check-out:** `INSERT INTO document_checkouts` — fails with `IntegrityError` if already checked out
2. **Check-in:** Upload new version → update `documents` denormalized fields → `DELETE FROM document_checkouts WHERE document_id = ?`
3. **Force unlock (admin):** Same as check-in delete, logged via audit event

---

## Workflow Entities

### `workflow_definitions`

State machine configuration stored as JSON. States and transitions are defined declaratively and evaluated in application code.

```python
class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    __table_args__ = (
        UniqueConstraint("name", name="uq_workflow_definitions_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    states: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # {"draft": {"transitions": [{"to": "review", "roles": ["editor"]}]}, ...}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    instances = relationship("WorkflowInstance", back_populates="definition")
```

**Example `states` JSON:**
```json
{
  "draft": {
    "transitions": [
      {"to": "review", "roles": ["author", "editor"]}
    ]
  },
  "review": {
    "transitions": [
      {"to": "approved", "roles": ["reviewer"]},
      {"to": "draft", "roles": ["reviewer"]}
    ]
  },
  "approved": {
    "transitions": [
      {"to": "published", "roles": ["publisher"]}
    ]
  },
  "published": {
    "final": true
  }
}
```

### `workflow_instances`

A running workflow attached to a specific document.

```python
class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        Index("ix_workflow_instances_document_id", "document_id"),
        Index("ix_workflow_instances_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    current_state: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[WorkflowInstanceStatus] = mapped_column(
        Enum(WorkflowInstanceStatus), default=WorkflowInstanceStatus.active
    )
    started_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    definition = relationship("WorkflowDefinition", back_populates="instances")
    document = relationship("Document")
    starter = relationship("Person", foreign_keys=[started_by])
    tasks = relationship("WorkflowTask", back_populates="instance")
```

### `workflow_tasks`

Individual actions assigned to people within a workflow instance.

```python
class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    __table_args__ = (
        Index("ix_workflow_tasks_instance_id", "instance_id"),
        Index("ix_workflow_tasks_assignee_id", "assignee_id"),
        Index("ix_workflow_tasks_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id"), nullable=False
    )
    task_type: Mapped[WorkflowTaskType] = mapped_column(
        Enum(WorkflowTaskType), nullable=False
    )
    status: Mapped[WorkflowTaskStatus] = mapped_column(
        Enum(WorkflowTaskStatus), default=WorkflowTaskStatus.pending
    )
    assignee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    from_state: Mapped[str] = mapped_column(String(80), nullable=False)
    to_state: Mapped[str] = mapped_column(String(80), nullable=False)
    decision_comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    instance = relationship("WorkflowInstance", back_populates="tasks")
    assignee = relationship("Person", foreign_keys=[assignee_id])
```

---

## Access Control

### `document_acls`

Per-document permissions. Uses polymorphic principal (person or role) identified by `principal_type` + `principal_id`.

```python
class DocumentACL(Base):
    __tablename__ = "document_acls"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "principal_type", "principal_id", "permission",
            name="uq_document_acls_doc_principal_perm",
        ),
        Index("ix_document_acls_document_id", "document_id"),
        Index("ix_document_acls_principal", "principal_type", "principal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    principal_type: Mapped[PrincipalType] = mapped_column(
        Enum(PrincipalType), nullable=False
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )  # FK to people.id or roles.id based on principal_type
    permission: Mapped[ACLPermission] = mapped_column(
        Enum(ACLPermission), nullable=False
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document = relationship("Document", back_populates="acls")
    grantor = relationship("Person", foreign_keys=[granted_by])
```

### `folder_acls`

Per-folder permissions with inheritance flag. When `is_inherited = True`, the ACL was propagated from a parent folder.

```python
class FolderACL(Base):
    __tablename__ = "folder_acls"
    __table_args__ = (
        UniqueConstraint(
            "folder_id", "principal_type", "principal_id", "permission",
            name="uq_folder_acls_folder_principal_perm",
        ),
        Index("ix_folder_acls_folder_id", "folder_id"),
        Index("ix_folder_acls_principal", "principal_type", "principal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    folder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folders.id"), nullable=False
    )
    principal_type: Mapped[PrincipalType] = mapped_column(
        Enum(PrincipalType), nullable=False
    )
    principal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    permission: Mapped[ACLPermission] = mapped_column(
        Enum(ACLPermission), nullable=False
    )
    is_inherited: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    folder = relationship("Folder", back_populates="acls")
    grantor = relationship("Person", foreign_keys=[granted_by])
```

### ACL Resolution Algorithm

Permission checks are evaluated in the service layer with this precedence:

```
1. Admin bypass   — person has "ecm.admin" RBAC permission → full access
2. Document ACLs  — check document_acls for (person_id, person's role_ids)
3. Folder walk    — walk up folder hierarchy via materialized path,
                    check folder_acls at each level
4. Deny           — no matching ACL → access denied
```

The algorithm short-circuits at the first match. `manage` permission implies `read + write + delete`.

---

## Retention & Compliance

### `retention_policies`

Rules defining how long documents must be retained before disposition.

```python
class RetentionPolicy(Base):
    __tablename__ = "retention_policies"
    __table_args__ = (
        UniqueConstraint("name", name="uq_retention_policies_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition_action: Mapped[DispositionAction] = mapped_column(
        Enum(DispositionAction), nullable=False
    )
    content_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_types.id")
    )  # Apply to specific content type
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )  # Apply to specific category
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    content_type = relationship("ContentType")
    category = relationship("Category")
```

### `document_retentions`

Per-document retention tracking. Created when a document is assigned a retention policy (manually or via content type / category match).

```python
class DocumentRetention(Base):
    __tablename__ = "document_retentions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "policy_id",
            name="uq_document_retentions_doc_policy",
        ),
        Index("ix_document_retentions_status", "disposition_status"),
        Index("ix_document_retentions_expires_at", "retention_expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retention_policies.id"), nullable=False
    )
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    disposition_status: Mapped[DispositionStatus] = mapped_column(
        Enum(DispositionStatus), default=DispositionStatus.pending
    )
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disposed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    document = relationship("Document")
    policy = relationship("RetentionPolicy")
    disposer = relationship("Person", foreign_keys=[disposed_by])
```

### `legal_holds` + `legal_hold_documents`

Legal holds freeze disposition for documents involved in litigation or regulatory review.

```python
class LegalHold(Base):
    __tablename__ = "legal_holds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reference_number: Mapped[str | None] = mapped_column(String(120))
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator = relationship("Person", foreign_keys=[created_by])
    documents = relationship("LegalHoldDocument", back_populates="legal_hold")


class LegalHoldDocument(Base):
    __tablename__ = "legal_hold_documents"
    __table_args__ = (
        UniqueConstraint(
            "legal_hold_id", "document_id",
            name="uq_legal_hold_documents_hold_doc",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    legal_hold_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_holds.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    added_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    legal_hold = relationship("LegalHold", back_populates="documents")
    document = relationship("Document")
    adder = relationship("Person", foreign_keys=[added_by])
```

**Legal hold flow:**
1. Create `LegalHold` with name/description
2. Add documents via `LegalHoldDocument` junction
3. Retention service checks for active legal holds before executing disposition
4. If any hold exists → set `disposition_status = "held"` and skip

---

## Comments & Collaboration

### `comments`

Threaded comments on documents via self-referential `parent_id`.

```python
class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_document_id", "document_id"),
        Index("ix_comments_parent_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    status: Mapped[CommentStatus] = mapped_column(
        Enum(CommentStatus), default=CommentStatus.active
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    document = relationship("Document", back_populates="comments")
    author = relationship("Person", foreign_keys=[author_id])
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", back_populates="parent")
```

### `document_subscriptions`

Event-based notification subscriptions. Users choose which events they want to be notified about.

```python
class DocumentSubscription(Base):
    __tablename__ = "document_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "person_id",
            name="uq_document_subscriptions_doc_person",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    event_types: Mapped[list] = mapped_column(
        JSON, nullable=False
    )  # ["version_created", "comment_added", "status_changed", "checkout", "checkin"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document = relationship("Document", back_populates="subscriptions")
    person = relationship("Person")
```

---

## Storage Architecture

### Object Storage (S3 / MinIO)

File blobs are stored in S3-compatible object storage. The API never proxies file content — all uploads and downloads use presigned URLs.

**Configuration** (added to `app/config.py`):

```python
# S3 / MinIO settings
s3_endpoint_url: str = os.getenv("S3_ENDPOINT_URL", "")
s3_access_key: str = os.getenv("S3_ACCESS_KEY", "")
s3_secret_key: str = os.getenv("S3_SECRET_KEY", "")
s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "ecm-documents")
s3_region: str = os.getenv("S3_REGION", "us-east-1")
s3_presigned_url_expiry: int = int(os.getenv("S3_PRESIGNED_URL_EXPIRY", "3600"))
```

**Storage key format:**
```
documents/<document_id>/<version_number>/<uuid4>/<original_filename>
```
Example: `documents/a1b2c3d4-.../3/e5f6a7b8-.../quarterly-report.pdf`

**Upload flow (presigned PUT):**
```
1. Client → POST /api/ecm/documents/{id}/versions/upload-url
   Body: { "file_name": "report.pdf", "mime_type": "application/pdf", "file_size": 1048576 }
2. Server → generates storage_key, creates presigned PUT URL
   Response: { "upload_url": "https://s3.../...", "storage_key": "documents/..." }
3. Client → PUT <upload_url> with file body (direct to S3)
4. Client → POST /api/ecm/documents/{id}/versions/confirm
   Body: { "storage_key": "...", "checksum_sha256": "abc123..." }
5. Server → verifies object exists in S3, creates DocumentVersion,
   updates Document denormalized fields
```

**Download flow (presigned GET):**
```
1. Client → GET /api/ecm/documents/{id}/versions/{version}/download-url
2. Server → checks ACLs, generates presigned GET URL
   Response: { "download_url": "https://s3.../..." }
3. Client → GET <download_url> (direct from S3)
```

---

## Search Architecture

### Phase 1: PostgreSQL Full-Text Search

Use PostgreSQL `tsvector` with a GIN index for full-text search. This avoids adding external dependencies and is sufficient for moderate document volumes.

**Generated column on `documents`:**
```sql
ALTER TABLE documents ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED;

CREATE INDEX ix_documents_search_vector ON documents USING GIN (search_vector);
```

**Query pattern:**
```python
stmt = (
    select(Document)
    .where(Document.search_vector.match(query_text))
    .order_by(func.ts_rank(Document.search_vector, func.to_tsquery(query_text)).desc())
)
```

### Future: Elasticsearch / OpenSearch

The search service will be behind an abstraction:

```python
# app/services/ecm_search.py
class ECMSearchService:
    def search(self, query: str, filters: dict, ...) -> list[uuid.UUID]: ...
```

Phase 1 implements this with PostgreSQL. A future phase can swap in Elasticsearch without changing the API layer.

---

## File Organization

All ECM code follows the existing project layout:

```
app/
├── models/
│   ├── ecm.py                  # All ECM models + enums (single file)
│   └── __init__.py             # Add ECM imports
├── schemas/
│   └── ecm.py                  # Pydantic schemas (request/response)
├── services/
│   ├── ecm_document.py         # Document CRUD, versioning, check-in/check-out
│   ├── ecm_folder.py           # Folder CRUD, hierarchy operations
│   ├── ecm_acl.py              # ACL management, permission checking
│   ├── ecm_workflow.py         # Workflow engine, task management
│   ├── ecm_retention.py        # Retention policies, disposition, legal holds
│   ├── ecm_search.py           # Search abstraction
│   └── ecm_storage.py          # S3 presigned URL generation
├── api/
│   ├── ecm_documents.py        # Document endpoints
│   ├── ecm_folders.py          # Folder endpoints
│   ├── ecm_workflows.py        # Workflow endpoints
│   ├── ecm_admin.py            # Admin: retention, legal holds, content types
│   └── ecm_search.py           # Search endpoint
├── tasks/
│   └── ecm_tasks.py            # Celery tasks: retention sweep, notification dispatch
└── config.py                   # Add S3 settings
```

**Model registration** — add to `app/models/__init__.py`:
```python
from app.models.ecm import (  # noqa: F401
    ACLPermission,
    Category,
    ClassificationLevel,
    Comment,
    CommentStatus,
    ContentType,
    DispositionAction,
    DispositionStatus,
    Document,
    DocumentACL,
    DocumentCategory,
    DocumentCheckout,
    DocumentRetention,
    DocumentStatus,
    DocumentSubscription,
    DocumentTag,
    DocumentVersion,
    Folder,
    FolderACL,
    LegalHold,
    LegalHoldDocument,
    PrincipalType,
    RetentionPolicy,
    Tag,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowInstanceStatus,
    WorkflowTask,
    WorkflowTaskStatus,
    WorkflowTaskType,
)
```

**Alembic registration** — add to `alembic/env.py`:
```python
from app.models import (  # noqa: F401
    ...
    ecm,
)
```

---

## Phased Implementation Plan

### Phase 1: Core Document Management
**Models:** `Folder`, `Document`, `DocumentVersion`, `ContentType`, `Tag`, `DocumentTag`, `Category`, `DocumentCategory`
**Enums:** `DocumentStatus`, `ClassificationLevel`
**Services:** `ecm_folder`, `ecm_document`, `ecm_storage`
**Endpoints:** Folder CRUD, document CRUD, version upload/download, tag/category management
**Dependencies:** None (only references `people` from existing models)

### Phase 2: Access Control & Check-in/Check-out
**Models:** `DocumentACL`, `FolderACL`, `DocumentCheckout`
**Enums:** `ACLPermission`, `PrincipalType`
**Services:** `ecm_acl` (permission check integrated into all document/folder services)
**Endpoints:** ACL management, check-out/check-in
**Dependencies:** Phase 1 (folders, documents)

### Phase 3: Workflows & Collaboration
**Models:** `WorkflowDefinition`, `WorkflowInstance`, `WorkflowTask`, `Comment`, `DocumentSubscription`
**Enums:** `WorkflowTaskStatus`, `WorkflowTaskType`, `WorkflowInstanceStatus`, `CommentStatus`
**Services:** `ecm_workflow`, comment/subscription handling in `ecm_document`
**Endpoints:** Workflow CRUD, task actions, comments, subscriptions
**Dependencies:** Phase 2 (ACLs for permission-gated workflow transitions)

### Phase 4: Retention & Compliance
**Models:** `RetentionPolicy`, `DocumentRetention`, `LegalHold`, `LegalHoldDocument`
**Enums:** `DispositionAction`, `DispositionStatus`
**Services:** `ecm_retention`
**Tasks:** Celery retention sweep task (runs on schedule)
**Endpoints:** Retention policy CRUD, legal hold management, disposition actions
**Dependencies:** Phase 1 (documents, content types, categories)

---

## Migration Strategy

### Enum Creation Order
PostgreSQL enums must be created before any table references them. Alembic migration order:

1. Create all enum types (`documentstatus`, `classificationlevel`, `aclpermission`, `principaltype`, `workflowtaskstatus`, `workflowtasktype`, `workflowinstancestatus`, `dispositionaction`, `dispositionstatus`, `commentstatus`)
2. Create tables with no FK dependencies: `content_types`, `tags`, `categories`, `retention_policies`, `workflow_definitions`, `legal_holds`
3. Create `folders` (self-referential FK, no circular deps)
4. Create `documents` (FK → `folders`, `people`, `content_types`; FK → `document_versions` is nullable, added in step 5)
5. Create `document_versions` (FK → `documents`, `people`)
6. Add FK constraint `documents.current_version_id → document_versions.id` (ALTER TABLE; handles circular FK)
7. Create all remaining tables (junction tables, ACLs, checkouts, workflow instances/tasks, comments, subscriptions, retentions, legal hold documents)
8. Create GIN index for full-text search

### Circular FK: `documents` ↔ `document_versions`

`documents.current_version_id` references `document_versions.id`, while `document_versions.document_id` references `documents.id`. Handle this by:
1. Creating `documents` first with `current_version_id` as a plain nullable UUID column (no FK)
2. Creating `document_versions` with its FK to `documents`
3. Adding the FK constraint on `documents.current_version_id` via `ALTER TABLE`

This is a standard Alembic pattern using `op.create_foreign_key()` in a separate migration step.

### GIN Index

The full-text search `tsvector` column and GIN index should be created in a separate migration to keep the initial migration fast. Use `CREATE INDEX CONCURRENTLY` in production:

```python
# In Alembic migration (non-transactional for CONCURRENTLY)
from alembic import op

def upgrade():
    op.execute("""
        ALTER TABLE documents ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
        ) STORED
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY ix_documents_search_vector
        ON documents USING GIN (search_vector)
    """)
```

---

## Key Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Folder hierarchy | Materialized path (`path` column) | O(1) subtree queries via `LIKE`; folder moves are rare in ECM; simpler than nested sets or CTEs |
| 2 | Metadata schema | JSON in `ContentType.schema` | Avoids EAV antipattern; validated in service layer via `jsonschema`; flexible per content type |
| 3 | ACL tables | Separate `DocumentACL` + `FolderACL` | Real FK constraints on `document_id`/`folder_id`; different columns (`is_inherited`); distinct query patterns |
| 4 | ACL principal | Polymorphic (`principal_type` + `principal_id`) | Supports both person and role principals without separate tables; checked in app code |
| 5 | Checkout mechanism | Separate table with `UNIQUE(document_id)` | DB-level exclusivity guarantee; hard-delete on check-in keeps table small |
| 6 | Workflow states | JSON in `WorkflowDefinition.states` | Read-heavy config; state machine evaluated in app code; avoids table-per-state explosion |
| 7 | Denormalized doc fields | `file_size`, `mime_type`, `storage_key`, `checksum_sha256` on `Document` | Avoids JOIN to `document_versions` on every list query; updated atomically with new version |
| 8 | Version immutability | No `updated_at` on `DocumentVersion` | Append-only design; soft delete (`is_active=False`) is the only mutation |
| 9 | File storage | S3/MinIO with presigned URLs | Avoids proxying large files through API; client uploads/downloads directly to object storage |
| 10 | Search (Phase 1) | PostgreSQL `tsvector` + GIN index | No external dependency; adequate for moderate volumes; swappable via abstraction layer |
| 11 | Single model file | All ECM models in `app/models/ecm.py` | Follows existing pattern (auth, rbac, person each in one file); avoids circular import issues |
| 12 | UUID primary keys | `UUID(as_uuid=True)` with `uuid.uuid4` default | Matches existing codebase convention; no sequential ID exposure |
| 13 | Soft delete default | `is_active: Mapped[bool]` on all tables | Matches existing convention; audit trail preserved; except `document_checkouts` (hard delete) |
| 14 | Timestamps | `DateTime(timezone=True)` with UTC lambdas | Matches existing `created_at`/`updated_at` pattern throughout codebase |
| 15 | Comment threading | Self-referential `parent_id` on `comments` | Simple two-level threading; no closure table needed for typical comment depths |

---

## Consequences

### Positive

- **Complete ECM domain** — all standard ECM capabilities (documents, folders, versions, workflows, retention, ACLs) are covered in a single coherent design
- **Consistent with existing codebase** — same UUID PKs, `Mapped[]` annotations, timestamp patterns, `is_active` soft delete, `metadata_` JSON columns
- **Database-enforced integrity** — unique constraints prevent duplicate checkouts, duplicate tags, duplicate ACLs; FK constraints maintain referential integrity
- **Scalable hierarchy** — materialized path enables O(1) subtree queries for folders and categories without recursive CTEs
- **No external dependencies for MVP** — PostgreSQL handles full-text search, JSON storage, and all ACL logic; S3/MinIO for blobs
- **Phased delivery** — four independent phases allow incremental delivery; Phase 1 is fully functional without workflows or retention
- **Presigned URL uploads** — no file proxy bottleneck; API servers remain stateless and lightweight

### Negative

- **Materialized path maintenance** — folder moves require updating `path` for all descendants (mitigated: moves are rare in ECM)
- **Denormalized document fields** — must be updated atomically when a new version is created (mitigated: encapsulated in service layer)
- **Polymorphic ACL principal** — no FK constraint to `people`/`roles` on `principal_id` (mitigated: validated in service layer; indexed for query performance)
- **JSON workflow states** — no DB-level validation of state machine structure (mitigated: validated in service layer on create/update)
- **Single model file** — `app/models/ecm.py` will be large (~500-600 lines) (mitigated: well-organized with clear sections; can split later if needed)

### Risks

- **PostgreSQL search limits** — `tsvector` search may not scale beyond ~1M documents with complex queries. Mitigation: search abstraction layer allows swapping to Elasticsearch without API changes.
- **ACL query performance** — folder walk for deep hierarchies could be slow. Mitigation: materialized path limits walk to `depth` levels; GIN index on `path`; cache hot ACL results in Redis (future).
- **S3 presigned URL expiry** — clients must complete upload within expiry window (default 1 hour). Mitigation: configurable expiry; multipart upload for large files (future enhancement).
- **Legal hold complexity** — disposition sweep must check all active holds before any action. Mitigation: indexed query on `legal_hold_documents`; sweep runs as background Celery task with configurable schedule.

---

## Summary

**20 model classes:**
Folder, Document, DocumentVersion, ContentType, Tag, DocumentTag, Category, DocumentCategory, DocumentCheckout, WorkflowDefinition, WorkflowInstance, WorkflowTask, DocumentACL, FolderACL, RetentionPolicy, DocumentRetention, LegalHold, LegalHoldDocument, Comment, DocumentSubscription

**10 enums:**
DocumentStatus, ClassificationLevel, ACLPermission, PrincipalType, WorkflowTaskStatus, WorkflowTaskType, WorkflowInstanceStatus, DispositionAction, DispositionStatus, CommentStatus

**4 implementation phases:**
1. Core Document Management (folders, documents, versions, metadata)
2. Access Control & Check-in/Check-out (ACLs, checkouts)
3. Workflows & Collaboration (workflow engine, comments, subscriptions)
4. Retention & Compliance (retention policies, disposition, legal holds)
