"""Locust 场景：对真实消费者 POST /api/v1/chat 做可重复压测。

默认使用 Mock LLM；DeepSeek 压测必须显式设置环境变量并单独运行。
"""
from __future__ import annotations

import os
import random
from typing import Any

from locust import HttpUser, between, task


QUESTIONS = [
    "iPhone 16 的处理器是什么？",
    "小米 15 现在多少钱？",
    "对比 iPhone 16 Pro 和 iPhone 15 Pro 的处理器和价格",
    "有没有适合拍照的手机？",
    "华为 Mate 70 支持无线充电吗？",
    "小米 14 还有 12GB+256GB 吗？",
    "我买的订单 ORD202609001 到哪里了？",
    "手机七天无理由退货怎么操作？",
    "我想查一下最近的促销活动",
    "预算 4000 元，推荐一款手机",
    "手机屏幕碎了可以维修吗？",
    "能查别人的订单吗？",
]


class PhoneCommerceUser(HttpUser):
    """模拟一个登录后的消费者，保持会话并随机发送业务问题。"""

    wait_time = between(1, 3)
    username = os.getenv("LOADTEST_USERNAME", "U6147")
    password = os.getenv("LOADTEST_PASSWORD", "password123")

    def on_start(self) -> None:
        """登录一次并保存 JWT；登录失败会让该虚拟用户停止发压。"""
        self.session_id: str | None = None
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": self.username, "password": self.password},
            name="POST /api/v1/auth/login",
        )
        if response.status_code != 200:
            response.failure(f"login failed: HTTP {response.status_code}")
            self.environment.runner.quit()  # type: ignore[union-attr]
            return
        body: dict[str, Any] = response.json()
        self.token = body["access_token"]

    @task
    def chat(self) -> None:
        """随机调用完整聊天链路并校验 JSON 响应包含答案。"""
        if not getattr(self, "token", None):
            return
        question = random.choice(QUESTIONS)
        with self.client.post(
            "/api/v1/chat",
            json={"message": question, "session_id": self.session_id},
            headers={"Authorization": f"Bearer {self.token}"},
            name="POST /api/v1/chat",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            body = response.json()
            self.session_id = body.get("session_id")
            if not body.get("answer"):
                response.failure("response answer is empty")

