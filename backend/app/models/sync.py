"""数据同步元信息模型。"""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncManifest(Base):
    """记录受管数据域最近一次成功同步的输入指纹和结果。"""

    __tablename__ = "sync_manifests"

    sync_domain: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sync_version: Mapped[str] = mapped_column(String(32), nullable=False)
    statistics: Mapped[dict | None] = mapped_column(JSONB)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
