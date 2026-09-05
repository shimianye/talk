"""知识库入库：读取 kb-docs 目录 → 解析 → 切分 → 向量化 → 落库。"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag.embedding import EmbeddingProvider

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_VERSION_RE = re.compile(r"文档版本[：:]\s*([Vv]\d+\.\d+|\d+\.\d+)")
_EFFECTIVE_RE = re.compile(r"生效日期[：:]\s*(\d{4}-\d{2}-\d{2})")


def parse_document(path: Path) -> dict:
    """解析知识文档标题、版本、生效日期、内容哈希和原始正文。"""
    text = path.read_text(encoding="utf-8")
    m = _TITLE_RE.search(text)
    title = m.group(1).strip() if m else path.stem
    version = _VERSION_RE.search(text)
    effective = _EFFECTIVE_RE.search(text)
    content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    return {
        "title": title,
        "category": path.parent.name,
        "version": version.group(1) if version else "V1.0",
        "effective_from": date.fromisoformat(effective.group(1)) if effective else None,
        "content_hash": content_hash,
        "text": text,
        "path": str(path),
    }


async def ingest_kb_docs(
    db: AsyncSession,
    docs_dir: Path,
    embedding: EmbeddingProvider,
    chunk_size: int = 500,
) -> dict:
    """兼容入口：委托统一知识同步服务执行版本化增量入库。

    Returns:
        包含 ``documents``、``chunks``、``skipped`` 和 ``deleted`` 的统计。
    """
    from app.services.kb_sync import sync_knowledge_docs

    return await sync_knowledge_docs(
        db, docs_dir, embedding, chunk_size=chunk_size
    )
