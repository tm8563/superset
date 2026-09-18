"""Add ai_studio_provider table.

Revision ID: afb32b2091ae
Revises: c9a1d5e7f201
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy_utils import UUIDType

from superset.extensions import encrypted_field_factory
from superset.migrations.shared.utils import create_table

revision = "afb32b2091ae"
down_revision = "c9a1d5e7f201"


def upgrade() -> None:
    create_table(
        "ai_studio_provider",
        sa.Column("id", UUIDType(binary=True), primary_key=True),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column(
            "api_key", encrypted_field_factory.create(sa.String(1024)), nullable=True
        ),
        sa.Column("default_model", sa.String(length=256), nullable=True),
        sa.Column("models_json", sa.Text(), nullable=False),
        sa.Column("capabilities_json", sa.Text(), nullable=False),
        sa.Column("effort_levels_json", sa.Text(), nullable=False),
        sa.Column("effort_param", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by_fk", sa.Integer(), sa.ForeignKey("ab_user.id"), nullable=True),
        sa.Column("created_on", sa.DateTime(), nullable=False),
        sa.Column("changed_by_fk", sa.Integer(), sa.ForeignKey("ab_user.id"), nullable=True),
        sa.Column("changed_on", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_studio_provider_enabled", "ai_studio_provider", ["enabled"])


def downgrade() -> None:
    op.drop_table("ai_studio_provider")
