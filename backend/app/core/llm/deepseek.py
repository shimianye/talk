"""DeepSeek 客户端（OpenAI 兼容协议）。

内置超时、指数退避重试与熔断。
"""
from __future__ import annotations

import json
import logging
from typing import Any

import openai
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.llm.base import (
    CircuitBreaker,
    LLMClient,
    LLMResponse,
    LLMUnavailableError,
    ToolCall,
)

logger = logging.getLogger(__name__)

_RETRYABLE = (
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class DeepSeekClient(LLMClient):
    """通过 OpenAI 兼容协议调用 DeepSeek 的异步客户端。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
        failure_threshold: int = 3,
    ):
        """创建客户端并配置模型、超时、重试和熔断策略。"""
        self.model = model
        self.max_retries = max_retries
        self.breaker = CircuitBreaker(failure_threshold=failure_threshold)
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,  # 重试统一由 _create_with_retry 控制
        )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """执行普通对话补全，并将文本或工具调用转换为统一响应。"""
        if self.breaker.is_open:
            raise LLMUnavailableError("LLM 熔断已打开，暂不可用")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            resp = await self._create_with_retry(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self.breaker.record_failure()
            logger.error("DeepSeek 调用失败: %s", exc)
            raise LLMUnavailableError(f"DeepSeek 调用失败: {exc}") from exc

        self.breaker.record_success()
        choice = resp.choices[0]
        message = choice.message

        tool_calls: list[ToolCall] = []
        for tc in message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        usage = resp.usage
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
        )

    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """要求 DeepSeek 返回 JSON 对象，解析失败时返回空字典。"""
        if self.breaker.is_open:
            raise LLMUnavailableError("LLM 熔断已打开，暂不可用")

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = await self._create_with_retry(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self.breaker.record_failure()
            logger.error("DeepSeek JSON 调用失败: %s", exc)
            raise LLMUnavailableError(f"DeepSeek JSON 调用失败: {exc}") from exc

        self.breaker.record_success()
        raw = resp.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("DeepSeek 返回非 JSON: %.200s", raw)
            return {}

    async def _create_with_retry(self, **kwargs: Any):
        """对可恢复的网络、限流和服务端错误执行指数退避重试。"""
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.max_retries + 1),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=True,
        ):
            with attempt:
                return await self._client.chat.completions.create(**kwargs)
