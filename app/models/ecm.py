import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ---------------------------------------------------------------------------
# Enums — Phase 1
# ---------------------------------------------------------------------------


class DocumentStatus(enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"
    deleted = "deleted"


class ClassificationLevel(enum.Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


# ---------------------------------------------------------------------------
# Enums — Phase 2
# ---------------------------------------------------------------------------


class ACLPermission(enum.Enum):
    read = "read"
    write = "write"
    delete = "delete"
    manage = "manage"


class PrincipalType(enum.Enum):
    person = "person"
    role = "role"


# ---------------------------------------------------------------------------
# Enums — Phase 3
# ---------------------------------------------------------------------------


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


class CommentStatus(enum.Enum):
    active = "active"
    deleted = "deleted"


# ---------------------------------------------------------------------------
# Enums — Phase 4
# ---------------------------------------------------------------------------


class DispositionAction(enum.Enum):
    retain = "retain"
    archive = "archive"
    destroy = "destroy"


class DispositionStatus(enum.Enum):
    pending = "pending"
    eligible = "eligible"
    held = "held"
    completed = "completed"


# ---------------------------------------------------------------------------
# Core Content — Folders
# ---------------------------------------------------------------------------


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
    path: Mapped[str] = mapped_column(String(4000), nullable=False, default="/")
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

    parent = relationship("Folder", remote_side="Folder.id", back_populates="children")
    children = relationship("Folder", back_populates="parent")
    documents = relationship("Document", back_populates="folder")
    creator = relationship("Person", foreign_keys=[created_by])
    acls = relationship("FolderACL", back_populates="folder")


# ---------------------------------------------------------------------------
# Core Content — Documents
# ---------------------------------------------------------------------------


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
    current_version = relationship("DocumentVersion", foreign_keys=[current_version_id])
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
    acls = relationship("DocumentACL", back_populates="document")
    comments = relationship("Comment", back_populates="document")
    subscriptions = relationship("DocumentSubscription", back_populates="document")


# ---------------------------------------------------------------------------
# Core Content — Document Versions (immutable — no updated_at)
# ---------------------------------------------------------------------------


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_doc_version",
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


# ---------------------------------------------------------------------------
# Metadata & Classification — Content Types
# ---------------------------------------------------------------------------


class ContentType(Base):
    __tablename__ = "content_types"
    __table_args__ = (UniqueConstraint("name", name="uq_content_types_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    schema: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Metadata & Classification — Tags
# ---------------------------------------------------------------------------


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tags_name"),)

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
        UniqueConstraint("document_id", "tag_id", name="uq_document_tags_doc_tag"),
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


# ---------------------------------------------------------------------------
# Metadata & Classification — Categories (hierarchical, materialized path)
# ---------------------------------------------------------------------------


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

    parent = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children = relationship("Category", back_populates="parent")
    documents = relationship("DocumentCategory", back_populates="category")


class DocumentCategory(Base):
    __tablename__ = "document_categories"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "category_id",
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


# ---------------------------------------------------------------------------
# Access Control — Document ACLs
# ---------------------------------------------------------------------------


class DocumentACL(Base):
    __tablename__ = "document_acls"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "principal_type",
            "principal_id",
            "permission",
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
    principal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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


# ---------------------------------------------------------------------------
# Access Control — Folder ACLs
# ---------------------------------------------------------------------------


class FolderACL(Base):
    __tablename__ = "folder_acls"
    __table_args__ = (
        UniqueConstraint(
            "folder_id",
            "principal_type",
            "principal_id",
            "permission",
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
    principal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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


# ---------------------------------------------------------------------------
# Check-in / Check-out — Document Checkouts (hard-deleted on check-in)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workflows — Definitions
# ---------------------------------------------------------------------------


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    __table_args__ = (UniqueConstraint("name", name="uq_workflow_definitions_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    states: Mapped[dict] = mapped_column(JSON, nullable=False)
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


# ---------------------------------------------------------------------------
# Workflows — Instances
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workflows — Tasks
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Comments & Collaboration — Comments
# ---------------------------------------------------------------------------


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
    parent = relationship("Comment", remote_side="Comment.id", back_populates="replies")
    replies = relationship("Comment", back_populates="parent")


# ---------------------------------------------------------------------------
# Comments & Collaboration — Document Subscriptions
# ---------------------------------------------------------------------------


class DocumentSubscription(Base):
    __tablename__ = "document_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "person_id",
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
    event_types: Mapped[list] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document = relationship("Document", back_populates="subscriptions")
    person = relationship("Person")


# ---------------------------------------------------------------------------
# Retention & Compliance — Retention Policies
# ---------------------------------------------------------------------------


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"
    __table_args__ = (UniqueConstraint("name", name="uq_retention_policies_name"),)

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
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
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

    content_type = relationship("ContentType")
    category = relationship("Category")


# ---------------------------------------------------------------------------
# Retention & Compliance — Document Retentions
# ---------------------------------------------------------------------------


class DocumentRetention(Base):
    __tablename__ = "document_retentions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "policy_id",
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


# ---------------------------------------------------------------------------
# Retention & Compliance — Legal Holds
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Retention & Compliance — Legal Hold Documents
# ---------------------------------------------------------------------------


class LegalHoldDocument(Base):
    __tablename__ = "legal_hold_documents"
    __table_args__ = (
        UniqueConstraint(
            "legal_hold_id",
            "document_id",
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


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_person_id", "person_id"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    person = relationship("Person", foreign_keys=[person_id])


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhookDeliveryStatus(enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        UniqueConstraint("url", "created_by", name="uq_webhook_endpoints_url_creator"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(255))
    event_types: Mapped[list] = mapped_column(JSON, nullable=False)
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
    deliveries = relationship("WebhookDelivery", back_populates="endpoint")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_endpoint_id", "endpoint_id"),
        Index("ix_webhook_deliveries_status", "status"),
        Index("ix_webhook_deliveries_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhook_endpoints.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus), default=WebhookDeliveryStatus.pending
    )
    response_status_code: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")
