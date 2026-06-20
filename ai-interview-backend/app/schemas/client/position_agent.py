from pydantic import BaseModel, Field
from typing import Optional


class PositionMatchRequest(BaseModel):
    resume_id: int = Field(..., description="已解析完成的简历 ID")
    target_direction: Optional[str] = Field(None, description="用户期望方向，如 'Python 后端'（可选，会传给 Agent 作参考）")


class StartInterviewFromAgentRequest(BaseModel):
    resume_id: int
    position_tag: str
    difficulty: Optional[str] = None
    total_questions: Optional[int] = None
