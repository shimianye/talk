"""模型聚合导出：导入本模块即可注册全部 ORM 实体到 Base.metadata。

Alembic autogenerate 依赖此处完整导入。
"""
from app.models.catalog import (
    Inventory,
    Price,
    Product,
    ProductVariant,
    Promotion,
    Source,
    StoreProduct,
)
from app.models.conversation import AgentTrace, AuditLog, Conversation, Message
from app.models.knowledge import (
    EvaluationItem,
    IntentTaxonomy,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.models.order import (
    AfterSalesCase,
    LogisticsEvent,
    LogisticsPackage,
    Order,
    OrderItem,
)
from app.models.user import Role, User, UserRole

__all__ = [
    # user
    "Role",
    "User",
    "UserRole",
    # catalog
    "Product",
    "ProductVariant",
    "Price",
    "Source",
    "StoreProduct",
    "Inventory",
    "Promotion",
    # order
    "Order",
    "OrderItem",
    "LogisticsPackage",
    "LogisticsEvent",
    "AfterSalesCase",
    # knowledge
    "KnowledgeDocument",
    "KnowledgeChunk",
    "IntentTaxonomy",
    "EvaluationItem",
    # conversation
    "Conversation",
    "Message",
    "AgentTrace",
    "AuditLog",
]
