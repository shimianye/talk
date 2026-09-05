"""双数据库 bootstrap 的 URL 隔离规则单元测试。"""
import pytest

from app.services.database_bootstrap import validate_database_pair

MAIN_URL = "postgresql+asyncpg://pca:secret@postgres:5432/phone_commerce"
EVAL_URL = "postgresql+asyncpg://pca:secret@postgres:5432/phone_commerce_eval"


def test_validate_database_pair_accepts_same_instance_separate_database():
    """同实例、同账号、不同且带后缀的评测库应通过。"""
    main, evaluation = validate_database_pair(MAIN_URL, EVAL_URL)
    assert main.database == "phone_commerce"
    assert evaluation.database == "phone_commerce_eval"


@pytest.mark.parametrize(
    ("eval_url", "message"),
    [
        (MAIN_URL, "不得与主库同名"),
        ("postgresql+asyncpg://pca:secret@other:5432/phone_commerce_eval", "同一 PostgreSQL 实例"),
        ("postgresql+asyncpg://other:secret@postgres:5432/phone_commerce_eval", "使用同一账号"),
        ("postgresql+asyncpg://pca:secret@postgres:5432/evaluation", "必须以 _eval 结尾"),
        ("sqlite+aiosqlite:///evaluation_eval", "仅支持 PostgreSQL"),
    ],
)
def test_validate_database_pair_rejects_unsafe_targets(eval_url: str, message: str):
    """主库复用、跨实例、跨账号、错误命名和非 PG URL 都必须拒绝。"""
    with pytest.raises(ValueError, match=message):
        validate_database_pair(MAIN_URL, eval_url)


def test_validate_database_pair_requires_both_urls():
    """缺失评测 URL 时不得静默回落到主库。"""
    with pytest.raises(ValueError, match="均必须显式配置"):
        validate_database_pair(MAIN_URL, "")
