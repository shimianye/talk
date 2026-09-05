"""评测数据库防误连与基线白名单测试。"""
import pytest

from app.config import settings
from eval.database import BASELINE_TABLES, resettable_table_names, validated_eval_database_url


def test_eval_database_url_rejects_main_database(monkeypatch):
    """评测 URL 指向主库时必须拒绝，不能静默复用 API 数据库。"""
    monkeypatch.setattr(settings, "database_url", "postgresql+asyncpg://pca:x@db/main")
    monkeypatch.setattr(settings, "eval_database_url", "postgresql+asyncpg://pca:x@db/main")
    with pytest.raises(ValueError, match="不得与主库同名"):
        validated_eval_database_url()


def test_runtime_reset_is_metadata_driven_and_preserves_baseline():
    """运行期表由 metadata 自动发现，只读基线不会被直接 truncate。"""
    resettable = set(resettable_table_names())
    assert not resettable & BASELINE_TABLES
    assert {"orders", "after_sales_cases", "agent_traces", "conversations"} <= resettable
    assert {"products", "evaluation_dataset", "sync_manifests"} <= BASELINE_TABLES
