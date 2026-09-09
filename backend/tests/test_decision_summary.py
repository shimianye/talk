import json

from app.services.decision_summary import build_decision_summary


def test_summary_exposes_only_allowlisted_decision_facts():
    state = {
        "trace_id": "trace-123",
        "intent": "order_query",
        "tool_results": [
            {
                "tool": "query_order",
                "success": True,
                "data": {"order_id": "SECRET-ORDER", "phone": "13812345678"},
                "arguments": {"user_id": "SECRET-USER"},
            }
        ],
        "guardrail_flags": ["pii_in_tool_result", "unknown_internal_flag"],
        "sources": [
            {"document_id": "policy-1", "title": "退换货政策", "version": "v2", "content": "SECRET-CONTENT"}
        ],
        "handoff_required": False,
    }
    summary = build_decision_summary(state)
    encoded = json.dumps(summary, ensure_ascii=False)
    assert summary["intent_label"] == "订单查询"
    assert summary["actions"] == [{"name": "query_order", "label": "查询本人订单", "success": True}]
    assert summary["sources"] == [{"document_id": "policy-1", "title": "退换货政策", "version": "v2"}]
    assert summary["safety"] == [{"code": "pii_in_tool_result", "label": "敏感信息已脱敏"}]
    assert "SECRET" not in encoded
    assert "13812345678" not in encoded


def test_summary_handles_empty_state_without_guessing():
    summary = build_decision_summary({})
    assert summary["intent"] == "unknown"
    assert summary["actions"] == []
    assert summary["sources"] == []
    assert summary["safety"] == []
