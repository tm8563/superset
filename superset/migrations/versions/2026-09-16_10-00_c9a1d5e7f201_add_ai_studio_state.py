"""Add AI Studio tasks, staged changes, and checkpoints.

Revision ID: c9a1d5e7f201
Revises: e2f3a1b9c640
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

revision = "c9a1d5e7f201"
# Was originally chained off 7e2c9a4f1b83 (the pre-merge branch point), which
# produced two heads once e2f3a1b9c640 merged the purge-audit and
# username-index branches back together — this migration had never actually
# been applied anywhere yet, so re-pointing it at the real current head is
# safe rather than needing its own merge migration.
down_revision = "e2f3a1b9c640"


def upgrade() -> None:
    op.create_table(
        "ai_studio_task",
        sa.Column("id", UUIDType(binary=True), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("ab_user.id"), nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=128)),
        sa.Column("model", sa.String(length=256)),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_on", sa.DateTime(), nullable=False),
        sa.Column("started_on", sa.DateTime()),
        sa.Column("completed_on", sa.DateTime()),
    )
    op.create_index("ix_ai_studio_task_user_id", "ai_studio_task", ["user_id"])
    op.create_index("ix_ai_studio_task_dashboard_id", "ai_studio_task", ["dashboard_id"])
    op.create_index("ix_ai_studio_task_status", "ai_studio_task", ["status"])
    op.create_table(
        "ai_studio_change_set",
        sa.Column("id", UUIDType(binary=True), primary_key=True),
        sa.Column("task_id", UUIDType(binary=True), sa.ForeignKey("ai_studio_task.id")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("ab_user.id"), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_on", sa.DateTime(), nullable=False),
        sa.Column("applied_on", sa.DateTime()),
        sa.Column("rejected_on", sa.DateTime()),
    )
    op.create_index("ix_ai_studio_change_set_task_id", "ai_studio_change_set", ["task_id"])
    op.create_index("ix_ai_studio_change_set_user_id", "ai_studio_change_set", ["user_id"])
    op.create_index("ix_ai_studio_change_set_status", "ai_studio_change_set", ["status"])
    op.create_table(
        "ai_studio_checkpoint",
        sa.Column("id", UUIDType(binary=True), primary_key=True),
        sa.Column("change_set_id", UUIDType(binary=True), sa.ForeignKey("ai_studio_change_set.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("ab_user.id"), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("restored_on", sa.DateTime()),
        sa.Column("created_on", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_studio_checkpoint_change_set_id", "ai_studio_checkpoint", ["change_set_id"])
    op.create_index("ix_ai_studio_checkpoint_user_id", "ai_studio_checkpoint", ["user_id"])


def downgrade() -> None:
    op.drop_table("ai_studio_checkpoint")
    op.drop_table("ai_studio_change_set")
    op.drop_table("ai_studio_task")
