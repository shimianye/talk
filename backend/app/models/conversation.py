"""会话、消息、Agent 轨迹与审计日志模型。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """一次客服会话。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(  # 对外会话 ID，也作为消息关联键。
        String(64), unique=True, index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="consumer")
    status: Mapped[str] = mapped_column(String(32), default="open")  # open、pending_human、agent_handling 等。
    summary: Mapped[str | None] = mapped_column(Text)  # 供人工接管快速阅读的会话摘要。
    handoff_required: Mapped[bool] = mapped_column(default=False)  # 是否进入人工客服待处理队列。


class Message(Base, TimestampMixin):
    """会话中的一条消息。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender: Mapped[str] = mapped_column(String(32), nullable=False)  # user / agent / human
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), default="text")  # text 或仅工作台可见的 note。
    intent: Mapped[str | None] = mapped_column(String(64))  # 该轮识别出的标准意图。
    entities: Mapped[dict | None] = mapped_column(JSONB)  # 商品、订单号、预算等结构化实体。


class AgentTrace(Base):
    """Agent 执行轨迹（可重放节点、工具调用与错误）。"""

    __tablename__ = "agent_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # 单轮执行唯一 ID。
    conversation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64))
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    role: Mapped[str | None] = mapped_column(String(32))
    intent: Mapped[str | None] = mapped_column(String(64))
    entities: Mapped[dict | None] = mapped_column(JSONB)
    plan: Mapped[list | None] = mapped_column(JSONB)
    tool_calls: Mapped[list | None] = mapped_column(JSONB)  # 模型生成的工具调用快照。
    tool_results: Mapped[list | None] = mapped_column(JSONB)  # 工具结构化返回快照。
    sources: Mapped[list | None] = mapped_column(JSONB)  # RAG 引用来源列表。
    guardrail_flags: Mapped[list | None] = mapped_column(JSONB)  # 注入、PII、限额等安全标记。
    handoff_required: Mapped[bool | None] = mapped_column(default=False)
    final_answer: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)  # 单轮总耗时，单位毫秒。
    token_usage: Mapped[dict | None] = mapped_column(JSONB)  # 模型 token 或工具调用量统计。
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditLog(Base):
    """审计日志（谁在何时对什么资源做了什么）。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSONB)  # 动作相关的非敏感结构化上下文。
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
