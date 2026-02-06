"""ecm phase4 retention and compliance

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-06 03:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    dispositionaction = sa.Enum(
        "retain", "archive", "destroy", name="dispositionaction"
    )
    dispositionstatus = sa.Enum(
        "pending", "eligible", "held", "completed", name="dispositionstatus"
    )
    dispositionaction.create(op.get_bind(), checkfirst=True)
    dispositionstatus.create(op.get_bind(), checkfirst=True)

    # --- Retention Policies ---
    op.create_table(
        "retention_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column(
            "disposition_action",
            sa.Enum(
                "retain",
                "archive",
                "destroy",
                name="dispositionaction",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content_type_id", sa.UUID(), nullable=True),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["content_type_id"], ["content_types.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_retention_policies_name"),
    )

    # --- Document Retentions ---
    op.create_table(
        "document_retentions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("policy_id", sa.UUID(), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "disposition_status",
            sa.Enum(
                "pending",
                "eligible",
                "held",
                "completed",
                name="dispositionstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposed_by", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["retention_policies.id"]),
        sa.ForeignKeyConstraint(["disposed_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "policy_id",
            name="uq_document_retentions_doc_policy",
        ),
    )
    op.create_index(
        "ix_document_retentions_status",
        "document_retentions",
        ["disposition_status"],
    )
    op.create_index(
        "ix_document_retentions_expires_at",
        "document_retentions",
        ["retention_expires_at"],
    )

    # --- Legal Holds ---
    op.create_table(
        "legal_holds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reference_number", sa.String(120), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Legal Hold Documents ---
    op.create_table(
        "legal_hold_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("legal_hold_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["legal_hold_id"], ["legal_holds.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["added_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legal_hold_id",
            "document_id",
            name="uq_legal_hold_documents_hold_doc",
        ),
    )


def downgrade() -> None:
    op.drop_table("legal_hold_documents")
    op.drop_table("legal_holds")

    op.drop_index("ix_document_retentions_expires_at", table_name="document_retentions")
    op.drop_index("ix_document_retentions_status", table_name="document_retentions")
    op.drop_table("document_retentions")

    op.drop_table("retention_policies")

    for enum_name in ["dispositionstatus", "dispositionaction"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
