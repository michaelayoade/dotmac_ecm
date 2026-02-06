"""ecm phase1 core document management

Revision ID: a1b2c3d4e5f6
Revises: 799a0ecebdd4
Create Date: 2026-02-06 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "799a0ecebdd4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    documentstatus = sa.Enum(
        "draft", "active", "archived", "deleted", name="documentstatus"
    )
    classificationlevel = sa.Enum(
        "public",
        "internal",
        "confidential",
        "restricted",
        name="classificationlevel",
    )
    documentstatus.create(op.get_bind(), checkfirst=True)
    classificationlevel.create(op.get_bind(), checkfirst=True)

    # --- Tables with no FK dependencies ---
    op.create_table(
        "content_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_content_types_name"),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("path", sa.String(length=4000), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "name", name="uq_categories_parent_name"),
    )
    op.create_index("ix_categories_path", "categories", ["path"])

    # --- Folders (self-referential FK) ---
    op.create_table(
        "folders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("path", sa.String(length=4000), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "name", name="uq_folders_parent_name"),
    )
    op.create_index("ix_folders_path", "folders", ["path"])

    # --- Documents (without current_version_id FK — added after document_versions) ---
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("folder_id", sa.UUID(), nullable=True),
        sa.Column("content_type_id", sa.UUID(), nullable=True),
        sa.Column(
            "classification",
            sa.Enum(
                "public",
                "internal",
                "confidential",
                "restricted",
                name="classificationlevel",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "active",
                "archived",
                "deleted",
                name="documentstatus",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"]),
        sa.ForeignKeyConstraint(["content_type_id"], ["content_types.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"])
    op.create_index("ix_documents_created_by", "documents", ["created_by"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # --- Document Versions ---
    op.create_table(
        "document_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_doc_version",
        ),
    )
    op.create_index(
        "ix_document_versions_document_id", "document_versions", ["document_id"]
    )
    op.create_index(
        "ix_document_versions_storage_key", "document_versions", ["storage_key"]
    )

    # --- Add circular FK: documents.current_version_id -> document_versions.id ---
    op.create_foreign_key(
        "fk_documents_current_version_id",
        "documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
    )

    # --- Junction tables ---
    op.create_table(
        "document_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "tag_id", name="uq_document_tags_doc_tag"),
    )

    op.create_table(
        "document_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "category_id", name="uq_document_categories_doc_cat"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_categories")
    op.drop_table("document_tags")

    op.drop_constraint(
        "fk_documents_current_version_id", "documents", type_="foreignkey"
    )

    op.drop_index("ix_document_versions_storage_key", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_created_by", table_name="documents")
    op.drop_index("ix_documents_folder_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_folders_path", table_name="folders")
    op.drop_table("folders")

    op.drop_index("ix_categories_path", table_name="categories")
    op.drop_table("categories")

    op.drop_table("tags")
    op.drop_table("content_types")

    for enum_name in ["documentstatus", "classificationlevel"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
