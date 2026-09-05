"""本地受管知识文档的增量同步与孤儿清理。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag.chunker import chunk_text
from app.core.rag.embedding import EmbeddingProvider
from app.core.rag.ingest import parse_document
from app.models import KnowledgeChunk, KnowledgeDocument

MANAGED_SOURCE = "seed:local"
CHUNKER_VERSION = "paragraph-v1"


def chunk_config_hash(chunk_size: int, overlap: int) -> str:
    """计算影响切分结果的稳定配置指纹。"""
    payload = json.dumps(
        {"chunk_size": chunk_size, "overlap": overlap,
         "separator": "blank-line+sentence", "version": CHUNKER_VERSION},
        ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def document_id_for_path(relative_path: str) -> str:
    """用规范化相对路径生成跨内容版本稳定的文档 ID。"""
    digest = hashlib.sha256(relative_path.encode("utf-8")).hexdigest()
    return f"doc-{digest[:20]}"


async def sync_knowledge_docs(
    session: AsyncSession, docs_dir: Path, embedding: EmbeddingProvider, *,
    chunk_size: int = 500, overlap: int = 60,
) -> dict[str, Any]:
    """按四维版本键同步 Markdown，仅重嵌变化文档并清理受管孤儿。"""
    docs_dir = docs_dir.resolve()
    files = sorted(docs_dir.rglob("*.md")) if docs_dir.is_dir() else []
    config_hash = chunk_config_hash(chunk_size, overlap)
    chunking_signature = f"recursive:{config_hash[:16]}"
    raw_embedding_signature = f"{embedding.model_name}:{embedding.dim}"
    embedding_signature = raw_embedding_signature
    if len(embedding_signature) > 64:
        embedding_signature = (
            f"sha256:{hashlib.sha256(raw_embedding_signature.encode('utf-8')).hexdigest()[:48]}"
        )

    stats = {"documents": 0, "chunks": 0, "skipped": 0, "deleted": 0}
    managed_paths: set[str] = set()
    for path in files:
        relative_path = path.relative_to(docs_dir).as_posix()
        managed_paths.add(relative_path)
        metadata = parse_document(path)
        document = (
            await session.execute(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.source == MANAGED_SOURCE,
                    KnowledgeDocument.file_path == relative_path,
                )
            )
        ).scalar_one_or_none()
        version_matches = (
            document
            and document.content_hash == metadata["content_hash"]
            and document.chunking_strategy == chunking_signature
            and document.embedding_model == embedding_signature
        )
        chunk_count = 0
        if version_matches:
            chunk_count = int(
                await session.scalar(
                    select(func.count()).select_from(KnowledgeChunk).where(
                        KnowledgeChunk.document_id == document.document_id
                    )
                ) or 0
            )
        if version_matches and chunk_count > 0:
            stats["skipped"] += 1
            continue

        if document is None:
            document = KnowledgeDocument(
                document_id=document_id_for_path(relative_path),
                source=MANAGED_SOURCE,
                file_path=relative_path,
                access_level="public",
            )
            session.add(document)
        else:
            await session.execute(
                delete(KnowledgeChunk).where(
                    KnowledgeChunk.document_id == document.document_id
                )
            )

        document.title = metadata["title"]
        document.category = metadata["category"]
        document.version = metadata["version"]
        document.region = "中国大陆"
        document.effective_from = metadata["effective_from"]
        document.content_hash = metadata["content_hash"]
        document.chunking_strategy = chunking_signature
        document.embedding_model = embedding_signature
        await session.flush()

        chunks = chunk_text(metadata["text"], chunk_size=chunk_size, overlap=overlap)
        vectors = await embedding.embed(chunks) if chunks else []
        if len(vectors) != len(chunks):
            raise ValueError("Embedding 返回数量与知识片段数量不一致")
        for index, (content, vector) in enumerate(zip(chunks, vectors)):
            session.add(KnowledgeChunk(
                document_id=document.document_id, chunk_index=index, content=content,
                token_count=len(content), embedding=vector,
                metadata_={"source_file": relative_path},
            ))
        stats["documents"] += 1
        stats["chunks"] += len(chunks)

    existing = (
        await session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.source == MANAGED_SOURCE)
        )
    ).scalars().all()
    for document in existing:
        if document.file_path not in managed_paths:
            await session.delete(document)
            stats["deleted"] += 1
    await session.flush()
    return stats
