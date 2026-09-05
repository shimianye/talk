"""种子与知识同步的确定性单元测试。"""
from app.core.rag.embedding import MockEmbeddingProvider, RemoteEmbeddingProvider
from app.services.kb_sync import chunk_config_hash, document_id_for_path
from app.services.seed_sync import seed_fingerprint, validate_source_integrity


def test_seed_source_integrity_and_fingerprint_are_stable():
    """当前种子满足引用约束，且相同输入产生相同指纹。"""
    assert not any(validate_source_integrity().values())
    assert seed_fingerprint() == seed_fingerprint()
    assert len(seed_fingerprint()) == 64


def test_chunk_config_and_document_identity_are_versioned():
    """切分参数改变版本键，但文档 ID 只由规范路径决定。"""
    assert chunk_config_hash(500, 60) == chunk_config_hash(500, 60)
    assert chunk_config_hash(500, 60) != chunk_config_hash(600, 60)
    assert chunk_config_hash(500, 60) != chunk_config_hash(500, 80)
    assert document_id_for_path("apple/iphone-16.md") == document_id_for_path(
        "apple/iphone-16.md"
    )
    assert document_id_for_path("apple/iphone-16.md") != document_id_for_path(
        "apple/iphone-15.md"
    )


def test_embedding_providers_expose_real_version_metadata():
    """Mock 与远程 provider 都暴露版本键所需的模型名和维度。"""
    mock = MockEmbeddingProvider(dim=64)
    assert (mock.model_name, mock.dim) == ("mock-hash-v1", 64)

    remote = RemoteEmbeddingProvider(
        base_url="http://embedding.invalid", model="bge-m3", dim=1024
    )
    assert (remote.model_name, remote.dim) == ("bge-m3", 1024)
