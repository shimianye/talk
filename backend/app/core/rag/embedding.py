"""Embedding 提供者：Mock（哈希）与可扩展的真实模型接入。"""
from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import settings

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


class EmbeddingProvider(ABC):
    """文本向量化提供者的统一异步接口。"""

    model_name: str
    dim: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化。"""


class MockEmbeddingProvider(EmbeddingProvider):
    """确定性哈希 Embedding：词袋哈希 + L2 归一化。

    零外部依赖，用于离线跑通 RAG 管线；共享词元的文本会得到更高余弦相似度，
    可作为轻量词法检索信号。真实语义检索应接入 BGE-M3。
    """

    def __init__(self, dim: int = 1024):
        """设置哈希向量维度；必须与数据库 vector 列维度一致。"""
        self.model_name = "mock-hash-v1"
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量生成确定性的 L2 归一化哈希向量。"""
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        """将一段文本映射为固定维度的词袋哈希向量。"""
        vec = [0.0] * self.dim
        for tok in _TOKEN_RE.findall((text or "").lower()):
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class RemoteEmbeddingProvider(EmbeddingProvider):
    """OpenAI 兼容 Embedding（可接 TEI 部署的 BGE-M3、Ollama 等）。"""

    def __init__(self, base_url: str, model: str, api_key: str = "", dim: int = 1024):
        """创建指向 OpenAI 兼容 Embedding 服务的异步 HTTP 客户端。"""
        import httpx

        self.model = model
        self.model_name = model
        self.dim = dim
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=30.0,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """调用远程服务并按原始 input 索引返回向量。"""
        resp = await self._client.post(
            "/v1/embeddings", json={"model": self.model, "input": texts}
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        data.sort(key=lambda x: x["index"])
        return [item["embedding"] for item in data]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """按配置返回缓存的远程向量服务或本地 Mock 实现。"""
    if settings.embedding_provider == "openai" and settings.embedding_base_url:
        return RemoteEmbeddingProvider(
            base_url=settings.embedding_base_url,
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            dim=settings.embedding_dim,
        )
    return MockEmbeddingProvider(dim=settings.embedding_dim)
