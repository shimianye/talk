"""LLM 客户端工厂：根据配置返回 DeepSeek 或 Mock 实现。"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.core.llm.base import LLMClient
from app.core.llm.deepseek import DeepSeekClient
from app.core.llm.mock import MockLLMClient


@lru_cache
def get_llm_client() -> LLMClient:
    if settings.llm_provider == "deepseek" and settings.deepseek_api_key:
        return DeepSeekClient(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    return MockLLMClient()
