"""Mock LLM 客户端：DeepSeek 不可用（无 Key / 离线）时跑通链路与测试。

确定性、零外部依赖。行为模拟真实 Agent：命中关键词先发起一次工具调用，
收到工具结果后转为文本作答，避免空转。
"""
from __future__ import annotations

import re
from typing import Any

from app.core.llm.base import LLMClient, LLMResponse, ToolCall

# 关键词 → 工具名（工具调用启发式）
_KEYWORD_TO_TOOL = {
    "参数": "query_product_spec",
    "屏幕": "query_product_spec",
    "处理器": "query_product_spec",
    "对比": "compare_products",
    "怎么选": "compare_products",
    "推荐": "recommend_products",
    "价格": "query_price",
    "多少钱": "query_price",
    "库存": "query_inventory",
    "有货": "query_inventory",
    "没货": "query_inventory",
    "订单": "query_order",
    "物流": "query_logistics",
    "快递": "query_logistics",
    "退货": "check_after_sales_eligibility",
    "退款": "check_after_sales_eligibility",
    "换货": "check_after_sales_eligibility",
    "保修": "search_knowledge_base",
    "配送": "search_knowledge_base",
    "发票": "search_knowledge_base",
    "促销": "search_knowledge_base",
    "投诉": "transfer_to_human",
    "转人工": "transfer_to_human",
    "人工": "transfer_to_human",
}

# 各工具的参数模板（query 类用原文，订单类用种子订单号）
_ARGS_BY_TOOL = {
    "query_product_spec": ("query", "text"),
    "compare_products": ("query", "text"),
    "recommend_products": ("query", "text"),
    "search_knowledge_base": ("query", "text"),
    "query_price": ("query", "text"),
    "query_inventory": ("query", "text"),
    "query_order": ("order_id", "ORD202609001"),
    "query_logistics": ("order_id", "ORD202609001"),
    "check_after_sales_eligibility": ("order_id", "ORD202609001"),
    "get_after_sales_case": ("order_id", "ORD202609001"),
    "create_after_sales_case": ("order_id", "ORD202609001"),
    "transfer_to_human": ("reason", "text"),
    "request_user_confirmation": ("question", "text"),
}


class MockLLMClient(LLMClient):
    """用于本地开发和测试的确定性 LLM 替身。"""

    def __init__(self, **_: Any):
        """接受并忽略真实客户端配置，保持与工厂调用方式兼容。"""
        pass

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """按关键词模拟工具选择，收到工具结果后生成固定格式回答。"""
        last_user = self._last_user_text(messages)

        # 上一轮是工具结果 → 转为文本作答，避免重复调用同一工具
        if messages and messages[-1].get("role") == "tool":
            return LLMResponse(
                content=f"[Mock] 已根据工具结果整理回答：{self._summarize(messages[-1].get('content', ''))}",
                tool_calls=[],
                finish_reason="stop",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        if tools:
            available = {t["function"]["name"] for t in tools}
            for keyword, tool_name in _KEYWORD_TO_TOOL.items():
                if keyword in last_user and tool_name in available:
                    return LLMResponse(
                        content=None,
                        tool_calls=[
                            ToolCall(
                                id="mock-1",
                                name=tool_name,
                                arguments=self._guess_args(tool_name, last_user),
                            )
                        ],
                        finish_reason="tool_calls",
                        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    )

        return LLMResponse(
            content=f"[Mock] 已收到你的问题：「{last_user}」",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """使用关键词规则模拟意图识别和结构化 JSON 输出。"""
        last_user = self._last_user_text(messages)
        return {"intent": self._classify_intent(last_user), "entities": {}, "query": last_user}

    @staticmethod
    def _classify_intent(text: str) -> str:
        """将用户文本映射到评测数据使用的标准意图名称。"""
        # 关键词 → 意图（与 intent_taxonomy 对齐）
        if "对比" in text or "怎么选" in text:
            return "product_compare"
        if "推荐" in text or "买哪个" in text or "买什么" in text:
            return "purchase_recommend"
        if "价格" in text or "多少钱" in text or "优惠" in text:
            return "price_query"
        if "库存" in text or "有货" in text or "没货" in text:
            return "inventory_query"
        if "物流" in text or "快递" in text or "配送" in text or "到哪" in text:
            return "shipping_policy"
        if "订单" in text:
            return "order_query"
        if "保修" in text or "质保" in text:
            return "warranty_policy"
        if "发票" in text:
            return "invoice_query"
        if "促销" in text or "活动" in text:
            return "promotion_query"
        if "退货" in text or "退款" in text or "换货" in text:
            return "refund_policy"
        if "投诉" in text:
            return "complaint"
        if "人工" in text or "转人工" in text:
            return "escalation"
        if "你好" in text or "您好" in text or "在吗" in text:
            return "greeting"
        if "处理器" in text or "屏幕" in text or "参数" in text or "电池" in text \
                or "摄像头" in text or "内存" in text or "充电" in text:
            return "product_spec"
        return "unknown"

    @staticmethod
    def _last_user_text(messages: list[dict[str, Any]]) -> str:
        """从 OpenAI 消息列表中取得最近一条用户输入。"""
        for m in reversed(messages):
            if m.get("role") == "user":
                return str(m.get("content", ""))
        return ""

    @staticmethod
    def _summarize(tool_result: str) -> str:
        """截取工具结果生成简短的 Mock 回答片段。"""
        return f"（工具返回：{tool_result[:80]}）"

    @classmethod
    def _guess_args(cls, tool_name: str, text: str) -> dict[str, Any]:
        """根据工具名称生成可重复执行的最小参数集合。"""
        key, default = _ARGS_BY_TOOL.get(tool_name, ("query", "text"))
        value = text if default == "text" else default
        if key == "order_id":
            value = re.search(r"ORD\d+", text, re.IGNORECASE)
            value = value.group(0).upper() if value else default
        args = {key: value}
        if tool_name == "create_after_sales_case":
            args.update({"case_type": "退货", "description": text})
        return args
