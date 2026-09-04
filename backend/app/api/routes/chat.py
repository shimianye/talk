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
    message: str
    session_id: str | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
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
    session_id = body.session_id or uuid.uuid4().hex

    async def event_stream() -> AsyncGenerator[str, None]:
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
