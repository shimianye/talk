"""聊天路由：JSON 与 SSE 流式两种返回。"""
from __future__ import annotations

import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.chat_service import handle_chat

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """消费者发起一轮对话的请求体。"""

    message: str  # 本轮用户问题原文。
    session_id: str | None = None  # 为空时创建新会话，否则延续历史。


def _sse(event: str, data: dict) -> str:
    """将事件名和数据编码为标准 Server-Sent Events 文本帧。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """同步完成一轮 Agent 对话并返回完整 JSON 响应。"""
    session_id = body.session_id or uuid.uuid4().hex
    result = await handle_chat(db, user, session_id, body.message)
    result["session_id"] = session_id
    return result


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """以 SSE 事件流返回状态、增量文本、完整答案和结束标记。"""
    session_id = body.session_id or uuid.uuid4().hex

    async def event_stream() -> AsyncGenerator[str, None]:
        """执行聊天服务并按 SSE 协议逐个生成响应事件。"""
        yield _sse("status", {"message": "正在思考…"})
        result = await handle_chat(db, user, session_id, body.message)
        result["session_id"] = session_id
        # Token 级 SSE：先发送元数据，再按字符增量推送答案，前端可即时渲染。
        answer = result.get("answer", "")
        meta = {k: v for k, v in result.items() if k != "answer"}
        yield _sse("message_start", meta)
        for token in answer:
            yield _sse("token", {"token": token})
        yield _sse("message_end", {"answer": answer})
        yield _sse("done", {})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
