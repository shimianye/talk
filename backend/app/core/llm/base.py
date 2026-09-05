"""LLM 适配层基类：统一的响应类型、客户端抽象与熔断器。

设计文档第 6 章要求：模型调用封装在 LLMClient 适配层，支持超时、重试、熔断、
结构化输出和 Mock 实现；LLM 只能通过 Tool Registry 发起工具调用。
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """LLM 返回的一次工具调用。

    Attributes:
        id: 模型生成的调用 ID，用于关联后续 tool 结果消息。
        name: Tool Registry 中注册的工具名称。
        arguments: 已解析为字典的工具参数。
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """不同模型供应商统一转换后的响应。

    Attributes:
        content: 普通文本答案；发起工具调用时通常为空。
        tool_calls: 模型请求执行的结构化工具列表。
        finish_reason: 模型停止原因，如 ``stop`` 或 ``tool_calls``。
        usage: prompt、completion 和 total token 数量。
    """

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        """返回响应是否包含至少一个工具调用。"""
        return bool(self.tool_calls)


class LLMClient(ABC):
    """LLM 客户端抽象接口。"""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """对话补全，可返回文本或工具调用。"""

    @abstractmethod
    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """结构化输出：要求模型返回 JSON 对象（意图/实体提取等）。"""


class CircuitBreaker:
    """轻量熔断器：连续失败达到阈值后打开，冷却期内快速失败。"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        """初始化熔断阈值、恢复窗口和连续失败计数。"""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        """返回当前是否处于应快速失败的熔断打开期。"""
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.recovery_timeout:
            # 半开状态：允许一次试探
            return False
        return True

    def record_success(self) -> None:
        """记录成功调用并清空失败计数和打开时间。"""
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        """累计失败次数，达到阈值时打开熔断器。"""
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._opened_at = time.monotonic()


class LLMUnavailableError(RuntimeError):
    """LLM 不可用（熔断打开 / 全部重试失败）时抛出，供上层降级或转人工。"""
