"""会话路由：消费者查看自己的会话与消息。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Conversation, Message, User
from app.core.tools.utils import serialize

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """按创建顺序倒序返回当前用户自己的会话列表。"""
    convs = (
        await db.execute(
            select(Conversation).where(Conversation.user_id == user.user_id).order_by(Conversation.id.desc())
        )
    ).scalars().all()
    return {"sessions": [serialize(c) for c in convs]}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回指定会话及其按顺序排列的消息记录。"""
    conv = (
        await db.execute(
            select(Conversation).where(Conversation.conversation_id == session_id)
        )
    ).scalar_one_or_none()
    if conv is None:
        return {"conversation": None, "messages": []}
    msgs = (
        await db.execute(
            select(Message)
            .where(Message.conversation_id == session_id)
            .order_by(Message.id)
        )
    ).scalars().all()
    return {"conversation": serialize(conv), "messages": [serialize(m) for m in msgs]}
