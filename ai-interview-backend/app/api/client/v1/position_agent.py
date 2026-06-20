"""
岗位匹配 Agent API（用户端）
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.schemas.response import ApiResponse
from app.schemas.client.position_agent import (
    PositionMatchRequest,
    StartInterviewFromAgentRequest,
)
from app.services.client.position_agent_service import PositionAgentService
from app.services.client.position_agent_tools import start_mock_interview

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/match")
async def match_positions_for_resume(
    payload: PositionMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    运行岗位匹配 Agent，基于简历输出结构化的岗位推荐结果。

    Agent 会自动按以下顺序调用工具：
        get_parsed_resume → build_candidate_profile → match_positions
        → get_position_interview_focus
    """
    # 校验简历归属
    resume = (await db.execute(
        select(Resume).where(
            Resume.id == payload.resume_id,
            Resume.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not resume:
        return ApiResponse.failed("简历不存在或无权访问", body_code=404, http_code=404)
    if resume.status != "completed":
        return ApiResponse.failed(
            f"简历尚未解析完成（当前状态: {resume.status}）",
            body_code=400,
        )

    logger.info(f"用户 {current_user.id} 触发 Agent 匹配，resume_id={payload.resume_id}")

    response = await PositionAgentService.run_agent(
        resume_id=payload.resume_id,
        target_direction=payload.target_direction,
    )

    if response["result"].get("error"):
        return ApiResponse.failed(
            response["result"].get("error"),
            body_code=500,
            data=response,
        )

    return ApiResponse.success(response, message="岗位匹配完成")


@router.post("/start-interview")
async def start_interview_from_agent(
    payload: StartInterviewFromAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    从 Agent 推荐结果直接启动一次专项模拟面试。
    内部直接复用 start_mock_interview 工具函数，自动走题库 RAG。
    """
    # 校验简历归属
    resume = (await db.execute(
        select(Resume).where(
            Resume.id == payload.resume_id,
            Resume.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not resume:
        return ApiResponse.failed("简历不存在或无权访问", body_code=404, http_code=404)

    # 直接调用 @tool 内部函数（注意 @tool 包装后要走 .ainvoke 调用）
    result = await start_mock_interview.ainvoke({
        "resume_id": payload.resume_id,
        "position_tag": payload.position_tag,
        "difficulty": payload.difficulty,
        "total_questions": payload.total_questions,
    })

    if isinstance(result, dict) and result.get("error"):
        return ApiResponse.failed(result["error"], body_code=400)

    return ApiResponse.success(result, message="面试已开始")
