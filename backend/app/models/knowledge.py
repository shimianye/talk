"""知识库、意图分类与评测集模型。"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db.base import Base, TimestampMixin


class KnowledgeDocument(Base):
    """RAG 知识文档（含版本、来源、有效期、访问级别）。"""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)  # 基于内容哈希生成的稳定文档 ID。
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    version: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(64))
    effective_from: Mapped[date | None] = mapped_column(Date)  # 政策或参数开始生效日期。
    effective_until: Mapped[date | None] = mapped_column(Date)  # 失效日期；空值表示未设截止日。
    content_hash: Mapped[str | None] = mapped_column(String(64))  # 入库幂等和版本识别用 MD5。
    chunking_strategy: Mapped[str | None] = mapped_column(String(64))
    embedding_model: Mapped[str | None] = mapped_column(String(64))
    access_level: Mapped[str] = mapped_column(String(32), default="public")  # public 或内部访问级别。
    file_path: Mapped[str | None] = mapped_column(String(512))


class KnowledgeChunk(Base):
    """知识片段（向量化后的检索单元）。"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("knowledge_documents.document_id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 片段在原文中的顺序号。
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 实际参与检索和引用的正文。
    token_count: Mapped[int | None] = mapped_column(Integer)  # 当前实现记录近似字符数。
    embedding: Mapped[list | None] = mapped_column(Vector(1024))  # 与配置维度一致的检索向量。
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)  # 来源文件等扩展元数据。


class IntentTaxonomy(Base):
    """意图分类。对应 intent_taxonomy 表。"""

    __tablename__ = "intent_taxonomy"

    intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    intent_cn: Mapped[str | None] = mapped_column(String(64))
    example_question: Mapped[str | None] = mapped_column(Text)
    processing_method: Mapped[str | None] = mapped_column(Text)
    requires_tool: Mapped[str | None] = mapped_column(String(8))
    tool_name: Mapped[str | None] = mapped_column(String(64))
    priority: Mapped[str | None] = mapped_column(String(16))
    description: Mapped[str | None] = mapped_column(Text)


class EvaluationItem(Base):
    """评测集条目。对应 evaluation_dataset 的 evaluation 表。"""

    __tablename__ = "evaluation_dataset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64))
    expected_answer: Mapped[str | None] = mapped_column(Text)
    expected_source: Mapped[str | None] = mapped_column(String(255))
    should_call_tool: Mapped[str | None] = mapped_column(String(8))  # 期望是否调用工具。
    should_transfer_human: Mapped[str | None] = mapped_column(String(8))  # 期望是否转人工。
    difficulty: Mapped[str | None] = mapped_column(String(16))
    evaluation_notes: Mapped[str | None] = mapped_column(Text)
    expected_tool_name: Mapped[str | None] = mapped_column(String(64))
    expected_route: Mapped[str | None] = mapped_column(String(64))
