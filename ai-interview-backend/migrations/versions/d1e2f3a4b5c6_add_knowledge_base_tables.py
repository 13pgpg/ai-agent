"""add_knowledge_base_tables

Revision ID: d1e2f3a4b5c6
Revises: c7f982abaaf0
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c7f982abaaf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector 扩展（已通过 psql 安装，保留此行确保幂等）
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── knowledge_documents ──────────────────────────────────────────────
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("file_type", sa.String(20), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("tags", JSONB(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("admins.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_documents_id", "knowledge_documents", ["id"])
    op.create_index("ix_knowledge_documents_category", "knowledge_documents", ["category"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])
    op.create_index("ix_knowledge_documents_is_active", "knowledge_documents", ["is_active"])

    # ── knowledge_chunks ─────────────────────────────────────────────────
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_id", "knowledge_chunks", ["id"])
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])

    # embedding 列单独用原生 SQL（Alembic 不支持 vector 类型）
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(1024)")
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    # ── question_bank ────────────────────────────────────────────────────
    op.create_table(
        "question_bank",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("position_tag", sa.String(100), nullable=False),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("key_points", JSONB(), nullable=True),
        sa.Column("tags", JSONB(), nullable=True),
        sa.Column("embedding_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), server_default="manual", nullable=False),
        sa.Column("use_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admins.id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_question_bank_id", "question_bank", ["id"])
    op.create_index("ix_question_bank_category", "question_bank", ["category"])
    op.create_index("ix_question_bank_position_tag", "question_bank", ["position_tag"])
    op.create_index("ix_question_bank_difficulty", "question_bank", ["difficulty"])
    op.create_index("ix_question_bank_is_active", "question_bank", ["is_active"])
    op.create_index(
        "ix_question_bank_filters",
        "question_bank",
        ["is_active", "position_tag", "difficulty"],
    )

    # embedding 列 + HNSW 索引
    op.execute("ALTER TABLE question_bank ADD COLUMN embedding vector(1024)")
    op.execute(
        "CREATE INDEX ix_question_bank_embedding "
        "ON question_bank USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("question_bank")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
