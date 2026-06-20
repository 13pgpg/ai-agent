from sqlalchemy import Column, Integer, String, Text, Boolean, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from .base import BaseModel


class KnowledgeDocument(BaseModel):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    file_name = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=True)
    file_type = Column(String(20), nullable=True)       # pdf / md / docx / txt
    file_size = Column(BigInteger, nullable=True)
    category = Column(String(50), nullable=True, index=True)   # python / java / vue / system_design
    tags = Column(JSONB, nullable=True)                 # ["GIL", "异步"]
    description = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="pending", index=True)  # pending/indexing/indexed/failed
    error_message = Column(Text, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    is_active = Column(Boolean, default=True, index=True)


class KnowledgeChunk(BaseModel):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    embedding = Column(Vector(1024), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)   # 页码、位置等
