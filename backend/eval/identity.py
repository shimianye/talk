"""评测身份映射：只在 harness 中派生，不修改评测 xlsx。"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Product, ProductVariant

# 仅这 8 条样本绑定真实消费者；AUTO 表示从评测库实时派生。
OWNER_BY_QUESTION_ID: dict[int, str] = {
    81: "U6147", 82: "AUTO", 83: "AUTO", 84: "AUTO",
    85: "AUTO", 87: "AUTO", 88: "U9375", 93: "U6147",
}
EXPLICIT_ORDER_BY_SAMPLE_ID = {81: "ORD202609001", 88: "ORD202609015"}
DEFAULT_OWNER_USER_ID = "U6147"  # ORD202609001 的真实 owner；用于无显式订单号的指向性表达。


@dataclass(frozen=True)
class EvaluationIdentity:
    """评测某条样本时注入 Agent state 的可信服务端身份。"""

    user_id: str | None
    role: str = "consumer"
    participates_in_owner_metric: bool = False


async def identity_for_item(session: AsyncSession, item: dict) -> EvaluationIdentity:
    """从评测库实时派生样本 owner；非数据访问样本不绑定身份。"""
    item_id = int(item["id"])
    if item_id not in OWNER_BY_QUESTION_ID:
        return EvaluationIdentity(user_id=None)
    if item_id == 93:
        # 该样本测试语义拒答，不进入 order SQL owner/non-owner 指标。
        return EvaluationIdentity(user_id=DEFAULT_OWNER_USER_ID)

    explicit_order = EXPLICIT_ORDER_BY_SAMPLE_ID.get(item_id)
    if explicit_order:
        owner = await session.scalar(
            select(Order.user_id).where(Order.order_id == explicit_order)
        )
        if owner is None:
            raise RuntimeError(f"评测显式订单不存在: {explicit_order}")
        return EvaluationIdentity(str(owner), participates_in_owner_metric=True)

    if item_id == 85:
        owner = await session.scalar(
            select(Order.user_id)
            .join(ProductVariant, ProductVariant.variant_id == Order.variant_id)
            .join(Product, Product.product_id == ProductVariant.product_id)
            .where(Product.brand.ilike("%小米%"))
            .limit(1)
        )
        if owner is None:
            raise RuntimeError("无法为小米库存样本派生真实消费者")
        return EvaluationIdentity(str(owner), participates_in_owner_metric=True)

    # 82/83/84/87 无显式订单号；Mock 订单工具使用 ORD202609001，故绑定其真实 owner。
    owner = await session.scalar(
        select(Order.user_id).where(Order.order_id == "ORD202609001")
    )
    if owner is None:
        raise RuntimeError("无法派生默认订单 owner")
    return EvaluationIdentity(str(owner), participates_in_owner_metric=True)


async def owner_isolation_pair(session: AsyncSession) -> tuple[str, str, str]:
    """返回固定真实订单及其 owner/non-owner，供独立安全对偶探针使用。"""
    order_id = "ORD202609001"
    owner = await session.scalar(select(Order.user_id).where(Order.order_id == order_id))
    non_owner = await session.scalar(
        select(Order.user_id).where(Order.order_id == "ORD202609002")
    )
    if not owner or not non_owner or owner == non_owner:
        raise RuntimeError("无法构建 owner/non-owner 评测对偶")
    return order_id, str(owner), str(non_owner)
