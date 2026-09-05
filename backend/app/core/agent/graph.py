"""LangGraph 状态图组装与入口。"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.core.agent import nodes
from app.core.agent.state import AgentState


def route_after_load(state: AgentState) -> str:
    """决定加载上下文后是恢复待确认工具，还是进入输入安全检查。"""
    # 确认恢复：直接进入工具执行，跳过 LLM 重新决策
    if state.get("confirmation_granted") and state.get("pending_tool_call"):
        return "tool_execution"
    return "input_guardrail"


def route_after_decision(state: AgentState) -> str:
    """根据 LLM 是否生成工具调用选择执行工具或直接输出答案。"""
    return "tool_call" if state.get("tool_calls") else "final_answer"


def route_after_tool_execution(state: AgentState) -> str:
    """根据工具执行状态路由到转人工、澄清或结果校验节点。"""
    if state.get("handoff_required"):
        return "handoff"
    if state.get("pending_confirmation"):
        return "clarify"
    return "validate"


def build_graph():
    """组装并编译一轮客服 Agent 的 LangGraph 状态图。"""
    g = StateGraph(AgentState)

    g.add_node("load_session_context", nodes.load_session_context)
    g.add_node("input_guardrail", nodes.input_guardrail)
    g.add_node("agent_decision", nodes.agent_decision)
    g.add_node("tool_execution", nodes.tool_execution)
    g.add_node("validate_tool_result", nodes.validate_tool_result)
    g.add_node("ask_clarification", nodes.ask_clarification)
    g.add_node("human_handoff", nodes.human_handoff)
    g.add_node("output_guardrail", nodes.output_guardrail)
    g.add_node("save_trace", nodes.save_trace)

    g.add_edge(START, "load_session_context")
    g.add_conditional_edges(
        "load_session_context",
        route_after_load,
        {"tool_execution": "tool_execution", "input_guardrail": "input_guardrail"},
    )
    g.add_edge("input_guardrail", "agent_decision")
    g.add_conditional_edges(
        "agent_decision",
        route_after_decision,
        {"tool_call": "tool_execution", "final_answer": "output_guardrail"},
    )
    g.add_conditional_edges(
        "tool_execution",
        route_after_tool_execution,
        {
            "handoff": "human_handoff",
            "clarify": "ask_clarification",
            "validate": "validate_tool_result",
        },
    )
    g.add_edge("validate_tool_result", "agent_decision")
    g.add_edge("ask_clarification", "save_trace")
    g.add_edge("human_handoff", "save_trace")
    g.add_edge("output_guardrail", "save_trace")
    g.add_edge("save_trace", END)

    return g.compile()


graph = build_graph()


async def run_turn(
    messages: list[dict[str, Any]],
    user_id: str,
    role: str,
    session_id: str,
    db: Any = None,
    confirmation_granted: bool = False,
    pending_tool_call: dict[str, Any] | None = None,
) -> AgentState:
    """运行一轮 Agent 并返回包含回答、确认和转人工状态的最终快照。

    Args:
        messages: OpenAI 消息格式的系统提示词和历史对话。
        user_id: 当前用户业务 ID，用于工具层数据隔离。
        role: 当前用户 RBAC 角色，决定可见工具集合。
        session_id: 多轮会话 ID。
        db: 请求作用域数据库会话；离线测试允许为空。
        confirmation_granted: 用户是否确认了上一轮挂起的写操作。
        pending_tool_call: 上一轮持久化的待确认工具调用。

    Returns:
        LangGraph 最终状态，包含 ``final_answer``、工具结果和安全标记。
    """
    state: AgentState = {
        "user_id": user_id,
        "role": role,
        "session_id": session_id,
        "messages": messages,
        "db": db,
        "confirmation_granted": confirmation_granted,
        "pending_tool_call": pending_tool_call,
    }
    result = await graph.ainvoke(state)
    return result
