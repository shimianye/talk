"""RAG 管线：切分、向量化、入库、检索。"""
from app.core.rag.chunker import chunk_text
from app.core.rag.embedding import EmbeddingProvider, MockEmbeddingProvider, get_embedding_provider
from app.core.rag.ingest import ingest_kb_docs
from app.core.rag.retriever import hybrid_retrieve, retrieve, retrieve_with_fallback

__all__ = [
    "chunk_text",
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "get_embedding_provider",
    "ingest_kb_docs",
    "hybrid_retrieve",
    "retrieve",
    "retrieve_with_fallback",
]
