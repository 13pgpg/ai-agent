"""
知识库相关 Celery 异步任务
"""
import asyncio
import logging
import httpx

from app.core.celery_app import celery_app
from app.services.backoffice.question_bank_service import QuestionBankService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, time_limit=600)
def ingest_document_task(self, doc_id: int, file_url: str, file_type: str):
    """
    异步文档摄入任务：下载文件 → 提取文本 → 切分 → 向量化 → 入库
    """
    async def _run():
        from app.db.base import get_session_local
        from app.services.backoffice.knowledge_service import KnowledgeService

        # 下载文件
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(file_url)
            resp.raise_for_status()
            file_bytes = resp.content

        async with get_session_local()() as db:
            await KnowledgeService.ingest_document(doc_id, file_bytes, file_type, db)

    try:
        asyncio.run(_run())
        return {"status": "success", "doc_id": doc_id}
    except Exception as exc:
        logger.error(f"文档 {doc_id} 摄入任务失败: {exc}")
        if self.request.retries < self.max_retries:
            self.retry(countdown=60 * (self.request.retries + 1), exc=exc)
        raise


@celery_app.task(bind=True, max_retries=3, time_limit=600)
def batch_embed_questions_task(self, question_ids: list[int]):
    """
    批量题目向量化任务（批量导入时触发）
    """
    try:
        result = QuestionBankService.batch_embed_sync(question_ids)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"批量向量化任务失败: {exc}")
        if self.request.retries < self.max_retries:
            self.retry(countdown=60 * (self.request.retries + 1), exc=exc)
        raise


@celery_app.task(time_limit=3600)
def reindex_all_questions_task():
    """全量重建题库 embedding（升级 Embedding 模型时使用）"""
    result = QuestionBankService.reindex_all_sync()
    logger.info(f"全量重建完成: {result}")
    return result
