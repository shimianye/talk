"""协作工具组：转人工、请求用户确认、保存会话摘要。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.tools.base import Tool, ToolContext, ToolResult
from app.models import Conversation


async def _transfer_to_human(ctx: ToolContext, reason: str) -> ToolResult:
    # 转人工由上层节点置位 handoff_required 并进入人工队列；这里返回交接信息
    return ToolResult(
        success=True,
        data={
            "handoff": True,
            "reason": reason,
            "session_id": ctx.session_id,
            "user_id": ctx.user_id,
        },
    )


async def _request_user_confirmation(ctx: ToolContext, question: str) -> ToolResult:
    # HITL：暂停执行，等待用户确认后恢复（写操作需确认，设计文档第 6 章）
    return ToolResult(
        success=True,
        data={"confirmation_required": True, "question": question},
    )


async def _save_conversation_summary(ctx: ToolContext, summary: str,
                                     conversation_id: str | None = None) -> ToolResult:
    cid = conversation_id or ctx.session_id
    if not cid:
        return ToolResult(success=False, error="缺少会话 ID", error_code="MISSING_PARAM")
    conv = (await ctx.db.execute(
        select(Conversation).where(Conversation.conversation_id == cid)
    )).scalar_one_or_none()
    if conv is None:
        return ToolResult(success=False, error="会话不存在", error_code="NOT_FOUND")
    conv.summary = summary
    await ctx.db.flush()
    return ToolResult(success=True, data={"conversation_id": cid, "saved": True})


def build_collaboration_tools() -> list[Tool]:
    return [
        Tool(
            name="transfer_to_human",
            description="当遇到投诉、法律威胁、安全事故、退款争议或用户明确要求时，转接人工客服。",
            parameters={
                "type": "object",
                "properties": {"reason": {"type": "string", "description": "转人工原因"}},
                "required": ["reason"],
            },
            permission="consumer",
            read_only=False,
            group="collaboration",
            handler=_transfer_to_human,
        ),
        Tool(
            name="request_user_confirmation",
            description="执行写操作（如下单、创建售后单）前请求用户确认。",
            parameters={
                "type": "object",
                "properties": {"question": {"type": "string", "description": "需要用户确认的问题"}},
                "required": ["question"],
            },
            permission="consumer",
            read_only=True,
            group="collaboration",
            handler=_request_user_confirmation,
        ),
        Tool(
            name="save_conversation_summary",
            description="保存当前会话的摘要（供人工接管时快速了解上下文）。",
            parameters={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "会话摘要文本"},
                    "conversation_id": {"type": "string"},
                },
                "required": ["summary"],
            },
            permission="agent",
            read_only=False,
            group="collaboration",
            handler=_save_conversation_summary,
        ),
    ]
