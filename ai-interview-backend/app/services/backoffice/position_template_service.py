import logging
from sqlalchemy import select, delete, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position_template import PositionTemplate

logger = logging.getLogger(__name__)


class PositionTemplateService:

    @staticmethod
    async def get_list(
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        category: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> dict:
        """分页查询岗位模板列表，支持分类、启用状态和关键词筛选。"""
        stmt = select(PositionTemplate)
        if category:
            stmt = stmt.where(PositionTemplate.category == category)
        if is_active is not None:
            stmt = stmt.where(PositionTemplate.is_active == is_active)
        if search:
            stmt = stmt.where(
                or_(
                    PositionTemplate.title.ilike(f"%{search}%"),
                    PositionTemplate.position_tag.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(
            PositionTemplate.sort_order.asc(),
            PositionTemplate.id.asc(),
        ).offset((page - 1) * size).limit(size)
        items = (await db.execute(stmt)).scalars().all()
        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def get_by_id(db: AsyncSession, template_id: int) -> PositionTemplate | None:
        """根据岗位模板主键查询单条记录。"""
        return await db.get(PositionTemplate, template_id)

    @staticmethod
    async def get_by_tag(db: AsyncSession, position_tag: str) -> PositionTemplate | None:
        """根据岗位标签查询岗位模板，Agent 和前后台都会用到。"""
        result = await db.execute(
            select(PositionTemplate).where(PositionTemplate.position_tag == position_tag)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_list(db: AsyncSession) -> list[PositionTemplate]:
        """供 Agent 工具使用：获取所有启用中的岗位模板"""
        result = await db.execute(
            select(PositionTemplate)
            .where(PositionTemplate.is_active == True)
            .order_by(PositionTemplate.sort_order.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> PositionTemplate:
        """创建岗位模板，并在写入前校验 position_tag 是否重复。"""
        existing = await PositionTemplateService.get_by_tag(db, data["position_tag"])
        if existing:
            raise ValueError(f"岗位标签 {data['position_tag']} 已存在")

        t = PositionTemplate(**data)
        db.add(t)
        await db.commit()
        await db.refresh(t)
        logger.info(f"岗位模板 {t.id} ({t.position_tag}) 已创建")
        return t

    @staticmethod
    async def update(db: AsyncSession, template_id: int, data: dict) -> PositionTemplate | None:
        """更新岗位模板的可变字段，返回更新后的记录。"""
        t = await db.get(PositionTemplate, template_id)
        if not t:
            return None
        for field, val in data.items():
            if hasattr(t, field):
                setattr(t, field, val)
        await db.commit()
        await db.refresh(t)
        return t

    @staticmethod
    async def delete(db: AsyncSession, template_id: int) -> bool:
        """删除岗位模板，成功则返回 True。"""
        result = await db.execute(
            delete(PositionTemplate).where(PositionTemplate.id == template_id)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def toggle(db: AsyncSession, template_id: int, is_active: bool) -> bool:
        """启用或禁用岗位模板，用于后台管理控制模板是否参与匹配。"""
        result = await db.execute(
            update(PositionTemplate)
            .where(PositionTemplate.id == template_id)
            .values(is_active=is_active)
        )
        await db.commit()
        return result.rowcount > 0
