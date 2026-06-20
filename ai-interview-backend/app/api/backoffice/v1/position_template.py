"""
岗位模板管理 API（管理端）
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.backoffice.position_template import (
    PositionTemplateCreate,
    PositionTemplateUpdate,
    PositionTemplateToggle,
)
from app.services.backoffice.position_template_service import PositionTemplateService

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(t) -> dict:
    return {
        "id": t.id,
        "position_tag": t.position_tag,
        "title": t.title,
        "category": t.category,
        "level": t.level,
        "core_skills": t.core_skills,
        "nice_to_have_skills": t.nice_to_have_skills,
        "project_keywords": t.project_keywords,
        "focus_topics": t.focus_topics,
        "recommended_query_keywords": t.recommended_query_keywords,
        "recommended_difficulty": t.recommended_difficulty,
        "recommended_question_count": t.recommended_question_count,
        "jd_summary": t.jd_summary,
        "typical_companies": t.typical_companies,
        "sort_order": t.sort_order,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("")
async def list_templates(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """岗位模板列表"""
    result = await PositionTemplateService.get_list(
        db=db, page=page, size=per_page,
        category=category, is_active=is_active, search=search,
    )
    return ApiResponse.success({
        "items": [_to_response(t) for t in result["items"]],
        "total": result["total"],
        "page": page,
        "per_page": per_page,
    })


@router.post("")
async def create_template(
    payload: PositionTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """新增岗位模板"""
    try:
        t = await PositionTemplateService.create(db, payload.model_dump())
    except ValueError as e:
        return ApiResponse.failed(str(e), body_code=400)
    return ApiResponse.success(_to_response(t), message="创建成功")


@router.get("/{template_id}")
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """岗位模板详情"""
    t = await PositionTemplateService.get_by_id(db, template_id)
    if not t:
        return ApiResponse.failed("岗位模板不存在", body_code=404, http_code=404)
    return ApiResponse.success(_to_response(t))


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    payload: PositionTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """更新岗位模板"""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return ApiResponse.failed("没有任何更新字段", body_code=400)
    t = await PositionTemplateService.update(db, template_id, data)
    if not t:
        return ApiResponse.failed("岗位模板不存在", body_code=404, http_code=404)
    return ApiResponse.success(_to_response(t), message="更新成功")


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """删除岗位模板"""
    ok = await PositionTemplateService.delete(db, template_id)
    if not ok:
        return ApiResponse.failed("岗位模板不存在", body_code=404, http_code=404)
    return ApiResponse.success(message="删除成功")


@router.patch("/{template_id}/toggle")
async def toggle_template(
    template_id: int,
    payload: PositionTemplateToggle,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """启用/禁用岗位模板"""
    ok = await PositionTemplateService.toggle(db, template_id, payload.is_active)
    if not ok:
        return ApiResponse.failed("岗位模板不存在", body_code=404, http_code=404)
    return ApiResponse.success(message="状态已更新")
