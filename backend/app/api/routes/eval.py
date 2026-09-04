"""评测路由：管理员触发评测并查看结果。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run")
async def run_eval(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from eval.run_eval import run_evaluation

    return await run_evaluation(db=db)
