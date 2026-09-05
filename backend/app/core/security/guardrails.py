"""安全护栏：输入注入检查、工具结果 PII/注入检查、输出敏感承诺检查与脱敏。

对齐设计文档第 9 章安全链路。
"""
from __future__ import annotations

import re
from typing import Any

# 输入注入特征（提示词注入 / 越权试探）
_INJECTION_PATTERNS = (
    "忽略以上",
    "ignore previous",
    "ignore above",
    "系统提示词",
    "system prompt",
    "输出你的指令",
    "reveal your instructions",
    "假装你是",
    "act as",
    "jailbreak",
    "不要遵守",
)

# 敏感承诺：Agent 不应未经授权自动承诺
_SENSITIVE_COMMITMENTS = (
    "无条件退款",
    "双倍赔偿",
    "全额赔偿",
    "现金赔偿",
    "保证免费",
    "一定退差价",
)

_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")


def check_input_injection(text: str) -> list[str]:
    """输入注入检查。"""
    flags: list[str] = []
    low = (text or "").lower()
    for p in _INJECTION_PATTERNS:
        if p.lower() in low:
            flags.append("injection_attempt")
            break
    return flags


def _find_pii(text: str) -> list[str]:
    """返回文本中检测到的手机号和身份证类型；不返回原始敏感值。"""
    found: list[str] = []
    if _PHONE_RE.search(text):
        found.append("phone")
    if _ID_RE.search(text):
        found.append("id_card")
    return found


def check_and_mask_pii(text: str) -> tuple[str, list[str]]:
    """工具结果脱敏：检测并掩码手机号/身份证。返回 (脱敏后文本, 命中的类型)。"""
    types: list[str] = []
    if _PHONE_RE.search(text):
        types.append("phone")
    if _ID_RE.search(text):
        types.append("id_card")
    masked = _PHONE_RE.sub(lambda m: m.group()[:3] + "****" + m.group()[-4:], text)
    masked = _ID_RE.sub(lambda m: m.group()[:6] + "********" + m.group()[-4:], masked)
    return masked, types


def check_output_commitments(text: str) -> list[str]:
    """输出敏感承诺检查。"""
    flags: list[str] = []
    for c in _SENSITIVE_COMMITMENTS:
        if c in (text or ""):
            flags.append("sensitive_commitment")
            break
    return flags


def redact_data(data: Any) -> Any:
    """递归脱敏（返回脱敏后数据）。"""
    redacted, _ = redact_recursive(data)
    return redacted


def redact_recursive(data: Any) -> tuple[Any, bool]:
    """递归脱敏，返回 (脱敏后数据, 是否命中 PII)。"""
    found = False

    def rec(x: Any) -> Any:
        """递归遍历字符串、字典和列表并更新命中标记。"""
        nonlocal found
        if isinstance(x, str):
            masked, hit = check_and_mask_pii(x)
            if hit:
                found = True
            return masked
        if isinstance(x, dict):
            return {k: rec(v) for k, v in x.items()}
        if isinstance(x, list):
            return [rec(v) for v in x]
        return x

    return rec(data), found
