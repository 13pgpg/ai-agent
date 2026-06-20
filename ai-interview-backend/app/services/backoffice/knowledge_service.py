import io
import logging
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.services.common.embedding import embed_texts, embed_text

logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", ".", " "],
)


def _extract_text(file_bytes: bytes, file_type: str) -> str:
    """从文件字节中提取纯文本"""
    file_type = file_type.lower().lstrip(".")

    if file_type == "pdf":
        import pdfplumber
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    # txt / md / markdown
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


class KnowledgeService:

    @staticmethod
    async def ingest_document(
        doc_id: int,
        file_bytes: bytes,
        file_type: str,
        db: AsyncSession,
    ) -> int:
        """摄入文档：提取文本 → 切分 → 批量向量化 → 写入 knowledge_chunks"""
        await db.execute(
            update(KnowledgeDocument)
            .where(KnowledgeDocument.id == doc_id)
            .values(status="indexing")
        )
        await db.commit()

        try:
            raw_text = _extract_text(file_bytes, file_type)
            if not raw_text.strip():
                raise ValueError("文档提取不到文本内容")

            chunks = _splitter.split_text(raw_text)
            if not chunks:
                raise ValueError("文档切分后为空")

            embeddings = await embed_texts(chunks)

            chunk_records = [
                KnowledgeChunk(
                    document_id=doc_id,
                    chunk_index=i,
                    content=chunk,
                    embedding=emb,
                )
                for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
            ]
            db.add_all(chunk_records)

            await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.id == doc_id)
                .values(status="indexed", chunk_count=len(chunks))
            )
            await db.commit()
            logger.info(f"文档 {doc_id} 索引完成，共 {len(chunks)} 个 chunk")
            return len(chunks)

        except Exception as e:
            await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.id == doc_id)
                .values(status="failed", error_message=str(e))
            )
            await db.commit()
            logger.error(f"文档 {doc_id} 索引失败: {e}")
            raise

    @staticmethod
    async def ingest_from_path(doc_id: int, file_path: str, file_type: str) -> int:
        """
        从本地磁盘路径摄入。用于 BackgroundTasks（自带独立 DB 会话）。
        """
        from app.db.base import get_session_local

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        async with get_session_local()() as db:
            return await KnowledgeService.ingest_document(doc_id, file_bytes, file_type, db)

    @staticmethod
    async def delete_document(doc_id: int, db: AsyncSession) -> None:
        """删除文档及其所有 chunk（CASCADE 已在外键上配置）"""
        await db.execute(
            delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        )
        await db.commit()

    @staticmethod
    async def reindex_document(
        doc_id: int,
        file_bytes: bytes,
        file_type: str,
        db: AsyncSession,
    ) -> int:
        """删除旧 chunk，重新索引"""
        await db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id)
        )
        await db.commit()
        return await KnowledgeService.ingest_document(doc_id, file_bytes, file_type, db)

    @staticmethod
    async def retrieve_chunks(
        query: str,
        db: AsyncSession,
        k: int = 4,
        category: str | None = None,
        min_score: float = 0.3,
    ) -> list[dict]:
        """
        语义检索文档 chunk。
        返回列表：[{id, document_id, content, similarity}, ...]
        """
        query_vec = await embed_text(query)
        distance_threshold = 1.0 - min_score  # cosine_distance = 1 - cosine_similarity

        stmt = (
            select(
                KnowledgeChunk.id,
                KnowledgeChunk.document_id,
                KnowledgeChunk.content,
                KnowledgeChunk.embedding.cosine_distance(query_vec).label("distance"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeChunk.embedding.is_not(None),
                KnowledgeDocument.is_active == True,
                KnowledgeChunk.embedding.cosine_distance(query_vec) <= distance_threshold,
            )
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vec))
            .limit(k)
        )

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)

        result = await db.execute(stmt)
        rows = result.mappings().all()
        return [
            {
                "id": row["id"],
                "document_id": row["document_id"],
                "content": row["content"],
                "similarity": round(1.0 - float(row["distance"]), 4),
            }
            for row in rows
        ]

    @staticmethod
    async def get_document_list(
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        category: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> dict:
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id > 0)
        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)
        if status:
            stmt = stmt.where(KnowledgeDocument.status == status)
        if search:
            stmt = stmt.where(KnowledgeDocument.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(KnowledgeDocument.created_at.desc()).offset((page - 1) * size).limit(size)
        items = (await db.execute(stmt)).scalars().all()
        return {"items": items, "total": total, "page": page, "size": size}
