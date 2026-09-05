"""混合检索：pgvector 向量检索 + BM25 关键词检索 + RRF 融合，文本降级兜底。

- 向量：pgvector 余弦相似度
- 关键词：纯 Python BM25（零外部依赖）
- 融合：RRF（Reciprocal Rank Fusion）
"""
from __future__ import annotations

import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag.embedding import EmbeddingProvider
from app.models import KnowledgeChunk

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z0-9]+")


def _tokenize(text: str) -> list[str]:
    """中文用字符二元组（bigram），英文/数字按词切分。"""
    tokens: list[str] = []
    for seg in _TOKEN_RE.findall((text or "").lower()):
        if re.match(r"[\u4e00-\u9fff]", seg):
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
        else:
            tokens.append(seg)
    return tokens


class BM25:
    """轻量 BM25 实现（Okapi BM25）。"""

    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        """预计算语料分词、文档长度和词项文档频率。"""
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_tokens = [self._tokenize(d) for d in corpus]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.n = len(corpus)
        self.avgdl = sum(self.doc_len) / max(self.n, 1)
        self.df: Counter = Counter()
        for tokens in self.doc_tokens:
            self.df.update(set(tokens))

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """复用模块级中英文分词规则。"""
        return _tokenize(text)

    def score(self, query: str) -> list[float]:
        """计算查询相对每篇文档的 Okapi BM25 分数。"""
        scores = [0.0] * self.n
        for term in self._tokenize(query):
            df = self.df.get(term, 0)
            if df == 0:
                continue
            idf = math.log((self.n - df + 0.5) / (df + 0.5) + 1)
            for i, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (1 - self.b + self.b * self.doc_len[i] / max(self.avgdl, 1))
                scores[i] += idf * (tf * (self.k1 + 1)) / denom
        return scores


def _rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """多路排序结果 RRF 融合，返回 [(idx, fused_score)] 按分数降序。"""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda x: -x[1])


async def _load_chunks(db: AsyncSession) -> list[KnowledgeChunk]:
    """加载已生成向量的全部知识片段作为混合检索语料。"""
    return (
        await db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.embedding.is_not(None))
        )
    ).scalars().all()


async def hybrid_retrieve(
    db: AsyncSession,
    query: str,
    embedding: EmbeddingProvider,
    top_k: int = 5,
) -> tuple[list[dict], str]:
    """执行向量与 BM25 双路召回，并使用 RRF 融合排名。

    Returns:
        ``(结果列表, "hybrid")``；结果同时保留融合、BM25 和向量分数。
    """
    chunks = await _load_chunks(db)
    if not chunks:
        return [], "empty"

    (query_vec,) = await embedding.embed([query])
    contents = [c.content for c in chunks]

    # 向量相似度
    vec_scores = []
    for c in chunks:
        sim = sum(a * b for a, b in zip(query_vec, c.embedding))
        vec_scores.append(sim)

    # BM25
    bm25 = BM25(contents)
    bm25_scores = bm25.score(query)

    # 排序（降序索引）
    vec_rank = sorted(range(len(chunks)), key=lambda i: -vec_scores[i])
    bm25_rank = sorted(range(len(chunks)), key=lambda i: -bm25_scores[i])

    fused = _rrf_fuse([vec_rank, bm25_rank])
    results = []
    for idx, score in fused[:top_k]:
        results.append(
            {
                "content": chunks[idx].content,
                "document_id": chunks[idx].document_id,
                "chunk_index": chunks[idx].chunk_index,
                "similarity": round(float(score), 4),
                "bm25": round(float(bm25_scores[idx]), 4),
                "vector": round(float(vec_scores[idx]), 4),
            }
        )
    return results, "hybrid"


async def _text_retrieve(db: AsyncSession, query: str, top_k: int) -> list[dict]:
    """使用数据库 ILIKE 执行无向量依赖的精确文本兜底检索。"""
    pattern = f"%{query}%"
    chunks = (
        await db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.content.ilike(pattern)).limit(top_k)
        )
    ).scalars().all()
    return [
        {
            "content": c.content,
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "similarity": 1.0,
            "bm25": None,
            "vector": None,
        }
        for c in chunks
    ]


async def retrieve_with_fallback(
    db: AsyncSession,
    query: str,
    embedding: EmbeddingProvider,
    top_k: int = 5,
) -> tuple[list[dict], str]:
    """混合检索，命中为空时降级为文本检索（设计文档：检索降级）。"""
    results, method = await hybrid_retrieve(db, query, embedding, top_k=top_k)
    if results:
        return results, method
    return await _text_retrieve(db, query, top_k), "text"


async def retrieve(
    db: AsyncSession,
    query: str,
    embedding: EmbeddingProvider,
    top_k: int = 5,
    min_similarity: float = 0.0,
) -> list[dict]:
    """纯向量检索（保留给需要单一语义召回的调用方）。"""
    chunks = await _load_chunks(db)
    (query_vec,) = await embedding.embed([query])
    scored = []
    for c in chunks:
        sim = sum(a * b for a, b in zip(query_vec, c.embedding))
        if sim >= min_similarity:
            scored.append((sim, c))
    scored.sort(key=lambda x: -x[0])
    return [
        {
            "content": c.content,
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "similarity": round(float(sim), 4),
        }
        for sim, c in scored[:top_k]
    ]
