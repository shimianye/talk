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
    """服务端注入的调用上下文（不信任 LLM 传入的身份信息）。

    Attributes:
        user_id: 当前登录用户 ID，用于订单和售后资源归属校验。
        role: 当前 RBAC 角色，默认是消费者。
        session_id: 当前会话 ID，用于转人工和摘要关联。
        db: 请求作用域的异步数据库会话。
    """

    user_id: str | None = None
    role: str = "consumer"  # consumer | agent | supervisor | admin
    session_id: str | None = None
    db: AsyncSession | None = None


@dataclass
class ToolResult:
    """所有工具统一返回的结构化结果。

    Attributes:
        success: 工具是否完成预期业务操作。
        data: 成功时返回的 JSON 可序列化业务数据。
        error: 失败时供 Agent 理解和展示的错误说明。
        error_code: 便于程序判断失败类别的稳定错误码。
    """

    success: bool
    data: Any = None
    error: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将工具结果转换为可传给 LLM 和 Trace 的普通字典。"""
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
    """一个可供 LLM 选择、受服务端权限控制的业务工具。"""

    name: str  # 注册表中的唯一名称，也是模型 function name。
    description: str  # 提供给 LLM 的能力描述和使用边界。
    parameters: dict[str, Any]  # OpenAI function calling 使用的 JSON Schema。
    permission: str  # 最低角色：consumer、agent、supervisor 或 admin。
    read_only: bool  # False 表示工具会改变业务数据。
    timeout: float = 10.0  # 单次执行最长秒数。
    idempotent: bool = False  # 重试相同请求是否不会产生重复副作用。
    requires_confirmation: bool = False  # 执行前是否必须获得用户确认。
    requires_approval: bool = False  # 是否需要主管审批。
    confirmation_message: str | None = None  # 面向用户的确认文案。
    handler: ToolHandler = field(default=None)  # 实际异步业务函数。
    group: str = "misc"  # 商品、知识、售后等工具分组。

    def to_openai_tool(self) -> dict[str, Any]:
        """转换为 OpenAI 兼容的 function tool Schema。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, ctx: ToolContext, **params: Any) -> ToolResult:
        """在超时和异常保护下调用处理函数，并统一错误返回。"""
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
