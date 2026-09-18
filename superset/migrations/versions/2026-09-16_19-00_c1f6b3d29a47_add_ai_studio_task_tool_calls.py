"""Add ai_studio_task.tool_calls_json.

Revision ID: c1f6b3d29a47
Revises: b5e7a2c4d813
"""
import sqlalchemy as sa

from superset.migrations.shared.utils import add_columns, drop_columns

revision = "c1f6b3d29a47"
down_revision = "b5e7a2c4d813"


def upgrade() -> None:
    add_columns(
        "ai_studio_task",
        sa.Column("tool_calls_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    drop_columns("ai_studio_task", "tool_calls_json")
