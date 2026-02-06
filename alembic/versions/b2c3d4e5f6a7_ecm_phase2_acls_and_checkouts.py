"""ecm phase2 acls and checkouts

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-06 01:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    aclpermission = sa.Enum("read", "write", "delete", "manage", name="aclpermission")
    principaltype = sa.Enum("person", "role", name="principaltype")
    aclpermission.create(op.get_bind(), checkfirst=True)
    principaltype.create(op.get_bind(), checkfirst=True)

    # --- Document ACLs ---
    op.create_table(
        "document_acls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column(
            "principal_type",
            sa.Enum("person", "role", name="principaltype", create_type=False),
            nullable=False,
        ),
        sa.Column("principal_id", sa.UUID(), nullable=False),
        sa.Column(
            "permission",
            sa.Enum(
                "read",
                "write",
                "delete",
                "manage",
                name="aclpermission",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("granted_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "principal_type",
            "principal_id",
            "permission",
            name="uq_document_acls_doc_principal_perm",
        ),
    )
    op.create_index("ix_document_acls_document_id", "document_acls", ["document_id"])
    op.create_index(
        "ix_document_acls_principal",
        "document_acls",
        ["principal_type", "principal_id"],
    )

    # --- Folder ACLs ---
    op.create_table(
        "folder_acls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("folder_id", sa.UUID(), nullable=False),
        sa.Column(
            "principal_type",
            sa.Enum("person", "role", name="principaltype", create_type=False),
            nullable=False,
        ),
        sa.Column("principal_id", sa.UUID(), nullable=False),
        sa.Column(
            "permission",
            sa.Enum(
                "read",
                "write",
                "delete",
                "manage",
                name="aclpermission",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("is_inherited", sa.Boolean(), nullable=False),
        sa.Column("granted_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"]),
        sa.ForeignKeyConstraint(["granted_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "folder_id",
            "principal_type",
            "principal_id",
            "permission",
            name="uq_folder_acls_folder_principal_perm",
        ),
    )
    op.create_index("ix_folder_acls_folder_id", "folder_acls", ["folder_id"])
    op.create_index(
        "ix_folder_acls_principal",
        "folder_acls",
        ["principal_type", "principal_id"],
    )

    # --- Document Checkouts ---
    op.create_table(
        "document_checkouts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("checked_out_by", sa.UUID(), nullable=False),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["checked_out_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_document_checkouts_document"),
    )


def downgrade() -> None:
    op.drop_table("document_checkouts")

    op.drop_index("ix_folder_acls_principal", table_name="folder_acls")
    op.drop_index("ix_folder_acls_folder_id", table_name="folder_acls")
    op.drop_table("folder_acls")

    op.drop_index("ix_document_acls_principal", table_name="document_acls")
    op.drop_index("ix_document_acls_document_id", table_name="document_acls")
    op.drop_table("document_acls")

    for enum_name in ["aclpermission", "principaltype"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
