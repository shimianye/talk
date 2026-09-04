"""RAG 切分、Embedding 与混合检索单元测试。"""
from app.core.rag.chunker import chunk_text
from app.core.rag.embedding import MockEmbeddingProvider
from app.core.rag.retriever import BM25, _rrf_fuse


def test_chunk_text_basic():
    chunks = chunk_text("段落一。\n\n段落二。\n\n段落三。", chunk_size=100)
    assert len(chunks) >= 1
    assert all(c.strip() for c in chunks)


def test_chunk_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


async def test_embedding_dimension():
    emb = MockEmbeddingProvider(dim=64)
    vecs = await emb.embed(["你好世界", "hello world"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 64


async def test_embedding_similarity():
    emb = MockEmbeddingProvider(dim=128)
    (a,) = await emb.embed(["七天无理由退货"])
    (b,) = await emb.embed(["七天无理由退货 支持"])
    (c,) = await emb.embed(["完全无关的内容"])
    sim_ab = sum(x * y for x, y in zip(a, b))
    sim_ac = sum(x * y for x, y in zip(a, c))
    assert sim_ab > sim_ac


def test_bm25_ranking():
    corpus = ["手机七天无理由退货政策", "手机电池续航参数", "退换货规则与保修说明"]
    bm25 = BM25(corpus)
    scores = bm25.score("退货")
    assert scores[0] > scores[1]  # 含"退货"的文档得分更高


def test_rrf_fusion():
    # 两路排序：A 排 [0,1,2]，B 排 [2,0,1]，融合后 0 号应最靠前
    fused = _rrf_fuse([[0, 1, 2], [2, 0, 1]])
    top_idx = fused[0][0]
    assert top_idx == 0
