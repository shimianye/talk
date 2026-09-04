"""认证路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security.jwt import create_access_token
from app.core.security.password import verify_password
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    user = (
        await db.execute(
            select(User)
            .where(User.username == body.username)
            .options(selectinload(User.roles))
        )
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    role = next((r.name for r in user.roles), "consumer")
    token = create_access_token(subject=user.user_id, role=role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "display_name": user.display_name,
        "role": role,
    }


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "user_id": user.user_id,
        "display_name": user.display_name,
        "roles": [r.name for r in user.roles],
    }
