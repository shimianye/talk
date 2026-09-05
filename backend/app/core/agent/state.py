"""Agent 状态定义（对齐设计文档第 5 章 AgentState）。"""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph 节点之间共享的一轮对话状态。

    ``total=False`` 表示节点可以渐进写入字段，无需在创建状态时一次性提供全部键。
    """

    # 身份与会话（服务端注入）
    user_id: str  # 当前登录用户的业务 ID，用于数据归属校验。
    role: str  # RBAC 角色：consumer、agent、supervisor 或 admin。
    session_id: str  # 会话 ID，同时关联 Conversation 和多轮上下文。
    trace_id: str  # 单轮 Agent 执行链路 ID，用于排障与审计。

    # 对话与理解
    messages: list[dict[str, Any]]  # OpenAI 消息格式的完整上下文。
    intent: str | None  # 标准化意图名，例如 price_query。
    entities: dict[str, Any]  # 从用户问题提取的商品、订单号、预算等实体。
    plan: list[str]  # LLM 给出的高层执行步骤，主要用于 Trace 和评测。

    # 工具调用循环
    tool_calls: list[dict[str, Any]]  # 当前等待执行的工具调用。
    tool_results: list[dict[str, Any]]  # 本轮累计的结构化工具结果。
    sources: list[dict[str, Any]]  # RAG 命中的来源及引用信息。

    # 控制流
    pending_confirmation: bool  # 是否正在等待用户确认写操作。
    pending_tool_call: dict[str, Any] | None  # Redis 中可恢复的待执行调用。
    confirmation_granted: bool  # 用户本轮是否已明确确认。
    handoff_required: bool  # 是否需要进入人工客服队列。
    guardrail_flags: list[str]  # 注入、PII、执行上限等安全标记。
    final_answer: str | None  # 最终面向用户的文本回答。

    # 执行限制
    steps: int  # 本轮经过 agent_decision 的次数。
    total_tool_calls: int  # 本轮已实际执行的工具总数。

    # 运行时对象（非序列化，用于节点内部）
    db: Any  # 请求作用域 AsyncSession；离线单测时可为 None。
