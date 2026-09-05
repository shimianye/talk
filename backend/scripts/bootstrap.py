"""Docker/CI 启动入口：创建、迁移并同步主库与独立评测库。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.core.rag.embedding import get_embedding_provider
from app.services.database_bootstrap import bootstrap_databases


def main() -> None:
    """解析显式 URL 覆盖并执行双库 bootstrap。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--eval-database-url", default=settings.eval_database_url)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--docs-dir", type=Path, default=Path(settings.kb_docs_dir))
    args = parser.parse_args()
    options = {}
    if args.data_dir is not None:
        options["data_dir"] = args.data_dir
    result = bootstrap_databases(
        args.database_url,
        args.eval_database_url,
        args.docs_dir,
        get_embedding_provider(),
        **options,
    )
    print("数据库 bootstrap 完成:", result)


if __name__ == "__main__":
    main()
