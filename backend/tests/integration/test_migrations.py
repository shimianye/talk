"""Alembic 初始迁移升级、回滚与漂移集成测试。"""
from __future__ import annotations

import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  注册完整 ORM metadata
from app.db.base import Base


def _migration_test_url() -> str:
    """取得显式测试库 URL，并拒绝对普通数据库执行回滚。"""
    url = os.getenv("ALEMBIC_DATABASE_URL")
    if not url:
        pytest.skip("未设置 ALEMBIC_DATABASE_URL，跳过破坏性迁移集成测试")
    database = make_url(url).database or ""
    if not database.endswith("_migration_test"):
        pytest.fail("迁移集成测试只允许使用名称以 _migration_test 结尾的数据库")
    return url


async def _inspect_database(url: str) -> tuple[int, bool, bool]:
    """返回应用表数、vector 扩展和 HNSW 索引是否存在。"""
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            table_count = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name <> 'alembic_version'"
                )
            )
            has_vector = bool(
                await connection.scalar(
                    text("SELECT count(*) FROM pg_extension WHERE extname='vector'")
                )
            )
            has_hnsw = bool(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_indexes "
                        "WHERE indexname='ix_knowledge_chunks_embedding_hnsw'"
                    )
                )
            )
            return int(table_count or 0), has_vector, has_hnsw
    finally:
        await engine.dispose()


def test_migration_upgrade_downgrade_and_drift() -> None:
    """验证真实初始迁移三连，并确保 ORM metadata 无漂移。"""
    url = _migration_test_url()
    assert len(Base.metadata.tables) == 24

    config = Config("alembic.ini")
    command.upgrade(config, "head")
    assert asyncio.run(_inspect_database(url)) == (24, True, True)

    command.downgrade(config, "base")
    assert asyncio.run(_inspect_database(url)) == (0, True, False)

    command.upgrade(config, "head")
    assert asyncio.run(_inspect_database(url)) == (24, True, True)
    command.check(config)
