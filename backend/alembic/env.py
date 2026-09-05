"""Alembic 异步迁移环境。

说明：pgvector 的 Vector 列在初始建表时由 scripts/init_db.py 的 create_all 处理；
后续如需 autogenerate 识别 vector 类型，可在本文件顶部补充：
    import pgvector.alembic  # noqa: F401
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401  注册全部模型到 Base.metadata
from app.config import settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """在无数据库连接模式下生成包含字面量参数的迁移 SQL。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """使用同步连接配置 Alembic 上下文并执行事务内迁移。"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """创建异步引擎，并桥接到 Alembic 所需的同步迁移函数。"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """从同步 Alembic 入口启动异步在线迁移流程。"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
