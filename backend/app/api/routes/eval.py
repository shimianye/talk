"""评测路由：管理员触发评测并查看结果。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from app.api.deps import require_role
from app.models import User

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run")
async def run_eval(
    user: User = Depends(require_role("admin")),
) -> dict:
    """仅允许管理员在独立评测库运行评测并返回报告。"""
    from eval.run_eval import run_evaluation

    return await run_evaluation()
