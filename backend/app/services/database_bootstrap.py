"""主库与独立评测库的创建、迁移和内容同步编排。"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.rag.embedding import EmbeddingProvider
from app.services.kb_sync import sync_knowledge_docs
from app.services.seed_sync import DEFAULT_DATA_DIR, sync_seed_data

BACKEND_DIR = Path(__file__).resolve().parents[2]
_DATABASE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_database_pair(main_url: str, eval_url: str) -> tuple[URL, URL]:
    """校验两个 URL 为同实例不同库，且评测库使用明确的 `_eval` 后缀。"""
    if not main_url or not eval_url:
        raise ValueError("DATABASE_URL 和 EVAL_DATABASE_URL 均必须显式配置")
    main = make_url(main_url)
    evaluation = make_url(eval_url)
    if main.get_backend_name() != "postgresql" or evaluation.get_backend_name() != "postgresql":
        raise ValueError("bootstrap 仅支持 PostgreSQL 数据库")
    main_endpoint = (main.host, main.port or 5432, main.username)
    eval_endpoint = (evaluation.host, evaluation.port or 5432, evaluation.username)
    if main_endpoint != eval_endpoint:
        raise ValueError("主库与评测库必须位于同一 PostgreSQL 实例并使用同一账号")
    if not main.database or not evaluation.database:
        raise ValueError("数据库 URL 必须包含 database 名")
    if main.database == evaluation.database:
        raise ValueError("评测库不得与主库同名")
    if not evaluation.database.endswith("_eval"):
        raise ValueError("评测库名称必须以 _eval 结尾")
    if not _DATABASE_NAME_RE.fullmatch(evaluation.database):
        raise ValueError("评测库名称只能包含字母、数字和下划线")
    return main, evaluation


async def ensure_database_exists(main_url: str, eval_url: str) -> bool:
    """连接 maintenance database，以 AUTOCOMMIT 创建缺失的评测库。"""
    _, evaluation = validate_database_pair(main_url, eval_url)
    maintenance_url = evaluation.set(database="postgres")
    engine = create_async_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            exists = bool(
                await connection.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": evaluation.database},
                )
            )
            if exists:
                return False
            # 数据库名已通过严格白名单校验；CREATE DATABASE 不支持绑定标识符。
            await connection.execute(text(f'CREATE DATABASE "{evaluation.database}"'))
            return True
    finally:
        await engine.dispose()


def migrate_database(database_url: str) -> None:
    """通过环境覆盖让同一 Alembic 配置升级指定数据库。"""
    previous_url = os.environ.get("ALEMBIC_DATABASE_URL")
    os.environ["ALEMBIC_DATABASE_URL"] = database_url
    try:
        command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    finally:
        if previous_url is None:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)
        else:
            os.environ["ALEMBIC_DATABASE_URL"] = previous_url


async def sync_database(
    database_url: str,
    docs_dir: Path,
    embedding: EmbeddingProvider,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, Any]:
    """在指定数据库的单一事务内同步业务种子和知识库。"""
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session, session.begin():
            seed_stats = await sync_seed_data(session, data_dir)
            knowledge_stats = await sync_knowledge_docs(
                session, docs_dir, embedding
            )
        return {"seed": seed_stats, "knowledge": knowledge_stats}
    finally:
        await engine.dispose()


async def _bootstrap_database_contents(
    main_url: str,
    eval_url: str,
    docs_dir: Path,
    embedding: EmbeddingProvider,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, Any]:
    """在同一事件循环中创建、迁移并同步主库与评测库。"""
    created = await ensure_database_exists(main_url, eval_url)
    # Alembic 的异步 env 从同步入口内部调用 asyncio.run；放入工作线程，
    # 避免与 bootstrap 主事件循环嵌套，同时保持两次迁移顺序执行。
    await asyncio.to_thread(migrate_database, main_url)
    await asyncio.to_thread(migrate_database, eval_url)
    main_stats = await sync_database(main_url, docs_dir, embedding, data_dir=data_dir)
    eval_stats = await sync_database(eval_url, docs_dir, embedding, data_dir=data_dir)
    return {"eval_database_created": created, "main": main_stats, "eval": eval_stats}


def bootstrap_databases(
    main_url: str,
    eval_url: str,
    docs_dir: Path,
    embedding: EmbeddingProvider,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> dict[str, Any]:
    """创建评测库，迁移双库，并分别执行幂等内容同步。"""
    validate_database_pair(main_url, eval_url)
    return asyncio.run(
        _bootstrap_database_contents(
            main_url,
            eval_url,
            docs_dir,
            embedding,
            data_dir=data_dir,
        )
    )
