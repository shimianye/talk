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
    """人工客服向会话追加消息的请求体。"""

    content: str  # 消息或内部备注正文。
    internal_note: bool = False  # True 时仅作为工作台内部备注保存。


@router.get("/conversations")
async def list_conversations(
    status: str | None = None,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """列出客服可处理的会话，可按会话状态筛选。"""
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
    """返回指定会话的主记录和按时间排列的全部消息。"""
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
    """将待人工会话标记为客服处理中，并记录接管审计。"""
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
    """向指定会话写入人工回复或内部备注。"""
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
    """客服更新售后工单时允许修改的字段。"""

    status: str | None = None  # 工单流转状态。
    resolution: str | None = None  # 最终处理方案；填写后记录解决时间。
    handler: str | None = None  # 当前处理客服的业务标识。
    compensation_amount: float | None = None  # 补偿金额，单位为元。


@router.get("/after-sales")
async def list_after_sales(
    status: str | None = None,
    user: User = Depends(require_role("agent", "supervisor", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """列出售后工单，可按工单状态筛选。"""
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
    """更新售后状态、处理方案、处理人或补偿金额并写审计。"""
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
    """返回管理后台展示的全部商品 SPU。"""
    products = (await db.execute(select(Product))).scalars().all()
    return {"products": [serialize(p) for p in products]}


@router.get("/knowledge")
async def list_knowledge(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回知识库文档元数据，不包含全部片段正文。"""
    docs = (await db.execute(select(KnowledgeDocument))).scalars().all()
    return {"documents": [serialize(d) for d in docs]}


@router.get("/traces")
async def list_traces(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回最近 100 条 Agent 执行 Trace。"""
    traces = (
        await db.execute(select(AgentTrace).order_by(AgentTrace.id.desc()).limit(100))
    ).scalars().all()
    return {"traces": [serialize(t) for t in traces]}


@router.get("/audit")
async def list_audit(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回最近 100 条系统审计日志。"""
    logs = (await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))).scalars().all()
    return {"logs": [serialize(a) for a in logs]}


@router.post("/kb/reingest")
async def reingest_kb(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """由管理员触发知识文档幂等重入库并返回统计。"""
    from pathlib import Path

    kb_dir = Path(__file__).resolve().parents[3] / "data" / "kb-docs"
    stats = await ingest_kb_docs(db, kb_dir, get_embedding_provider())
    await db.commit()
    return {"stats": stats}
