"""Deterministic intent routing and handoff policy for the retail agent."""
from __future__ import annotations

from typing import Iterable

INTENT_TOOL_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "product_spec": ("query_product_spec", "search_knowledge_base"),
    "product_compare": ("compare_products", "search_knowledge_base"),
    "purchase_recommend": ("recommend_products", "query_inventory"),
    "price_query": ("query_price", "search_knowledge_base"),
    "inventory_query": ("query_inventory",),
    "order_query": ("query_order", "query_logistics"),
    "shipping_policy": ("query_logistics", "search_knowledge_base"),
    "after_sales_apply": ("check_after_sales_eligibility", "create_after_sales_case"),
    "refund_policy": ("search_knowledge_base", "check_after_sales_eligibility"),
    "warranty_policy": ("search_knowledge_base",),
    "promotion_query": ("search_knowledge_base", "query_price"),
    "complaint": ("transfer_to_human", "save_conversation_summary"),
    "escalation": ("transfer_to_human", "save_conversation_summary"),
}

_HANDOFF_TERMS = ("人工", "投诉", "举报", "律师", "赔偿", "退款争议", "转人工")


def candidate_tools_for_intent(intent: str | None, available: Iterable[str]) -> list[str]:
    """Return an ordered, intent-scoped tool list while preserving safety tools."""
    available_set = set(available)
    candidates = INTENT_TOOL_ALLOWLIST.get(intent or "", ())
    selected = [name for name in candidates if name in available_set]
    # Knowledge search and handoff remain safe fallbacks for unknown intents.
    if not selected:
        selected = [name for name in ("search_knowledge_base", "transfer_to_human") if name in available_set]
    return selected


def should_handoff(*, text: str, intent: str | None = None, tool_failures: int = 0,
                   intent_confidence: float | None = None) -> bool:
    """Apply explicit escalation rules before relying on an LLM's judgement."""
    lowered = text.lower()
    return (
        any(term in lowered for term in _HANDOFF_TERMS)
        or intent in {"complaint", "escalation"}
        or tool_failures >= 2
        or (intent_confidence is not None and intent_confidence < 0.55)
    )
