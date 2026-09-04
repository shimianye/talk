"""应用配置：统一从环境变量 / .env 读取，由 pydantic-settings 管理。

所有可变配置（密钥、端口、模型、执行限制）均通过环境变量注入，
禁止硬编码到代码或仓库，符合设计文档第 11 章「部署与可观测性」约定。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 基础
    app_name: str = "phone-commerce-agent"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    # 数据库 / 缓存
    database_url: str = "postgresql+asyncpg://pca:pca_password@localhost:5432/phone_commerce"
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    llm_provider: str = "mock"  # mock | deepseek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    # Embedding
    embedding_provider: str = "mock"  # mock | openai（OpenAI 兼容，可接 TEI/BGE-M3 或 Ollama）
    embedding_model: str = "bge-m3"
    embedding_dim: int = 1024
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    kb_docs_dir: str = "/data/kb-docs"

    # 安全
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Agent 执行限制
    max_agent_steps: int = 8
    max_tool_calls: int = 12
    max_tokens_per_turn: int = 4000
    tool_timeout_seconds: float = 10.0

    # CORS
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
