"""兼容初始化入口：升级结构并幂等同步业务种子与知识库。"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.rag.embedding import get_embedding_provider
from app.services.kb_sync import sync_knowledge_docs
from app.services.seed_sync import DEFAULT_DATA_DIR, sync_seed_data


def upgrade_schema() -> None:
    """使用当前应用数据库 URL 将结构升级到 Alembic head。"""
    previous_url = os.environ.get("ALEMBIC_DATABASE_URL")
    os.environ["ALEMBIC_DATABASE_URL"] = settings.database_url
    try:
        command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    finally:
        if previous_url is None:
            os.environ.pop("ALEMBIC_DATABASE_URL", None)
        else:
            os.environ["ALEMBIC_DATABASE_URL"] = previous_url


async def initialize(*, reset: bool = False) -> None:
    """在一个事务中同步受管数据；任一步失败则整批回滚。"""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            async with session.begin():
                seed_stats = await sync_seed_data(
                    session, DEFAULT_DATA_DIR, reset=reset
                )
                knowledge_stats = await sync_knowledge_docs(
                    session,
                    Path(settings.kb_docs_dir),
                    get_embedding_provider(),
                )
        print("[2/3] 业务种子同步:", seed_stats)
        print("[3/3] 知识库同步:", knowledge_stats)
    finally:
        await engine.dispose()


def main() -> None:
    """解析 reset 选项并运行迁移和幂等同步。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清空受管种子及其依赖后重灌；默认只做幂等更新",
    )
    args = parser.parse_args()
    upgrade_schema()
    print("[1/3] Alembic 数据结构迁移完成")
    asyncio.run(initialize(reset=args.reset))


if __name__ == "__main__":
    main()
