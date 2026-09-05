"""聊天服务：会话管理 + Agent 编排 + 持久化 + 确认恢复。"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.graph import run_turn
from app.core.cache import redis_client
from app.core.security.audit import write_audit
from app.config import settings
from app.models import Conversation, Message, User

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是手机电商店铺的智能客服助手。职责：商品参数咨询、对比与推荐、价格与库存查询、"
    "订单与物流查询、售后协助。规则：\n"
    "1. 实时价格/库存/订单/物流必须调用工具查询，不得凭记忆编造；\n"
    "2. 订单/物流/售后只能查询用户本人信息；\n"
    "3. 写操作（如创建售后单）必须先请求用户确认；\n"
    "4. 遇到投诉、法律威胁、安全事故或用户明确要求，转人工客服；\n"
    "5. 回答简洁友好，使用中文。"
)

_CONFIRM_WORDS = ("确认", "同意", "好的", "可以", "是的", "确认一下", "yes", "ok", "确定")


def _pending_key(user_id: str, session_id: str) -> str:
    """生成用户与会话双重隔离的 Redis 待确认键。"""
    # 键含 user_id，防止跨用户确认状态串用
    return f"pending:{user_id}:{session_id}"


async def _load_conversation(db: AsyncSession, user: User, session_id: str) -> Conversation:
    """加载现有会话；首次请求时按当前用户和角色创建会话。"""
    conv = (
        await db.execute(
            select(Conversation).where(Conversation.conversation_id == session_id)
        )
    ).scalar_one_or_none()
    if conv is None:
        conv = Conversation(
            conversation_id=session_id,
            user_id=user.user_id,
            role=next((r.name for r in user.roles), "consumer"),
            status="open",
        )
        db.add(conv)
        await db.flush()
    return conv


async def _load_history(db: AsyncSession, conversation_id: str) -> list[dict]:
    """按消息顺序加载历史并转换为 OpenAI user/assistant 格式。"""
    msgs = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
    ).scalars().all()
    history: list[dict] = []
    for m in msgs:
        role = "assistant" if m.sender == "agent" else "user"
        history.append({"role": role, "content": m.content})
    return history


async def handle_chat(
    db: AsyncSession,
    user: User,
    session_id: str,
    user_message: str,
) -> dict:
    """处理一轮聊天，串联确认恢复、Agent 执行、持久化和审计。

    Args:
        db: 请求作用域的异步数据库会话。
        user: 通过 JWT 加载且携带角色关系的当前用户。
        session_id: 当前多轮会话 ID。
        user_message: 用户本轮输入的原始文本。

    Returns:
        前端响应字典，包含回答、意图、确认状态、转人工状态和运行模式。
    """
    role = next((r.name for r in user.roles), "consumer")
    conv = await _load_conversation(db, user, session_id)
    history = await _load_history(db, conv.conversation_id)

    # 确认恢复：上一轮存在待确认的写操作
    confirmation_granted = False
    pending_tool_call = None
    try:
        raw = await redis_client.get(_pending_key(user.user_id, session_id))
    except Exception:  # noqa: BLE001
        raw = None
    if raw:
        try:
            pending_tool_call = json.loads(raw)
            if any(w in user_message for w in _CONFIRM_WORDS):
                confirmation_granted = True
                try:
                    await redis_client.delete(_pending_key(user.user_id, session_id))
                except Exception:  # noqa: BLE001
                    pass
        except json.JSONDecodeError:
            pending_tool_call = None

    # 记录用户消息
    db.add(
        Message(
            conversation_id=conv.conversation_id,
            sender="user",
            content=user_message,
            message_type="text",
        )
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_message}]

    state = await run_turn(
        messages=messages,
        user_id=user.user_id,
        role=role,
        session_id=session_id,
        db=db,
        confirmation_granted=confirmation_granted,
        pending_tool_call=pending_tool_call,
    )

    final_answer = state.get("final_answer") or "抱歉，我暂时无法回答，请稍后再试。"

    # 记录 Agent 回复
    db.add(
        Message(
            conversation_id=conv.conversation_id,
            sender="agent",
            content=final_answer,
            message_type="text",
            intent=state.get("intent"),
        )
    )

    # 挂起确认：持久化待执行的写操作
    if state.get("pending_confirmation") and state.get("pending_tool_call"):
        try:
            await redis_client.set(
                _pending_key(user.user_id, session_id),
                json.dumps(state["pending_tool_call"], ensure_ascii=False),
                ex=1800,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 不可用，确认状态未持久化: %s", exc)

    if state.get("handoff_required"):
        conv.handoff_required = True
        conv.status = "pending_human"

    await write_audit(
        db, user.user_id, "chat",
        resource_type="conversation",
        resource_id=conv.conversation_id,
        detail={"intent": state.get("intent"), "handoff": state.get("handoff_required", False)},
    )
    await db.commit()

    return {
        "conversation_id": conv.conversation_id,
        "answer": final_answer,
        "pending_confirmation": state.get("pending_confirmation", False),
        "handoff_required": state.get("handoff_required", False),
        "guardrail_flags": state.get("guardrail_flags", []),
        "intent": state.get("intent"),
        "mode": {
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
        },
    }
