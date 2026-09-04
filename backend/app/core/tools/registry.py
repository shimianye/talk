"""工具注册表：集中管理全部工具，并按角色过滤可用工具。

LLM 只能通过注册表发起工具调用；注册表是工具权限边界的一部分。
"""
from __future__ import annotations

from typing import Any

from app.core.tools.base import Tool

_ROLE_LEVEL = {"consumer": 0, "agent": 1, "supervisor": 2, "admin": 3}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具重复注册: {tool.name}")
        self._tools[tool.name] = tool

    def register_many(self, tools: list[Tool]) -> None:
        for t in tools:
            self.register(t)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def for_role(self, role: str) -> list[Tool]:
        """返回指定角色可用的工具。"""
        level = _ROLE_LEVEL.get(role, 0)
        return [t for t in self._tools.values() if _ROLE_LEVEL.get(t.permission, 0) <= level]

    def to_openai_tools(self, role: str = "consumer") -> list[dict[str, Any]]:
        return [t.to_openai_tool() for t in self.for_role(role)]

    def __len__(self) -> int:
        return len(self._tools)
