import logging
from langchain_community.embeddings import DashScopeEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

_embeddings: DashScopeEmbeddings | None = None

BATCH_SIZE = 25  # DashScope 单次最多 25 条


def get_embeddings() -> DashScopeEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = DashScopeEmbeddings(
            model=settings.KNOWLEDGE_EMBEDDING_MODEL,
            dashscope_api_key=settings.DASHSCOPE_API_KEY,
        )
    return _embeddings


async def embed_text(text: str) -> list[float]:
    """单文本异步向量化"""
    try:
        return await get_embeddings().aembed_query(text)
    except Exception as e:
        logger.error(f"Embedding 失败: {e}")
        raise


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量异步向量化（自动分批，每批最多 25 条）"""
    if not texts:
        return []
    results: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        try:
            vecs = await get_embeddings().aembed_documents(batch)
            results.extend(vecs)
        except Exception as e:
            logger.error(f"批量 Embedding 第 {i // BATCH_SIZE + 1} 批失败: {e}")
            raise
    return results


def embed_text_sync(text: str) -> list[float]:
    """同步向量化（用于 Celery 任务）"""
    try:
        return get_embeddings().embed_query(text)
    except Exception as e:
        logger.error(f"同步 Embedding 失败: {e}")
        raise


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """批量同步向量化（用于 Celery 任务）"""
    if not texts:
        return []
    results: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        try:
            vecs = get_embeddings().embed_documents(batch)
            results.extend(vecs)
        except Exception as e:
            logger.error(f"批量同步 Embedding 第 {i // BATCH_SIZE + 1} 批失败: {e}")
            raise
    return results
