"""售后工具组：售后资格检查、售后单创建（写，需确认+幂等）、售后单查询。"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.cache import redis_client
from app.core.tools.base import Tool, ToolContext, ToolExecutionError, ToolResult
from app.core.tools.utils import serialize
from app.models import AfterSalesCase, Order

logger = logging.getLogger(__name__)

# 七天无理由退货（自然日）
_NO_REASON_WINDOW_DAYS = 7
# 不支持售后的订单状态
_CLOSED_STATUSES = {"已取消", "退款中", "已退款"}


async def _get_owned_order(ctx: ToolContext, order_id: str) -> Order:
    order = (await ctx.db.execute(
        select(Order).where(Order.order_id == order_id)
    )).scalar_one_or_none()
    if order is None:
        raise ToolExecutionError("订单不存在")
    if ctx.role == "consumer" and order.user_id != ctx.user_id:
        raise ToolExecutionError("无权操作该订单")
    return order


async def _check_after_sales_eligibility(ctx: ToolContext, order_id: str) -> ToolResult:
    order = await _get_owned_order(ctx, order_id)

    if order.order_status in _CLOSED_STATUSES:
        return ToolResult(
            success=True,
            data={"eligible": False, "reason": f"订单状态为「{order.order_status}」，不支持售后"},
        )

    if order.receive_time is not None:
        days = (datetime.now(timezone.utc) - order.receive_time).days
        if days > _NO_REASON_WINDOW_DAYS:
            return ToolResult(
                success=True,
                data={
                    "eligible": False,
                    "reason": f"签收已超过 {_NO_REASON_WINDOW_DAYS} 天，无理由退货不适用；如属质量问题请说明",
                },
            )

    return ToolResult(
        success=True,
        data={"eligible": True, "order_status": order.order_status, "reason": "在售后时效内"},
    )


async def _create_after_sales_case(
    ctx: ToolContext,
    order_id: str,
    case_type: str,
    description: str,
    sub_type: str | None = None,
    idempotency_key: str | None = None,
) -> ToolResult:
    order = await _get_owned_order(ctx, order_id)

    # 幂等：相同幂等键不重复建单（Redis 幂等键，设计文档第 4 章）
    if idempotency_key:
        idem_key = f"idem:after_sales:{ctx.user_id}:{idempotency_key}"
        try:
            existing = await redis_client.get(idem_key)
            if existing:
                return ToolResult(
                    success=True,
                    data={"case_id": existing, "idempotent_replay": True},
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 不可用，跳过幂等检查: %s", exc)

    case_id = f"AS-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    case = AfterSalesCase(
        case_id=case_id,
        order_id=order_id,
        user_id=ctx.user_id or order.user_id,
        case_type=case_type,
        sub_type=sub_type,
        description=description,
        status="已创建",
        create_time=datetime.now(timezone.utc),
    )
    ctx.db.add(case)
    await ctx.db.flush()

    if idempotency_key:
        try:
            await redis_client.set(idem_key, case_id, ex=86400)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 不可用，幂等键未写入: %s", exc)

    return ToolResult(success=True, data={"case_id": case_id, "status": "已创建"})


async def _get_after_sales_case(ctx: ToolContext, case_id: str | None = None,
                                order_id: str | None = None) -> ToolResult:
    stmt = select(AfterSalesCase)
    if case_id:
        stmt = stmt.where(AfterSalesCase.case_id == case_id)
    elif order_id:
        stmt = stmt.where(AfterSalesCase.order_id == order_id)
    else:
        return ToolResult(success=False, error="请提供 case_id 或 order_id", error_code="MISSING_PARAM")

    if ctx.role == "consumer":
        stmt = stmt.where(AfterSalesCase.user_id == ctx.user_id)

    cases = (await ctx.db.execute(stmt)).scalars().all()
    return ToolResult(success=True, data={"cases": [serialize(c) for c in cases]})


def build_after_sales_tools() -> list[Tool]:
    return [
        Tool(
            name="check_after_sales_eligibility",
            description="检查订单是否满足退货/换货/退款等售后条件（时效、订单状态）。",
            parameters={
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号"}},
                "required": ["order_id"],
            },
            permission="consumer",
            read_only=True,
            group="after_sales",
            handler=_check_after_sales_eligibility,
        ),
        Tool(
            name="create_after_sales_case",
            description="为用户创建售后工单（需用户确认后执行；写操作，幂等）。",
            parameters={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"},
                    "case_type": {"type": "string", "description": "售后类型：退货/换货/退款/投诉"},
                    "sub_type": {"type": "string", "description": "子类型，如 质量问题/发错货"},
                    "description": {"type": "string", "description": "问题描述"},
                    "idempotency_key": {"type": "string", "description": "幂等键，防重复建单"},
                },
                "required": ["order_id", "case_type", "description"],
            },
            permission="consumer",
            read_only=False,
            idempotent=True,
            requires_confirmation=True,
            confirmation_message="为您创建售后工单",
            group="after_sales",
            handler=_create_after_sales_case,
        ),
        Tool(
            name="get_after_sales_case",
            description="查询用户本人的售后工单进度。",
            parameters={
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "order_id": {"type": "string"},
                },
            },
            permission="consumer",
            read_only=True,
            group="after_sales",
            handler=_get_after_sales_case,
        ),
    ]
