"""FastAPI 依赖：认证与角色校验。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security.jwt import decode_token
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """解析 Bearer JWT 并加载仍处于启用状态的用户及其角色。"""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未提供认证令牌")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "令牌无效或已过期") from exc

    user_id = payload.get("sub")
    user = (
        await db.execute(
            select(User).where(User.user_id == user_id).options(selectinload(User.roles))
        )
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已停用")
    return user


def require_role(*roles: str):
    """角色守卫依赖工厂。"""

    async def checker(user: User = Depends(get_current_user)) -> User:
        """确认当前用户至少拥有一个路由允许的角色。"""
        user_roles = {r.name for r in user.roles}
        if not (user_roles & set(roles)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "权限不足")
        return user

    return checker
