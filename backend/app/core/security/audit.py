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
    """写入一条审计日志；失败仅记录告警，不中断主业务请求。

    Args:
        db: 当前请求的异步数据库会话。
        actor_user_id: 发起操作的用户 ID，系统任务允许为空。
        action: 稳定的动作名称，如 chat 或 takeover。
        resource_type: 被操作资源类型，如 conversation。
        resource_id: 被操作资源的业务 ID。
        detail: 额外的结构化审计上下文。
        ip: 调用方 IP 地址。
    """
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
