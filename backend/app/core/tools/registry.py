"""工具注册表：集中管理全部工具，并按角色过滤可用工具。

LLM 只能通过注册表发起工具调用；注册表是工具权限边界的一部分。
"""
from __future__ import annotations

from typing import Any

from app.core.tools.base import Tool

_ROLE_LEVEL = {"consumer": 0, "agent": 1, "supervisor": 2, "admin": 3}


class ToolRegistry:
    """按唯一名称保存工具，并提供基于角色级别的过滤能力。"""

    def __init__(self) -> None:
        """初始化空的名称到工具映射。"""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册单个工具，名称重复时拒绝覆盖已有实现。"""
        if tool.name in self._tools:
            raise ValueError(f"工具重复注册: {tool.name}")
        self._tools[tool.name] = tool

    def register_many(self, tools: list[Tool]) -> None:
        """依次注册一组工具，并复用单工具的重复检查。"""
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Tool | None:
        """按模型返回的工具名称查找定义，不存在时返回 None。"""
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        """返回当前注册的全部工具。"""
        return list(self._tools.values())

    def for_role(self, role: str) -> list[Tool]:
        """返回指定角色可用的工具。"""
        level = _ROLE_LEVEL.get(role, 0)
        return [t for t in self._tools.values() if _ROLE_LEVEL.get(t.permission, 0) <= level]

    def to_openai_tools(self, role: str = "consumer") -> list[dict[str, Any]]:
        """返回指定角色可见工具的 OpenAI function calling Schema。"""
        return [t.to_openai_tool() for t in self.for_role(role)]

    def __len__(self) -> int:
        """返回注册工具数量。"""
        return len(self._tools)
