"""ecm phase3 workflows and collaboration

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-06 02:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums ---
    workflowtaskstatus = sa.Enum(
        "pending", "approved", "rejected", "cancelled", name="workflowtaskstatus"
    )
    workflowtasktype = sa.Enum(
        "approval", "review", "sign_off", name="workflowtasktype"
    )
    workflowinstancestatus = sa.Enum(
        "active", "completed", "cancelled", name="workflowinstancestatus"
    )
    commentstatus = sa.Enum("active", "deleted", name="commentstatus")

    workflowtaskstatus.create(op.get_bind(), checkfirst=True)
    workflowtasktype.create(op.get_bind(), checkfirst=True)
    workflowinstancestatus.create(op.get_bind(), checkfirst=True)
    commentstatus.create(op.get_bind(), checkfirst=True)

    # --- Workflow Definitions ---
    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("states", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_workflow_definitions_name"),
    )

    # --- Workflow Instances ---
    op.create_table(
        "workflow_instances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("definition_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("current_state", sa.String(80), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "completed",
                "cancelled",
                name="workflowinstancestatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("started_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["definition_id"], ["workflow_definitions.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["started_by"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_instances_document_id",
        "workflow_instances",
        ["document_id"],
    )
    op.create_index(
        "ix_workflow_instances_status",
        "workflow_instances",
        ["status"],
    )

    # --- Workflow Tasks ---
    op.create_table(
        "workflow_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("instance_id", sa.UUID(), nullable=False),
        sa.Column(
            "task_type",
            sa.Enum(
                "approval",
                "review",
                "sign_off",
                name="workflowtasktype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "cancelled",
                name="workflowtaskstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("assignee_id", sa.UUID(), nullable=False),
        sa.Column("from_state", sa.String(80), nullable=False),
        sa.Column("to_state", sa.String(80), nullable=False),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["workflow_instances.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_tasks_instance_id", "workflow_tasks", ["instance_id"])
    op.create_index("ix_workflow_tasks_assignee_id", "workflow_tasks", ["assignee_id"])
    op.create_index("ix_workflow_tasks_status", "workflow_tasks", ["status"])

    # --- Comments ---
    op.create_table(
        "comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "deleted", name="commentstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_document_id", "comments", ["document_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])

    # --- Document Subscriptions ---
    op.create_table(
        "document_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["people.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "person_id", name="uq_document_subscriptions_doc_person"
        ),
    )


def downgrade() -> None:
    op.drop_table("document_subscriptions")

    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_index("ix_comments_document_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_workflow_tasks_status", table_name="workflow_tasks")
    op.drop_index("ix_workflow_tasks_assignee_id", table_name="workflow_tasks")
    op.drop_index("ix_workflow_tasks_instance_id", table_name="workflow_tasks")
    op.drop_table("workflow_tasks")

    op.drop_index("ix_workflow_instances_status", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_document_id", table_name="workflow_instances")
    op.drop_table("workflow_instances")

    op.drop_table("workflow_definitions")

    for enum_name in [
        "commentstatus",
        "workflowinstancestatus",
        "workflowtasktype",
        "workflowtaskstatus",
    ]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
