"""管理路由：客服工作台（会话接管、工单）与管理员面板（商品/审计/Trace/知识库）。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.rag.embedding import get_embedding_provider
from app.core.rag.ingest import ingest_kb_docs
from app.core.security.audit import write_audit
from app.core.tools.utils import serialize
from app.db.session import get_db
from app.models import (
    AfterSalesCase,
    AgentTrace,
    AuditLog,
    Conversation,
    KnowledgeDocument,
    Message,
    Product,
    User,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- 客服工作台 ----------
class HumanMessage(BaseModel):
    content: str
    internal_note: bool = False


@router.get("/conversations")
async def list_conversations(
    status: str | None = None,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Conversation).order_by(Conversation.id.desc())
    if status:
        stmt = stmt.where(Conversation.status == status)
    convs = (await db.execute(stmt)).scalars().all()
    return {"conversations": [serialize(c) for c in convs]}


@router.get("/conversations/{session_id}")
async def get_conversation(
    session_id: str,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conv = (
        await db.execute(select(Conversation).where(Conversation.conversation_id == session_id))
    ).scalar_one_or_none()
    msgs = (
        await db.execute(
            select(Message).where(Message.conversation_id == session_id).order_by(Message.id)
        )
    ).scalars().all()
    return {"conversation": serialize(conv), "messages": [serialize(m) for m in msgs]}


@router.post("/conversations/{session_id}/takeover")
async def takeover(
    session_id: str,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conv = (
        await db.execute(select(Conversation).where(Conversation.conversation_id == session_id))
    ).scalar_one_or_none()
    if conv is None:
        raise HTTPException(404, "会话不存在")
    conv.status = "agent_handling"
    conv.handoff_required = False
    await write_audit(db, user.user_id, "takeover", "conversation", session_id)
    await db.commit()
    return {"ok": True}


@router.post("/conversations/{session_id}/messages")
async def send_human_message(
    session_id: str,
    body: HumanMessage,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    db.add(
        Message(
            conversation_id=session_id,
            sender="human",
            content=body.content,
            message_type="note" if body.internal_note else "text",
        )
    )
    await db.commit()
    return {"ok": True}


# ---------- 售后工单 ----------
class CaseUpdate(BaseModel):
    status: str | None = None
    resolution: str | None = None
    handler: str | None = None
    compensation_amount: float | None = None


@router.get("/after-sales")
async def list_after_sales(
    status: str | None = None,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(AfterSalesCase).order_by(AfterSalesCase.create_time.desc())
    if status:
        stmt = stmt.where(AfterSalesCase.status == status)
    cases = (await db.execute(stmt)).scalars().all()
    return {"cases": [serialize(c) for c in cases]}


@router.post("/after-sales/{case_id}")
async def update_after_sales(
    case_id: str,
    body: CaseUpdate,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    case = (
        await db.execute(select(AfterSalesCase).where(AfterSalesCase.case_id == case_id))
    ).scalar_one_or_none()
    if case is None:
        raise HTTPException(404, "工单不存在")
    if body.status:
        case.status = body.status
    if body.resolution:
        case.resolution = body.resolution
        case.resolve_time = datetime.now(timezone.utc)
    if body.handler:
        case.handler = body.handler
    if body.compensation_amount is not None:
        case.compensation_amount = body.compensation_amount
    await write_audit(db, user.user_id, "update_after_sales", "after_sales_cases", case_id, body.model_dump())
    await db.commit()
    return {"ok": True}


# ---------- 管理员面板 ----------
@router.get("/products")
async def list_products(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    products = (await db.execute(select(Product))).scalars().all()
    return {"products": [serialize(p) for p in products]}


@router.get("/knowledge")
async def list_knowledge(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    docs = (await db.execute(select(KnowledgeDocument))).scalars().all()
    return {"documents": [serialize(d) for d in docs]}


@router.get("/traces")
async def list_traces(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    traces = (
        await db.execute(select(AgentTrace).order_by(AgentTrace.id.desc()).limit(100))
    ).scalars().all()
    return {"traces": [serialize(t) for t in traces]}


@router.get("/audit")
async def list_audit(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    logs = (await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))).scalars().all()
    return {"logs": [serialize(a) for a in logs]}


@router.post("/kb/reingest")
async def reingest_kb(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from pathlib import Path

    kb_dir = Path(__file__).resolve().parents[3] / "data" / "kb-docs"
    stats = await ingest_kb_docs(db, kb_dir, get_embedding_provider())
    await db.commit()
    return {"stats": stats}
