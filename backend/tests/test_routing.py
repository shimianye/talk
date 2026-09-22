from app.core.agent.routing import candidate_tools_for_intent, should_handoff


def test_candidates_are_scoped_by_intent():
    assert candidate_tools_for_intent("price_query", ["query_price", "query_order"]) == ["query_price"]
    assert "search_knowledge_base" in candidate_tools_for_intent("unknown", ["search_knowledge_base"])


def test_handoff_policy_covers_explicit_and_repeated_failures():
    assert should_handoff(text="我要求转人工")
    assert should_handoff(text="查一下", tool_failures=2)
    assert not should_handoff(text="查询价格", intent="price_query", intent_confidence=0.9)
