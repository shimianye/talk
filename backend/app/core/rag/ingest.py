"""知识库入库：读取 kb-docs 目录 → 解析 → 切分 → 向量化 → 落库。"""
from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag.chunker import chunk_text
from app.core.rag.embedding import EmbeddingProvider
from app.models import KnowledgeChunk, KnowledgeDocument

_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_VERSION_RE = re.compile(r"文档版本[：:]\s*([Vv]\d+\.\d+|\d+\.\d+)")
_EFFECTIVE_RE = re.compile(r"生效日期[：:]\s*(\d{4}-\d{2}-\d{2})")


def _parse_document(path: Path) -> dict:
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
    """入库知识库目录，返回统计信息。幂等：按内容哈希跳过已入库文档。"""
    files = sorted(docs_dir.rglob("*.md")) if docs_dir.is_dir() else []
    stats = {"documents": 0, "chunks": 0, "skipped": 0}

    for path in files:
        meta = _parse_document(path)

        existing = (
            await db.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.content_hash == meta["content_hash"]
                )
            )
        ).scalar_one_or_none()
        if existing:
            stats["skipped"] += 1
            continue

        doc = KnowledgeDocument(
            document_id=f"doc-{meta['content_hash'][:12]}",
            title=meta["title"],
            category=meta["category"],
            version=meta["version"],
            source=meta["path"],
            region="中国大陆",
            effective_from=meta["effective_from"],
            content_hash=meta["content_hash"],
            chunking_strategy="recursive",
            embedding_model=getattr(embedding, "dim", None) and "mock-hash",
            access_level="public",
            file_path=meta["path"],
        )
        db.add(doc)
        await db.flush()

        chunks = chunk_text(meta["text"], chunk_size=chunk_size)
        vectors = await embedding.embed(chunks)
        for i, (content, vec) in enumerate(zip(chunks, vectors)):
            db.add(
                KnowledgeChunk(
                    document_id=doc.document_id,
                    chunk_index=i,
                    content=content,
                    token_count=len(content),
                    embedding=vec,
                    metadata_={"source_file": meta["path"]},
                )
            )
        stats["documents"] += 1
        stats["chunks"] += len(chunks)

    await db.flush()
    return stats
