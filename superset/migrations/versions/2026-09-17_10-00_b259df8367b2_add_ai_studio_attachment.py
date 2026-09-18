"""Add ai_studio_attachment table.

Revision ID: b259df8367b2
Revises: c1f6b3d29a47
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from superset.migrations.shared.utils import create_index, create_table, drop_index

revision = "b259df8367b2"
down_revision = "c1f6b3d29a47"


def upgrade() -> None:
    create_table(
        "ai_studio_attachment",
        sa.Column("id", UUIDType(binary=True), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("ab_user.id"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_filename", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_on", sa.DateTime(), nullable=False),
    )
    create_index("ai_studio_attachment", "ix_ai_studio_attachment_user_id", ["user_id"])
    create_index(
        "ai_studio_attachment", "ix_ai_studio_attachment_created_on", ["created_on"]
    )


def downgrade() -> None:
    drop_index("ai_studio_attachment", "ix_ai_studio_attachment_created_on")
    drop_index("ai_studio_attachment", "ix_ai_studio_attachment_user_id")
    op.drop_table("ai_studio_attachment")
