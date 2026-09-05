"""评测 JSON/Markdown 报告一致性测试。"""
import json

from eval.reporting import persist_report


def test_persist_report_writes_matching_json_and_markdown(tmp_path):
    result = {
        "total": 2, "succeeded": 1, "failed": 1,
        "environment": {"git_commit": "abc", "database_name": "demo_eval"},
        "metrics": {"意图准确率": 0.5},
        "owner_isolation": {"owner通过数": 1, "non_owner拦截数": 1},
        "execution": {"one_round_samples": 1, "two_round_samples": 0},
        "category_distribution": {"商品参数": 2},
        "errors": [{"id": 2, "error_type": "RuntimeError", "error_message": "failed"}],
        "detail": [],
    }
    json_path, md_path = persist_report(result, tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8")) == result
    markdown = md_path.read_text(encoding="utf-8")
    assert "样本总数：2" in markdown
    assert "non_owner拦截数" in markdown
    assert "RuntimeError - failed" in markdown
    assert "one_round_samples" in markdown
    assert "商品参数" in markdown
