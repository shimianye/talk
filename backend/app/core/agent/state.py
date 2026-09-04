"""Agent 状态定义（对齐设计文档第 5 章 AgentState）。"""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # 身份与会话（服务端注入）
    user_id: str
    role: str
    session_id: str
    trace_id: str

    # 对话与理解
    messages: list[dict[str, Any]]
    intent: str | None
    entities: dict[str, Any]
    plan: list[str]

    # 工具调用循环
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    sources: list[dict[str, Any]]

    # 控制流
    pending_confirmation: bool
    pending_tool_call: dict[str, Any] | None
    confirmation_granted: bool
    handoff_required: bool
    guardrail_flags: list[str]
    final_answer: str | None

    # 执行限制
    steps: int
    total_tool_calls: int

    # 运行时对象（非序列化，用于节点内部）
    db: Any
