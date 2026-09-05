"""检查 Alembic head 与 SQLAlchemy ORM metadata 是否一致。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    """对显式指定的数据库执行 Alembic autogenerate 漂移检查。"""
    if not os.getenv("ALEMBIC_DATABASE_URL"):
        raise SystemExit("必须显式设置 ALEMBIC_DATABASE_URL，拒绝检查默认数据库")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.check(config)


if __name__ == "__main__":
    main()
