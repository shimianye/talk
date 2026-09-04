"""工具注册表单元测试。"""
import asyncio

from app.core.tools import registry
from app.core.tools.base import Tool, ToolContext


def test_registry_has_14_tools():
    assert len(registry) == 14


def test_write_tool_requires_confirmation():
    tool = registry.get("create_after_sales_case")
    assert tool is not None
    assert tool.read_only is False
    assert tool.requires_confirmation is True
    assert tool.idempotent is True


def test_read_tool_flags():
    tool = registry.get("query_order")
    assert tool.read_only is True
    assert tool.permission == "consumer"


def test_role_filtering():
    # save_conversation_summary 仅 agent+ 可用
    assert registry.get("save_conversation_summary").permission == "agent"
    consumer_names = {t.name for t in registry.for_role("consumer")}
    assert "save_conversation_summary" not in consumer_names
    agent_names = {t.name for t in registry.for_role("agent")}
    assert "save_conversation_summary" in agent_names


def test_openai_schema_serializable():
    import json

    tools = registry.to_openai_tools("consumer")
    assert len(tools) == 13
    json.dumps(tools)  # 不应抛异常


def test_tool_context_defaults():
    ctx = ToolContext()
    assert ctx.role == "consumer"
    assert ctx.user_id is None


async def test_tool_timeout_interrupts():
    async def slow_handler(ctx, **params):
        await asyncio.sleep(0.5)
        return {"success": True}

    tool = Tool(
        name="slow_tool",
        description="慢工具",
        parameters={"type": "object", "properties": {}},
        permission="consumer",
        read_only=True,
        timeout=0.05,
        handler=slow_handler,
    )
    result = await tool.execute(ToolContext())
    assert result.success is False
    assert result.error_code == "TOOL_TIMEOUT"
