"""工具通用辅助函数。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _jsonify(value: Any) -> Any:
    """将日期和 Decimal 等数据库值转换为 JSON 原生类型。"""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize(obj: Any) -> Any:
    """将 ORM 实例 / 列表 / 标量 转为 JSON 可序列化结构。"""
    if obj is None:
        return None
    if hasattr(obj, "__table__"):  # SQLAlchemy 模型实例
        return {c.name: _jsonify(getattr(obj, c.name)) for c in obj.__table__.columns}
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize(x) for x in obj]
    return _jsonify(obj)
