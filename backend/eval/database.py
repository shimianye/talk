"""评测数据库的隔离校验、会话工厂和运行基线恢复。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401  确保所有模型注册到 Base.metadata。
from app.config import settings
from app.db.base import Base
from app.services.database_bootstrap import validate_database_pair

# 评测前不清空的只读基线；其余 ORM 表默认作为运行期状态重置。
BASELINE_TABLES = frozenset({
    "products", "product_variants", "prices", "inventory", "promotions", "sources",
    "store_products", "knowledge_documents", "knowledge_chunks", "intent_taxonomy",
    "users", "roles", "user_roles", "evaluation_dataset", "sync_manifests",
})


def validated_eval_database_url() -> str:
    """验证评测 URL 与主库隔离，拒绝任何主库回退或非 `_eval` 目标。"""
    _, evaluation = validate_database_pair(settings.database_url, settings.eval_database_url)
    return evaluation.render_as_string(hide_password=False)


def create_eval_engine():
    """创建评测库专用异步引擎，生命周期由 runner 管理。"""
    return create_async_engine(validated_eval_database_url(), pool_pre_ping=True)


def create_eval_session_factory() -> async_sessionmaker[AsyncSession]:
    """为评测库创建专用 session factory，绝不复用 API 主库依赖。"""
    return async_sessionmaker(create_eval_engine(), expire_on_commit=False)


async def verify_eval_connection(session: AsyncSession) -> str:
    """二次确认连接的真实数据库名与 URL 配置一致。"""
    expected = make_url(validated_eval_database_url()).database
    actual = await session.scalar(text("SELECT current_database()"))
    if actual != expected:
        raise RuntimeError(f"评测数据库连接不匹配: expected={expected}, actual={actual}")
    return str(actual)


def resettable_table_names() -> tuple[str, ...]:
    """从 ORM metadata 推导运行期表，新增表默认随评测重置，避免遗漏。"""
    return tuple(
        table.name for table in Base.metadata.sorted_tables
        if table.name not in BASELINE_TABLES
    )


async def reset_eval_runtime_state(session: AsyncSession) -> tuple[str, ...]:
    """清空评测产生的会话、Trace 和业务写入，保留只读种子和知识基线。"""
    await verify_eval_connection(session)
    names = resettable_table_names()
    if names:
        identifiers = ", ".join(f'"{name}"' for name in names)
        await session.execute(text(f"TRUNCATE {identifiers} RESTART IDENTITY CASCADE"))
    return names
