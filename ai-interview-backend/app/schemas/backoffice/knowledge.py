from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── 请求模型 ───────────────────────────────────────────────────────────

class KnowledgeDocumentToggle(BaseModel):
    is_active: bool


class KnowledgeTestRetrieve(BaseModel):
    """文档检索测试"""
    query: str = Field(..., description="查询文本")
    k: int = Field(4, ge=1, le=20)
    category: Optional[str] = None
    min_score: float = Field(0.3, ge=0, le=1)


# ── 响应模型 ───────────────────────────────────────────────────────────

class KnowledgeDocumentResponse(BaseModel):
    id: int
    title: str
    file_name: Optional[str]
    file_url: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    category: Optional[str]
    tags: Optional[List[str]] = None
    description: Optional[str]
    chunk_count: int
    status: str
    error_message: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    has_embedding: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeRetrievedChunk(BaseModel):
    """检索返回的 chunk"""
    id: int
    document_id: int
    content: str
    similarity: float
