"""Add ai_studio_task.gtf_task_uuid.

Revision ID: b5e7a2c4d813
Revises: afb32b2091ae
"""
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from superset.migrations.shared.utils import add_columns, create_index, drop_columns, drop_index

revision = "b5e7a2c4d813"
down_revision = "afb32b2091ae"


def upgrade() -> None:
    add_columns(
        "ai_studio_task",
        sa.Column("gtf_task_uuid", UUIDType(binary=True), nullable=True),
    )
    create_index("ai_studio_task", "ix_ai_studio_task_gtf_task_uuid", ["gtf_task_uuid"])


def downgrade() -> None:
    drop_index("ai_studio_task", "ix_ai_studio_task_gtf_task_uuid")
    drop_columns("ai_studio_task", "gtf_task_uuid")
