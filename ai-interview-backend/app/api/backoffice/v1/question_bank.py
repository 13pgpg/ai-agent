"""
题库管理 API（管理端）
"""
import logging
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Literal

from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.schemas.response import ApiResponse
from app.schemas.backoffice.question_bank import (
    QuestionBankCreate,
    QuestionBankUpdate,
    QuestionBankToggle,
    QuestionBankBatchImport,
    QuestionBankTestRetrieve,
    QuestionBankResponse,
    QuestionBankRetrievedItem,
)
from app.services.backoffice.question_bank_service import QuestionBankService

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(q) -> dict:
    """ORM 对象 → 响应字典（含 has_embedding 标志）"""
    return {
        "id": q.id,
        "category": q.category,
        "position_tag": q.position_tag,
        "difficulty": q.difficulty,
        "question": q.question,
        "reference_answer": q.reference_answer,
        "key_points": q.key_points,
        "tags": q.tags,
        "source": q.source,
        "use_count": q.use_count,
        "is_active": q.is_active,
        "has_embedding": q.embedding is not None,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }


# ── 1. 列表 ────────────────────────────────────────────────────────────

@router.get("")
async def list_questions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    position_tag: Optional[str] = Query(None),
    difficulty: Optional[Literal["easy", "medium", "hard"]] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="题面/参考答案关键字"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """题库列表（分页 + 筛选）"""
    result = await QuestionBankService.get_list(
        db=db, page=page, size=per_page,
        category=category, position_tag=position_tag,
        difficulty=difficulty, is_active=is_active, search=search,
    )
    return ApiResponse.success({
        "items": [_to_response(q) for q in result["items"]],
        "total": result["total"],
        "page": page,
        "per_page": per_page,
    })


# ── 2. 创建 ────────────────────────────────────────────────────────────

@router.post("")
async def create_question(
    payload: QuestionBankCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """新增题目（保存后自动向量化）"""
    data = payload.model_dump()
    data["created_by"] = current_admin.id
    q = await QuestionBankService.create(db, data)
    return ApiResponse.success(_to_response(q), message="创建成功")


# ── 3. 详情 ────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_question_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """题库统计（总数、按分类/难度分布、热门题）"""
    stats = await QuestionBankService.get_stats(db)
    return ApiResponse.success(stats)


@router.get("/{question_id}")
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    q = await QuestionBankService.get_by_id(db, question_id)
    if not q:
        return ApiResponse.failed("题目不存在", body_code=404, http_code=404)
    return ApiResponse.success(_to_response(q))


# ── 4. 更新 ────────────────────────────────────────────────────────────

@router.put("/{question_id}")
async def update_question(
    question_id: int,
    payload: QuestionBankUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """更新题目（若改了 question/reference_answer 则自动重新向量化）"""
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return ApiResponse.failed("没有任何更新字段", body_code=400)
    q = await QuestionBankService.update(db, question_id, data)
    if not q:
        return ApiResponse.failed("题目不存在", body_code=404, http_code=404)
    return ApiResponse.success(_to_response(q), message="更新成功")


# ── 5. 删除 ────────────────────────────────────────────────────────────

@router.delete("/{question_id}")
async def delete_question(
    question_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    ok = await QuestionBankService.delete(db, question_id)
    if not ok:
        return ApiResponse.failed("题目不存在", body_code=404, http_code=404)
    return ApiResponse.success(message="删除成功")


# ── 6. 启用/禁用 ───────────────────────────────────────────────────────

@router.patch("/{question_id}/toggle")
async def toggle_question(
    question_id: int,
    payload: QuestionBankToggle,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    ok = await QuestionBankService.toggle(db, question_id, payload.is_active)
    if not ok:
        return ApiResponse.failed("题目不存在", body_code=404, http_code=404)
    return ApiResponse.success(message="状态已更新")


# ── 7. 批量导入 ────────────────────────────────────────────────────────

@router.post("/batch-import")
async def batch_import_questions(
    payload: QuestionBankBatchImport,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    批量导入题目。先全部入库（embedding=NULL），再后台异步向量化。
    """
    from app.models.question_bank import QuestionBank

    inserted_ids = []
    for item in payload.items:
        q = QuestionBank(
            **item.model_dump(),
            created_by=current_admin.id,
        )
        db.add(q)
        await db.flush()
        inserted_ids.append(q.id)
    await db.commit()

    # 后台批量向量化（走 Celery，避免阻塞请求）
    from app.schedule.jobs.knowledge_tasks import batch_embed_questions_task
    batch_embed_questions_task.delay(inserted_ids)

    return ApiResponse.success(
        {"inserted_count": len(inserted_ids), "ids": inserted_ids},
        message=f"已导入 {len(inserted_ids)} 题，向量化任务已提交",
    )


# ── 8. 全量重建 ────────────────────────────────────────────────────────

@router.post("/reindex-all")
async def reindex_all_questions(
    current_admin: Admin = Depends(get_current_admin),
):
    """异步全量重建题库 embedding（升级模型时用）"""
    from app.schedule.jobs.knowledge_tasks import reindex_all_questions_task
    task = reindex_all_questions_task.delay()
    return ApiResponse.success(
        {"task_id": task.id},
        message="全量重建任务已提交，请稍后查看",
    )


# ── 9. 检索测试 ────────────────────────────────────────────────────────

@router.post("/test-retrieve")
async def test_retrieve_questions(
    payload: QuestionBankTestRetrieve,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """测试题库召回效果（输入岗位/技能，看返回的 Top N 题）"""
    items = await QuestionBankService.retrieve_questions(
        query=payload.query,
        db=db,
        k=payload.k,
        position_tag=payload.position_tag,
        difficulty=payload.difficulty,
        min_score=payload.min_score,
    )
    return ApiResponse.success({
        "query": payload.query,
        "count": len(items),
        "items": items,
    })
