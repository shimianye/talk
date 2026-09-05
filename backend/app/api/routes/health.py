"""健康检查与运行模式信息。"""
from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """返回 API 状态及当前 LLM、Embedding 配置模式。"""
    return {
        "status": "ok",
        "mode": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.deepseek_model if settings.llm_provider == "deepseek" else "mock",
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model if settings.embedding_provider != "mock" else "mock-hash",
        },
        "components": {
            "database": "pending",
            "redis": "pending",
        },
    }
