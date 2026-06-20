from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ── 请求模型 ───────────────────────────────────────────────────────────

class QuestionBankCreate(BaseModel):
    """新增题目请求"""
    category: str = Field(..., description="分类：technical / behavioral / system_design / project")
    position_tag: str = Field(..., description="岗位标签：python_backend / java_backend / vue_frontend")
    difficulty: Literal["easy", "medium", "hard"] = Field(..., description="难度")
    question: str = Field(..., min_length=1, description="题面")
    reference_answer: Optional[str] = Field(None, description="参考答案")
    key_points: Optional[List[str]] = Field(None, description="答题要点列表")
    tags: Optional[List[str]] = Field(None, description="标签数组")
    source: Optional[str] = Field("manual", description="来源")


class QuestionBankUpdate(BaseModel):
    """更新题目请求（所有字段可选）"""
    category: Optional[str] = None
    position_tag: Optional[str] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    question: Optional[str] = Field(None, min_length=1)
    reference_answer: Optional[str] = None
    key_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class QuestionBankToggle(BaseModel):
    is_active: bool


class QuestionBankBatchImport(BaseModel):
    """批量导入请求"""
    items: List[QuestionBankCreate] = Field(..., min_length=1, max_length=500)


class QuestionBankTestRetrieve(BaseModel):
    """检索测试请求"""
    query: str = Field(..., description="查询文本（如 'Python 协程 异步'）")
    k: int = Field(20, ge=1, le=50, description="返回数量")
    position_tag: Optional[str] = Field(None, description="岗位筛选")
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    min_score: float = Field(0.7, ge=0, le=1, description="最低相似度")


# ── 响应模型 ───────────────────────────────────────────────────────────

class QuestionBankResponse(BaseModel):
    """题目响应（不含 embedding 向量本身，太大）"""
    id: int
    category: str
    position_tag: str
    difficulty: str
    question: str
    reference_answer: Optional[str]
    key_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    source: str
    use_count: int
    is_active: bool
    has_embedding: bool = Field(False, description="是否已向量化")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuestionBankRetrievedItem(BaseModel):
    """检索返回的题目"""
    id: int
    category: str
    position_tag: str
    difficulty: str
    question: str
    reference_answer: Optional[str]
    key_points: Optional[List[str]] = None
    similarity: float
    source: str = "from_bank"
