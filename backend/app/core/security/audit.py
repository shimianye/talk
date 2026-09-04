"""审计日志写入辅助。"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

logger = logging.getLogger(__name__)


async def write_audit(
    db: AsyncSession,
    actor_user_id: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    try:
        db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                ip=ip,
            )
        )
        await db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("审计写入失败: %s", exc)
