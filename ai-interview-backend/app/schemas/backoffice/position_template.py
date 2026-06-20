from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ── 请求模型 ───────────────────────────────────────────────────────────

class PositionTemplateCreate(BaseModel):
    position_tag: str = Field(..., min_length=1, description="岗位标签，如 python_backend")
    title: str = Field(..., min_length=1, description="岗位展示名")
    category: Literal["backend", "frontend", "ai", "mobile", "devops"] = Field(...)
    level: Literal["intern", "junior", "mid", "senior"] = Field("junior")
    core_skills: Optional[List[str]] = None
    nice_to_have_skills: Optional[List[str]] = None
    project_keywords: Optional[List[str]] = None
    focus_topics: Optional[List[str]] = None
    recommended_query_keywords: Optional[List[str]] = None
    recommended_difficulty: Literal["easy", "medium", "hard"] = Field("medium")
    recommended_question_count: int = Field(8, ge=1, le=30)
    jd_summary: Optional[str] = None
    typical_companies: Optional[List[str]] = None
    sort_order: int = Field(0, ge=0)


class PositionTemplateUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[Literal["backend", "frontend", "ai", "mobile", "devops"]] = None
    level: Optional[Literal["intern", "junior", "mid", "senior"]] = None
    core_skills: Optional[List[str]] = None
    nice_to_have_skills: Optional[List[str]] = None
    project_keywords: Optional[List[str]] = None
    focus_topics: Optional[List[str]] = None
    recommended_query_keywords: Optional[List[str]] = None
    recommended_difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    recommended_question_count: Optional[int] = Field(None, ge=1, le=30)
    jd_summary: Optional[str] = None
    typical_companies: Optional[List[str]] = None
    sort_order: Optional[int] = Field(None, ge=0)


class PositionTemplateToggle(BaseModel):
    is_active: bool


# ── 响应模型 ───────────────────────────────────────────────────────────

class PositionTemplateResponse(BaseModel):
    id: int
    position_tag: str
    title: str
    category: str
    level: str
    core_skills: Optional[List[str]] = None
    nice_to_have_skills: Optional[List[str]] = None
    project_keywords: Optional[List[str]] = None
    focus_topics: Optional[List[str]] = None
    recommended_query_keywords: Optional[List[str]] = None
    recommended_difficulty: str
    recommended_question_count: int
    jd_summary: Optional[str] = None
    typical_companies: Optional[List[str]] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
