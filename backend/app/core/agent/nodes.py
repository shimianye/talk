"""Agent 图节点实现。

节点对应设计文档第 5 章执行图：
load_session_context → input_guardrail → agent_decision → tool_execution →
validate_tool_result → agent_decision（循环）；特殊路由到 ask_clarification / human_handoff。
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from app.config import settings
from app.core.agent.state import AgentState
from app.core.llm.base import LLMUnavailableError
from app.core.llm.factory import get_llm_client
from app.core.security import guardrails
from app.core.tools import registry
from app.core.tools.base import ToolContext

logger = logging.getLogger(__name__)

# 澄清 / 转人工 由协作工具触发，映射到设计文档中的路由
_CLARIFY_TOOL = "request_user_confirmation"
_HANDOFF_TOOL = "transfer_to_human"

# 意图/实体/计划提取提示词（结构化输出）
_INTENT_PROMPT = (
    "你是手机电商客服的意图识别模块。请从用户输入中提取结构化信息，"
    '严格输出 JSON：{"intent": 意图英文名, "entities": 实体对象, "plan": 执行步骤数组}。\n'
    "意图候选：product_spec / product_compare / purchase_recommend / price_query / "
    "inventory_query / order_query / refund_policy / warranty_policy / shipping_policy / "
    "promotion_query / after_sales_apply / complaint / escalation / greeting / unknown。\n"
    "entities 可包含 product、order_id、budget、brand 等字段；无法确定时用空对象。"
)


def _assistant_tool_call_message(tool_calls: list[dict]) -> dict:
    """将内部工具调用转换成 OpenAI assistant tool_calls 消息。"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                },
            }
            for tc in tool_calls
        ],
    }


def _tool_result_message(tool_call_id: str, content: str) -> dict:
    """构造供 LLM 继续推理的 OpenAI tool 结果消息。"""
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def _last_user_text(state: AgentState) -> str:
    """从状态消息中倒序取得最近一条用户文本。"""
    for m in reversed(state.get("messages", [])):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


async def _extract_intent(state: AgentState) -> None:
    """结构化提取意图/实体/计划，写入 state（失败时降级为 unknown）。"""
    try:
        llm = get_llm_client()
        text = _last_user_text(state)
        parsed = await llm.complete_json(
            [
                {"role": "system", "content": _INTENT_PROMPT},
                {"role": "user", "content": text},
            ]
        )
        state["intent"] = parsed.get("intent") or "unknown"
        state["entities"] = parsed.get("entities") or {}
        state["plan"] = parsed.get("plan") or []
    except Exception:  # noqa: BLE001
        state.setdefault("intent", "unknown")
        state.setdefault("entities", {})
        state.setdefault("plan", [])


async def load_session_context(state: AgentState) -> AgentState:
    """初始化本轮 Trace、计数器和控制字段，并恢复已确认的工具调用。"""
    state["trace_id"] = state.get("trace_id") or uuid.uuid4().hex
    state.setdefault("steps", 0)
    state.setdefault("total_tool_calls", 0)
    state.setdefault("tool_results", [])
    state.setdefault("sources", [])
    state.setdefault("guardrail_flags", [])
    state.setdefault("pending_confirmation", False)
    state.setdefault("handoff_required", False)
    # 确认恢复：用户已确认待执行的写操作
    if state.get("confirmation_granted") and state.get("pending_tool_call"):
        state["tool_calls"] = [state["pending_tool_call"]]
    return state


async def input_guardrail(state: AgentState) -> AgentState:
    """检查最近输入中的提示词注入特征，命中时阻断后续模型调用。"""
    text = _last_user_text(state)
    flags = guardrails.check_input_injection(text)
    state["guardrail_flags"] = state.get("guardrail_flags", []) + flags
    if flags:
        state["guardrail_flags"].append("blocked")
        state["final_answer"] = "抱歉，检测到异常输入，无法处理该请求。"
    return state


async def agent_decision(state: AgentState) -> AgentState:
    """调用 LLM 决定直接回答还是使用工具，并执行步数与故障降级控制。"""
    # 输入已被拦截，直接走最终回答
    if "blocked" in state.get("guardrail_flags", []):
        return state

    state["steps"] = state.get("steps", 0) + 1

    # 意图/实体/计划提取（每轮首次，供 Trace 与评测使用）
    if state.get("intent") is None:
        await _extract_intent(state)

    # 执行限制：超步数 / 超工具数 → 降级转人工
    if (
        state["steps"] > settings.max_agent_steps
        or state.get("total_tool_calls", 0) >= settings.max_tool_calls
    ):
        state["final_answer"] = "抱歉，本次咨询步骤较多，已为您转接人工客服。"
        state["handoff_required"] = True
        state["guardrail_flags"] = state.get("guardrail_flags", []) + ["execution_limit"]
        return state

    llm = get_llm_client()
    tools = registry.to_openai_tools(state.get("role", "consumer"))
    try:
        resp = await llm.complete(state["messages"], tools=tools)
    except LLMUnavailableError:
        state["final_answer"] = "抱歉，智能服务暂时不可用，已为您转接人工客服。"
        state["handoff_required"] = True
        state["guardrail_flags"] = state.get("guardrail_flags", []) + ["llm_unavailable"]
        return state

    if resp.has_tool_calls:
        tcs = [
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
            for tc in resp.tool_calls
        ]
        state["messages"].append(_assistant_tool_call_message(tcs))
        state["tool_calls"] = tcs
        state["final_answer"] = None
    else:
        state["tool_calls"] = []
        state["final_answer"] = resp.content or "抱歉，我没有理解您的问题，请换一种说法。"
    return state


async def tool_execution(state: AgentState) -> AgentState:
    """按调用顺序执行已授权工具，处理确认、澄清和转人工分支。"""
    ctx = ToolContext(
        user_id=state.get("user_id"),
        role=state.get("role", "consumer"),
        session_id=state.get("session_id"),
        db=state.get("db"),
    )

    results: list[dict] = []
    for tc in state.get("tool_calls", []):
        tool = registry.get(tc["name"])
        if tool is None:
            results.append(
                {"tool": tc["name"], "success": False, "error": "未知工具", "error_code": "UNKNOWN_TOOL"}
            )
            continue

        # 协作工具：转人工
        if tc["name"] == _HANDOFF_TOOL:
            state["handoff_required"] = True
            state["final_answer"] = "已为您转接人工客服，请稍候。"
            return state

        # 协作工具：请求澄清
        if tc["name"] == _CLARIFY_TOOL:
            state["pending_confirmation"] = True
            state["pending_tool_call"] = None
            state["final_answer"] = tc["arguments"].get("question", "请补充一下信息？")
            return state

        # 写操作需用户确认：未确认则挂起，绝不执行（设计文档验收项）
        if tool.requires_confirmation and not state.get("confirmation_granted"):
            state["pending_confirmation"] = True
            state["pending_tool_call"] = tc
            prompt = tool.confirmation_message or f"执行「{tool.name}」"
            state["final_answer"] = f"即将{prompt}，是否确认？"
            return state

        result = await tool.execute(ctx, **tc["arguments"])
        results.append({"tool": tc["name"], **result.to_dict()})
        state["messages"].append(
            _tool_result_message(tc["id"], json.dumps(result.to_dict(), ensure_ascii=False))
        )
        state["total_tool_calls"] = state.get("total_tool_calls", 0) + 1

    state["tool_results"] = state.get("tool_results", []) + results
    state["tool_calls"] = []
    # 确认后执行完毕，复位挂起状态
    state["pending_confirmation"] = False
    state["pending_tool_call"] = None
    return state


async def validate_tool_result(state: AgentState) -> AgentState:
    """递归脱敏工具返回的数据，并记录工具结果中的 PII 风险。"""
    # 工具结果 PII/注入检查：递归脱敏 dict/list/str（设计文档安全链路）
    for r in state.get("tool_results", []):
        if r.get("success"):
            r["data"], hit = guardrails.redact_recursive(r.get("data"))
            if hit:
                state["guardrail_flags"] = list(state.get("guardrail_flags", [])) + [
                    "pii_in_tool_result"
                ]
    return state


async def ask_clarification(state: AgentState) -> AgentState:
    """保留工具节点生成的澄清问题并结束本轮执行。"""
    # final_answer 已由 tool_execution 设置为澄清问题
    return state


async def human_handoff(state: AgentState) -> AgentState:
    """标记会话需要人工接管，并确保存在面向用户的提示语。"""
    state["handoff_required"] = True
    if not state.get("final_answer"):
        state["final_answer"] = "已为您转接人工客服，请稍候。"
    return state


async def output_guardrail(state: AgentState) -> AgentState:
    """检查模型回答中的越权承诺，命中时改为人工确认。"""
    text = state.get("final_answer") or ""
    flags = guardrails.check_output_commitments(text)
    if flags:
        state["guardrail_flags"] = state.get("guardrail_flags", []) + flags
        state["final_answer"] = "抱歉，该事项需人工客服确认后处理，已为您转接。"
        state["handoff_required"] = True
    return state


async def save_trace(state: AgentState) -> AgentState:
    """将本轮意图、工具、安全标记和最终答案持久化为 Agent Trace。"""
    # 持久化 Agent Trace 与审计（db 未注入时静默跳过，便于离线单测）
    db = state.get("db")
    if db is None:
        return state
    from app.models import AgentTrace

    trace = AgentTrace(
        trace_id=state.get("trace_id", uuid.uuid4().hex),
        conversation_id=state.get("session_id"),
        session_id=state.get("session_id"),
        user_id=state.get("user_id"),
        role=state.get("role"),
        intent=state.get("intent"),
        entities=state.get("entities"),
        plan=state.get("plan"),
        tool_calls=state.get("tool_calls") or [],
        tool_results=state.get("tool_results") or [],
        sources=state.get("sources") or [],
        guardrail_flags=state.get("guardrail_flags") or [],
        handoff_required=state.get("handoff_required", False),
        final_answer=state.get("final_answer"),
        token_usage={"total_tool_calls": state.get("total_tool_calls", 0)},
    )
    db.add(trace)
    await db.flush()
    return state
