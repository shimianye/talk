"""实时业务工具组：价格、库存、订单、物流。

关键安全约束：订单/物流查询必须校验资源归属（设计文档第 6 章）。
"""
from __future__ import annotations

from sqlalchemy import func, or_, select

from app.core.tools.base import Tool, ToolContext, ToolExecutionError, ToolResult
from app.core.tools.utils import serialize
from app.models import (
    Inventory,
    LogisticsPackage,
    Order,
    Product,
    ProductVariant,
    Promotion,
    StoreProduct,
)


def _assert_owner(ctx: ToolContext, order: Order) -> None:
    if ctx.role == "consumer" and order.user_id != ctx.user_id:
        raise ToolExecutionError("无权访问该订单")


async def _resolve_variant_ids(ctx: ToolContext, variant_id: str | None,
                               product_id: str | None, query: str | None) -> list[str]:
    ids: list[str] = []
    if variant_id:
        ids.append(variant_id)
    if product_id:
        ids.extend(
            (await ctx.db.execute(
                select(ProductVariant.variant_id).where(ProductVariant.product_id == product_id)
            )).scalars().all()
        )
    if query and not ids:
        pattern = f"%{query}%"
        normalized = query.replace(" ", "").replace("　", "")
        normalized_pattern = f"%{normalized}%"
        ids.extend(
            (await ctx.db.execute(
                select(ProductVariant.variant_id)
                .join(Product, Product.product_id == ProductVariant.product_id)
                .where(or_(
                    Product.brand.ilike(pattern),
                    Product.model.ilike(pattern),
                    func.replace(func.replace(Product.brand, " ", ""), "　", "").ilike(normalized_pattern),
                    func.replace(func.replace(Product.model, " ", ""), "　", "").ilike(normalized_pattern),
                ))
            )).scalars().all()
        )
    return list(dict.fromkeys(ids))


async def _query_price(ctx: ToolContext, variant_id: str | None = None,
                       product_id: str | None = None, query: str | None = None) -> ToolResult:
    ids = await _resolve_variant_ids(ctx, variant_id, product_id, query)
    if not ids:
        return ToolResult(success=False, error="未定位到商品", error_code="NOT_FOUND")
    rows = (await ctx.db.execute(
        select(StoreProduct).where(StoreProduct.variant_id.in_(ids))
    )).scalars().all()
    if not rows:
        return ToolResult(success=False, error="商品暂未上架或价格缺失", error_code="NOT_FOUND")
    data = []
    for sp in rows:
        promo = None
        if sp.promotion_id:
            promo = (await ctx.db.execute(
                select(Promotion).where(Promotion.promo_id == sp.promotion_id)
            )).scalar_one_or_none()
        data.append({"store_product": serialize(sp), "promotion": serialize(promo)})
    return ToolResult(success=True, data={"prices": data, "count": len(data)})


async def _query_inventory(ctx: ToolContext, variant_id: str | None = None,
                           product_id: str | None = None, query: str | None = None) -> ToolResult:
    ids = await _resolve_variant_ids(ctx, variant_id, product_id, query)
    if not ids:
        return ToolResult(success=False, error="未定位到商品", error_code="NOT_FOUND")
    rows = (await ctx.db.execute(
        select(Inventory).where(Inventory.variant_id.in_(ids))
    )).scalars().all()
    total = sum(r.available_qty for r in rows)
    return ToolResult(
        success=True,
        data={"warehouses": [serialize(r) for r in rows], "total_available": total},
    )


async def _query_order(ctx: ToolContext, order_id: str) -> ToolResult:
    order = (await ctx.db.execute(
        select(Order).where(Order.order_id == order_id)
    )).scalar_one_or_none()
    if order is None:
        return ToolResult(success=False, error="订单不存在", error_code="ORDER_NOT_FOUND")
    _assert_owner(ctx, order)
    return ToolResult(success=True, data={"order": serialize(order)})


async def _query_logistics(ctx: ToolContext, order_id: str) -> ToolResult:
    order = (await ctx.db.execute(
        select(Order).where(Order.order_id == order_id)
    )).scalar_one_or_none()
    if order is None:
        return ToolResult(success=False, error="订单不存在", error_code="ORDER_NOT_FOUND")
    _assert_owner(ctx, order)
    packages = (await ctx.db.execute(
        select(LogisticsPackage).where(LogisticsPackage.order_id == order_id)
    )).scalars().all()
    return ToolResult(success=True, data={"packages": [serialize(p) for p in packages]})


def build_business_tools() -> list[Tool]:
    return [
        Tool(
            name="query_price",
            description="查询商品当前售价与优惠（实时价格，不来自知识库静态回答）。",
            parameters={
                "type": "object",
                "properties": {
                    "variant_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "query": {"type": "string", "description": "商品名关键词"},
                },
            },
            permission="consumer",
            read_only=True,
            group="business",
            handler=_query_price,
        ),
        Tool(
            name="query_inventory",
            description="查询商品在各仓库的库存数量。",
            parameters={
                "type": "object",
                "properties": {
                    "variant_id": {"type": "string"},
                    "product_id": {"type": "string"},
                    "query": {"type": "string", "description": "商品名关键词"},
                },
            },
            permission="consumer",
            read_only=True,
            group="business",
            handler=_query_inventory,
        ),
        Tool(
            name="query_order",
            description="查询用户本人的订单详情（仅限订单所有者查询）。",
            parameters={
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号"}},
                "required": ["order_id"],
            },
            permission="consumer",
            read_only=True,
            group="business",
            handler=_query_order,
        ),
        Tool(
            name="query_logistics",
            description="查询订单的物流包裹与最新轨迹。",
            parameters={
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号"}},
                "required": ["order_id"],
            },
            permission="consumer",
            read_only=True,
            group="business",
            handler=_query_logistics,
        ),
    ]
