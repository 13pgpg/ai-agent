"""add_position_templates_table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-04 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "position_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("position_tag", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("level", sa.String(20), server_default="junior", nullable=False),

        sa.Column("core_skills", JSONB(), nullable=True),
        sa.Column("nice_to_have_skills", JSONB(), nullable=True),
        sa.Column("project_keywords", JSONB(), nullable=True),
        sa.Column("focus_topics", JSONB(), nullable=True),
        sa.Column("recommended_query_keywords", JSONB(), nullable=True),

        sa.Column("recommended_difficulty", sa.String(20), server_default="medium", nullable=False),
        sa.Column("recommended_question_count", sa.Integer(), server_default="8", nullable=False),
        sa.Column("jd_summary", sa.Text(), nullable=True),
        sa.Column("typical_companies", JSONB(), nullable=True),

        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_position_templates_position_tag", "position_templates", ["position_tag"], unique=True)
    op.create_index("ix_position_templates_category", "position_templates", ["category"])
    op.create_index("ix_position_templates_is_active", "position_templates", ["is_active"])
    op.create_index("ix_position_templates_sort_order", "position_templates", ["sort_order"])


def downgrade() -> None:
    op.drop_table("position_templates")
