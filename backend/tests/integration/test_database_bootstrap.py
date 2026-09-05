"""主库与独立评测库 bootstrap 的 PostgreSQL 集成测试。"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.rag.embedding import MockEmbeddingProvider
from app.services.database_bootstrap import bootstrap_databases

BACKEND_DIR = Path(__file__).resolve().parents[2]
KB_DIR = BACKEND_DIR.parent / "data" / "kb-docs"


def _bootstrap_test_urls() -> tuple[str, str]:
    """读取显式测试 URL，并锁定两个可安全删除的临时库名。"""
    raw_url = os.getenv("BOOTSTRAP_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("未设置 BOOTSTRAP_TEST_DATABASE_URL，跳过双库 bootstrap 集成测试")
    main = make_url(raw_url)
    if main.get_backend_name() != "postgresql":
        pytest.fail("双库 bootstrap 集成测试只支持 PostgreSQL")
    if main.database != "phone_commerce_bootstrap_test":
        pytest.fail("测试主库必须命名为 phone_commerce_bootstrap_test")
    evaluation = main.set(database="phone_commerce_bootstrap_test_eval")
    return main.render_as_string(hide_password=False), evaluation.render_as_string(
        hide_password=False
    )


async def _recreate_main_and_drop_eval(main_url: str, eval_url: str) -> None:
    """通过 maintenance database 重建测试主库并删除旧评测库。"""
    main = make_url(main_url)
    evaluation = make_url(eval_url)
    maintenance_url = main.set(database="postgres")
    engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            for database in (evaluation.database, main.database):
                await connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :database AND pid <> pg_backend_pid()"
                    ),
                    {"database": database},
                )
                await connection.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
            await connection.execute(text(f'CREATE DATABASE "{main.database}"'))
    finally:
        await engine.dispose()


async def _drop_test_databases(main_url: str, eval_url: str) -> None:
    """终止残留连接并删除两个固定命名的 bootstrap 测试库。"""
    main = make_url(main_url)
    evaluation = make_url(eval_url)
    engine = create_async_engine(
        main.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        async with engine.connect() as connection:
            for database in (evaluation.database, main.database):
                await connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :database AND pid <> pg_backend_pid()"
                    ),
                    {"database": database},
                )
                await connection.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
    finally:
        await engine.dispose()


async def _database_snapshot(database_url: str) -> dict[str, int | str]:
    """读取迁移版本及双库必须一致的核心数据计数。"""
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result: dict[str, int | str] = {
                "revision": str(
                    await connection.scalar(text("SELECT version_num FROM alembic_version"))
                )
            }
            for table in (
                "products",
                "product_variants",
                "evaluation_dataset",
                "knowledge_documents",
                "knowledge_chunks",
            ):
                result[table] = int(
                    await connection.scalar(text(f'SELECT count(*) FROM "{table}"')) or 0
                )
            return result
    finally:
        await engine.dispose()


def test_bootstrap_creates_migrates_and_reuses_isolated_eval_database() -> None:
    """验证首次双库初始化与第二次幂等快速路径的完整闭环。"""
    main_url, eval_url = _bootstrap_test_urls()
    asyncio.run(_recreate_main_and_drop_eval(main_url, eval_url))
    try:
        first = bootstrap_databases(
            main_url, eval_url, KB_DIR, MockEmbeddingProvider()
        )
        assert first["eval_database_created"] is True
        assert first["main"]["seed"]["skipped"] is False
        assert first["eval"]["seed"]["skipped"] is False

        main_snapshot = asyncio.run(_database_snapshot(main_url))
        eval_snapshot = asyncio.run(_database_snapshot(eval_url))
        assert main_snapshot == eval_snapshot
        assert main_snapshot == {
            "revision": "8fcb26067dd1",
            "products": 9,
            "product_variants": 31,
            "evaluation_dataset": 100,
            "knowledge_documents": 20,
            "knowledge_chunks": 87,
        }

        second = bootstrap_databases(
            main_url, eval_url, KB_DIR, MockEmbeddingProvider()
        )
        assert second["eval_database_created"] is False
        for database in ("main", "eval"):
            assert second[database]["seed"]["skipped"] is True
            assert second[database]["knowledge"] == {
                "documents": 0,
                "chunks": 0,
                "skipped": 20,
                "deleted": 0,
            }
    finally:
        asyncio.run(_drop_test_databases(main_url, eval_url))
