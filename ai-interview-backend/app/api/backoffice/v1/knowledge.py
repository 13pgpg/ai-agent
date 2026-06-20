"""
知识文档管理 API（管理端）
"""
import os
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional

from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.schemas.response import ApiResponse
from app.schemas.backoffice.knowledge import (
    KnowledgeDocumentToggle,
    KnowledgeTestRetrieve,
)
from app.services.backoffice.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("/app/uploads/knowledge")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "md", "markdown", "txt"}


def _doc_to_response(d: KnowledgeDocument) -> dict:
    return {
        "id": d.id,
        "title": d.title,
        "file_name": d.file_name,
        "file_url": d.file_url,
        "file_type": d.file_type,
        "file_size": d.file_size,
        "category": d.category,
        "tags": d.tags,
        "description": d.description,
        "chunk_count": d.chunk_count,
        "status": d.status,
        "error_message": d.error_message,
        "is_active": d.is_active,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


# ── 1. 上传文档 ────────────────────────────────────────────────────────

@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    上传文档。流程：
    1. 保存文件到 uploads/knowledge/
    2. 创建 knowledge_documents 记录（status=pending）
    3. 后台异步触发摄入流水线（pdf 解析 → 切分 → 向量化）
    """
    file_name = file.filename or "untitled"
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return ApiResponse.failed(
            f"不支持的文件类型 .{ext}（仅支持 PDF / MD / TXT）",
            body_code=400,
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)

    # 1. 创建 DB 记录
    doc = KnowledgeDocument(
        title=title or file_name.rsplit(".", 1)[0],
        file_name=file_name,
        file_type=ext,
        file_size=file_size,
        category=category,
        description=description,
        status="pending",
        uploaded_by=current_admin.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 2. 保存文件到磁盘
    save_path = UPLOAD_DIR / f"{doc.id}_{file_name}"
    save_path.write_bytes(file_bytes)
    file_url = str(save_path)

    await db.execute(
        update(KnowledgeDocument)
        .where(KnowledgeDocument.id == doc.id)
        .values(file_url=file_url)
    )
    await db.commit()

    # 3. 后台异步摄入
    background_tasks.add_task(
        KnowledgeService.ingest_from_path,
        doc.id, file_url, ext,
    )

    return ApiResponse.success(
        {"doc_id": doc.id, "status": "pending"},
        message="文档已上传，索引任务已启动",
    )


# ── 2. 列表 ────────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    result = await KnowledgeService.get_document_list(
        db=db, page=page, size=per_page,
        category=category, status=status, search=search,
    )
    return ApiResponse.success({
        "items": [_doc_to_response(d) for d in result["items"]],
        "total": result["total"],
        "page": page,
        "per_page": per_page,
    })


# ── 3. 检索测试（放在 {id} 之前，避免被路由匹配截胡）────────────────

@router.post("/test-retrieve")
async def test_retrieve_chunks(
    payload: KnowledgeTestRetrieve,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """测试文档检索效果"""
    chunks = await KnowledgeService.retrieve_chunks(
        query=payload.query,
        db=db,
        k=payload.k,
        category=payload.category,
        min_score=payload.min_score,
    )
    return ApiResponse.success({
        "query": payload.query,
        "count": len(chunks),
        "items": chunks,
    })


# ── 4. 详情 ────────────────────────────────────────────────────────────

@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        return ApiResponse.failed("文档不存在", body_code=404, http_code=404)
    return ApiResponse.success(_doc_to_response(doc))


# ── 5. 删除 ────────────────────────────────────────────────────────────

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        return ApiResponse.failed("文档不存在", body_code=404, http_code=404)

    # 删除磁盘文件（best-effort）
    if doc.file_url and os.path.exists(doc.file_url):
        try:
            os.remove(doc.file_url)
        except OSError as e:
            logger.warning(f"删除文件失败 {doc.file_url}: {e}")

    await KnowledgeService.delete_document(doc_id, db)
    return ApiResponse.success(message="文档已删除")


# ── 6. 启用/禁用 ───────────────────────────────────────────────────────

@router.patch("/documents/{doc_id}/toggle")
async def toggle_document(
    doc_id: int,
    payload: KnowledgeDocumentToggle,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    result = await db.execute(
        update(KnowledgeDocument)
        .where(KnowledgeDocument.id == doc_id)
        .values(is_active=payload.is_active)
    )
    await db.commit()
    if result.rowcount == 0:
        return ApiResponse.failed("文档不存在", body_code=404, http_code=404)
    return ApiResponse.success(message="状态已更新")


# ── 7. 重建索引 ────────────────────────────────────────────────────────

@router.post("/documents/{doc_id}/reindex")
async def reindex_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        return ApiResponse.failed("文档不存在", body_code=404, http_code=404)
    if not doc.file_url or not os.path.exists(doc.file_url):
        return ApiResponse.failed("源文件已丢失，无法重建", body_code=400)

    # 标记 pending 状态
    await db.execute(
        update(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        .values(status="pending", error_message=None)
    )
    await db.commit()

    # 异步重建（先删旧 chunk，再重新摄入）
    async def _reindex():
        from app.db.base import get_session_local
        async with get_session_local()() as session:
            with open(doc.file_url, "rb") as f:
                file_bytes = f.read()
            await KnowledgeService.reindex_document(doc_id, file_bytes, doc.file_type, session)

    background_tasks.add_task(_reindex)

    return ApiResponse.success(message="重建任务已启动")


# ── 8. 查看 chunks ─────────────────────────────────────────────────────

@router.get("/documents/{doc_id}/chunks")
async def list_document_chunks(
    doc_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """查看文档切分后的 chunks（调试用）"""
    stmt = (
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == doc_id)
        .order_by(KnowledgeChunk.chunk_index)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        {
            "id": c.id,
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "has_embedding": c.embedding is not None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]
    return ApiResponse.success({"items": items, "page": page, "per_page": per_page})
