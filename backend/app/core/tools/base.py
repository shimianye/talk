"""工具框架：Tool 定义、执行上下文与结果。

设计文档第 6 章要求每个工具声明 name / description / JSON Schema 参数、
permission / read_only / timeout / idempotency，以及需要用户确认或主管审批的条件。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolContext:
    """服务端注入的调用上下文（不信任 LLM 传入的身份/租户信息）。"""

    user_id: str | None = None
    role: str = "consumer"  # consumer | agent | supervisor | admin
    session_id: str | None = None
    db: AsyncSession | None = None


@dataclass
class ToolResult:
    """工具结构化结果。"""

    success: bool
    data: Any = None
    error: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
        }


class ToolExecutionError(Exception):
    """工具执行失败（已按结构化错误处理）。"""


# handler 签名：async (ctx: ToolContext, **params) -> ToolResult
ToolHandler = Callable[[ToolContext, Any], Awaitable[ToolResult]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    permission: str  # 最低角色：consumer | agent | supervisor | admin
    read_only: bool
    timeout: float = 10.0
    idempotent: bool = False
    requires_confirmation: bool = False
    requires_approval: bool = False  # 需要主管审批
    confirmation_message: str | None = None  # 面向用户的确认文案
    handler: ToolHandler = field(default=None)  # type: ignore[assignment]
    group: str = "misc"

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, ctx: ToolContext, **params: Any) -> ToolResult:
        try:
            result = await asyncio.wait_for(
                self.handler(ctx, **params), timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"工具 {self.name} 执行超时（>{self.timeout}s）",
                error_code="TOOL_TIMEOUT",
            )
        except ToolExecutionError as exc:
            return ToolResult(success=False, error=str(exc))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                success=False,
                error=f"工具 {self.name} 执行异常: {exc}",
                error_code="TOOL_INTERNAL_ERROR",
            )
