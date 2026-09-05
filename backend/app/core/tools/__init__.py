"""工具模块入口：组装完整的工具注册表。"""
from __future__ import annotations

from functools import lru_cache

from app.core.tools.after_sales import build_after_sales_tools
from app.core.tools.business import build_business_tools
from app.core.tools.collaboration import build_collaboration_tools
from app.core.tools.knowledge import build_knowledge_tools
from app.core.tools.product import build_product_tools
from app.core.tools.registry import ToolRegistry


@lru_cache
def build_registry() -> ToolRegistry:
    """构建并缓存包含全部 14 个业务工具的注册表。"""
    registry = ToolRegistry()
    registry.register_many(build_product_tools())      # 商品 3
    registry.register_many(build_knowledge_tools())    # 知识 1
    registry.register_many(build_business_tools())     # 实时业务 4
    registry.register_many(build_after_sales_tools())  # 售后 3
    registry.register_many(build_collaboration_tools())  # 协作 3
    return registry


registry = build_registry()

__all__ = ["registry", "build_registry"]
