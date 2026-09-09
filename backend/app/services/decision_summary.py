"""Build a public, allowlisted summary of one Agent turn."""
from __future__ import annotations

from typing import Any

from app.config import settings


_INTENT_LABELS = {
    "product_spec": "商品参数咨询",
    "product_compare": "商品对比",
    "purchase_recommend": "购买推荐",
    "price_query": "价格查询",
    "inventory_query": "库存查询",
    "order_query": "订单查询",
    "refund_policy": "退货退款政策",
    "warranty_policy": "保修政策",
    "shipping_policy": "配送政策",
    "promotion_query": "促销查询",
    "after_sales_apply": "售后申请",
    "complaint": "投诉处理",
    "escalation": "人工升级",
    "greeting": "普通问候",
    "unknown": "暂未明确",
}

_ACTION_LABELS = {
    "query_product_spec": "查询商品参数",
    "compare_products": "对比商品",
    "recommend_products": "生成购买推荐",
    "query_price": "查询实时价格",
    "query_inventory": "查询库存",
    "query_order": "查询本人订单",
    "query_logistics": "查询物流",
    "check_after_sales_eligibility": "检查售后资格",
    "create_after_sales_case": "创建售后工单",
    "get_after_sales_case": "查询售后工单",
    "search_knowledge_base": "检索知识库",
    "transfer_to_human": "转接人工客服",
    "request_user_confirmation": "请求用户确认",
    "save_conversation_summary": "保存会话摘要",
}

_SAFETY_LABELS = {
    "injection_attempt": "检测到提示词注入",
    "blocked": "异常请求已拦截",
    "pii_in_tool_result": "敏感信息已脱敏",
    "sensitive_commitment": "高风险承诺已转人工",
    "execution_limit": "执行次数达到安全上限",
    "llm_unavailable": "模型不可用，已降级转人工",
}


def _public_sources(state: dict[str, Any]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in state.get("sources", []) or []:
        if not isinstance(source, dict):
            continue
        document_id = str(source.get("document_id") or "")[:80]
        title = str(source.get("title") or "")[:120]
        if not document_id or not title or document_id in seen:
            continue
        seen.add(document_id)
        public = {"document_id": document_id, "title": title}
        if source.get("version") is not None:
            public["version"] = str(source["version"])[:40]
        sources.append(public)
    return sources[:5]


def build_decision_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Return facts safe for consumers; never expose prompts, arguments or result data."""
    actions: list[dict[str, Any]] = []
    seen_actions: set[str] = set()
    for result in state.get("tool_results", []) or []:
        if not isinstance(result, dict):
            continue
        name = str(result.get("tool") or "")
        if name not in _ACTION_LABELS or name in seen_actions:
            continue
        seen_actions.add(name)
        actions.append(
            {
                "name": name,
                "label": _ACTION_LABELS[name],
                "success": bool(result.get("success")),
            }
        )

    flags = [
        {"code": flag, "label": _SAFETY_LABELS[flag]}
        for flag in dict.fromkeys(state.get("guardrail_flags", []) or [])
        if flag in _SAFETY_LABELS
    ]
    intent = str(state.get("intent") or "unknown")
    return {
        "trace_id": str(state.get("trace_id") or "")[:64],
        "intent": intent,
        "intent_label": _INTENT_LABELS.get(intent, "其他咨询"),
        "actions": actions,
        "sources": _public_sources(state),
        "safety": flags,
        "handoff_required": bool(state.get("handoff_required")),
        "mode": settings.llm_provider,
    }
