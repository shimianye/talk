"""商品工具组：参数查询、对比、推荐。"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tools.base import Tool, ToolContext, ToolResult
from app.core.tools.utils import serialize
from app.models import Price, Product, ProductVariant


def _build_product_filter(query: str | None, product_id: str | None, model: str | None):
    """按 product_id、型号或文本关键词构造商品 SPU 查询。"""
    stmt = select(Product)
    if product_id:
        return stmt.where(Product.product_id == product_id)
    if model:
        return stmt.where(Product.model.ilike(f"%{model}%"))
    if query:
        pattern = f"%{query}%"
        return stmt.where(
            or_(
                Product.brand.ilike(pattern),
                Product.model.ilike(pattern),
                Product.series.ilike(pattern),
            )
        )
    return None


async def _load_product_details(db: AsyncSession, product: Product) -> dict:
    """聚合一个商品 SPU 的 SKU 规格和官方指导价。"""
    variants = (
        await db.execute(
            select(ProductVariant).where(ProductVariant.product_id == product.product_id)
        )
    ).scalars().all()
    prices = (
        await db.execute(
            select(Price).where(Price.product_id == product.product_id)
        )
    ).scalars().all()
    return {
        "product": serialize(product),
        "variants": [serialize(v) for v in variants],
        "official_prices": [serialize(p) for p in prices],
    }


async def _query_product_spec(ctx: ToolContext, query: str | None = None,
                              product_id: str | None = None,
                              model: str | None = None) -> ToolResult:
    """查询匹配手机的基础信息、全部规格和官方价格。"""
    stmt = _build_product_filter(query, product_id, model)
    if stmt is None:
        return ToolResult(success=False, error="请提供 query/product_id/model 之一", error_code="MISSING_PARAM")
    products = (await ctx.db.execute(stmt)).scalars().all()
    if not products:
        return ToolResult(success=False, error="未找到匹配商品", error_code="NOT_FOUND")
    details = [await _load_product_details(ctx.db, p) for p in products]
    return ToolResult(success=True, data={"products": details, "count": len(details)})


async def _compare_products(ctx: ToolContext, product_ids: list[str] | None = None,
                            query: str | None = None) -> ToolResult:
    """按商品 ID 或关键词加载多款手机的结构化对比数据。"""
    ids = product_ids or []
    if query and not ids:
        products = (await ctx.db.execute(_build_product_filter(query, None, None))).scalars().all()
        ids = [p.product_id for p in products]
    if not ids:
        return ToolResult(success=False, error="请提供 product_ids 或 query", error_code="MISSING_PARAM")
    products = (await ctx.db.execute(select(Product).where(Product.product_id.in_(ids)))).scalars().all()
    details = [await _load_product_details(ctx.db, p) for p in products]
    return ToolResult(success=True, data={"comparison": details, "count": len(details)})


async def _recommend_products(ctx: ToolContext, budget: float | None = None,
                              preference: str | None = None,
                              brand: str | None = None,
                              top_n: int = 3) -> ToolResult:
    """按品牌和预算筛选官方价格，并返回指定数量的候选手机。"""
    stmt = select(Price)
    if brand:
        stmt = stmt.join(Product, Product.product_id == Price.product_id).where(
            Product.brand == brand
        )
    prices = (await ctx.db.execute(stmt)).scalars().all()
    if budget is not None:
        prices = [p for p in prices if float(p.official_price) <= budget]
    # 简单评分：价格从低到高排序，优先官方建议零售价合理的机型
    prices = sorted(prices, key=lambda p: float(p.official_price))[: top_n]
    if not prices:
        return ToolResult(success=False, error="该预算内暂无匹配商品", error_code="NOT_FOUND")
    result = []
    for p in prices:
        product = (await ctx.db.execute(
            select(Product).where(Product.product_id == p.product_id)
        )).scalar_one_or_none()
        result.append({
            "product": serialize(product),
            "price": serialize(p),
            "preference_match": preference or None,
        })
    return ToolResult(success=True, data={"recommendations": result, "count": len(result)})


def build_product_tools() -> list[Tool]:
    """构建商品参数查询、对比和推荐三个只读工具。"""
    return [
        Tool(
            name="query_product_spec",
            description="查询手机商品的详细参数（处理器、屏幕、摄像头、电池、防水等），可按商品名或 product_id 查询。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "商品名称或关键词，如 iPhone 16"},
                    "product_id": {"type": "string", "description": "商品 ID，如 APPLE_IPHONE_16"},
                    "model": {"type": "string", "description": "具体型号"},
                },
            },
            permission="consumer",
            read_only=True,
            group="product",
            handler=_query_product_spec,
        ),
        Tool(
            name="compare_products",
            description="对比两款或多款手机的参数与价格，返回结构化对比结果。",
            parameters={
                "type": "object",
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要对比的商品 ID 列表",
                    },
                    "query": {"type": "string", "description": "商品名关键词（无 product_ids 时用）"},
                },
            },
            permission="consumer",
            read_only=True,
            group="product",
            handler=_compare_products,
        ),
        Tool(
            name="recommend_products",
            description="根据预算、偏好和品牌推荐合适的手机。",
            parameters={
                "type": "object",
                "properties": {
                    "budget": {"type": "number", "description": "预算上限（元）"},
                    "preference": {"type": "string", "description": "偏好，如拍照、游戏、续航"},
                    "brand": {"type": "string", "description": "品牌，如 Apple/Huawei/Xiaomi"},
                    "top_n": {"type": "integer", "description": "返回数量，默认 3"},
                },
            },
            permission="consumer",
            read_only=True,
            group="product",
            handler=_recommend_products,
        ),
    ]
