"""Add ai_studio_task.attachment_ids_json.

Revision ID: 703cb42bd437
Revises: b259df8367b2
"""
import sqlalchemy as sa

from superset.migrations.shared.utils import add_columns, drop_columns

revision = "703cb42bd437"
down_revision = "b259df8367b2"


def upgrade() -> None:
    add_columns(
        "ai_studio_task",
        sa.Column("attachment_ids_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    drop_columns("ai_studio_task", "attachment_ids_json")
