"""知识工具组：知识库语义检索（含文本降级与引用溯源）。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.rag.embedding import get_embedding_provider
from app.core.rag.retriever import retrieve_with_fallback
from app.core.tools.base import Tool, ToolContext, ToolResult
from app.core.tools.utils import serialize
from app.models import KnowledgeDocument


async def _search_knowledge_base(ctx: ToolContext, query: str,
                                 top_k: int = 5) -> ToolResult:
    """检索知识片段并补充去重后的来源文档信息。"""
    if not query:
        return ToolResult(success=False, error="查询词不能为空", error_code="MISSING_PARAM")

    embedding = get_embedding_provider()
    chunks, method = await retrieve_with_fallback(ctx.db, query, embedding, top_k=top_k)

    # 引用溯源：返回片段对应的文档标题与来源
    sources: list[dict] = []
    seen_docs: set[str] = set()
    for c in chunks:
        doc = (
            await ctx.db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.document_id == c["document_id"])
            )
        ).scalar_one_or_none()
        if doc is not None and doc.document_id not in seen_docs:
            seen_docs.add(doc.document_id)
            sources.append(
                {"document_id": doc.document_id, "title": doc.title, "version": doc.version}
            )

    return ToolResult(
        success=True,
        data={
            "chunks": chunks,
            "sources": sources,
            "method": method,
            "count": len(chunks),
        },
    )


def build_knowledge_tools() -> list[Tool]:
    """构建带引用溯源的知识库检索工具。"""
    return [
        Tool(
            name="search_knowledge_base",
            description="在商品知识与政策知识库中语义检索（退换货、保修、配送、发票、促销规则等），返回带来源的片段。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词"},
                    "top_k": {"type": "integer", "description": "返回片段数，默认 5"},
                },
                "required": ["query"],
            },
            permission="consumer",
            read_only=True,
            group="knowledge",
            handler=_search_knowledge_base,
        ),
    ]
