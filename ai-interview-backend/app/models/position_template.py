from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from .base import BaseModel


class PositionTemplate(BaseModel):
    """岗位模板库 —— Agent 岗位匹配的核心数据源"""
    __tablename__ = "position_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    position_tag = Column(String(100), unique=True, index=True, nullable=False)  # python_backend / java_backend / ...
    title = Column(String(200), nullable=False)                                  # 岗位展示名
    category = Column(String(50), index=True, nullable=False)                    # backend / frontend / ai / mobile / devops
    level = Column(String(20), nullable=False, default="junior")                 # intern / junior / mid / senior

    core_skills = Column(JSONB, nullable=True)                                   # ["Python", "FastAPI", ...]
    nice_to_have_skills = Column(JSONB, nullable=True)                           # ["Kubernetes", "微服务"]
    project_keywords = Column(JSONB, nullable=True)                              # ["电商", "高并发"]
    focus_topics = Column(JSONB, nullable=True)                                  # 推荐面试重点
    recommended_query_keywords = Column(JSONB, nullable=True)                    # 题库 RAG 检索关键词

    recommended_difficulty = Column(String(20), default="medium")                # easy / medium / hard
    recommended_question_count = Column(Integer, default=8)
    jd_summary = Column(Text, nullable=True)                                     # 岗位 JD 摘要
    typical_companies = Column(JSONB, nullable=True)

    sort_order = Column(Integer, default=0, index=True)
    is_active = Column(Boolean, default=True, index=True)
