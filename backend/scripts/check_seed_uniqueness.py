"""验证种子文件中用于 upsert 的自然键保持唯一。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def _column_values(filename: str, sheet: str, column: str) -> list[Any]:
    """读取指定工作表列，并确保表头存在。"""
    workbook = openpyxl.load_workbook(
        DATA_DIR / filename, read_only=True, data_only=True
    )
    try:
        worksheet = workbook[sheet]
        rows = worksheet.iter_rows(values_only=True)
        header = tuple(next(rows))
        if column not in header:
            raise ValueError(f"{filename}/{sheet} 缺少列 {column}")
        index = header.index(column)
        return [row[index] for row in rows]
    finally:
        workbook.close()


def _assert_unique(filename: str, sheet: str, column: str) -> int:
    """断言列值非空且唯一，返回记录数。"""
    values = _column_values(filename, sheet, column)
    if any(value is None or str(value).strip() == "" for value in values):
        raise ValueError(f"{filename}/{sheet}.{column} 包含空值")
    if len(values) != len(set(values)):
        raise ValueError(f"{filename}/{sheet}.{column} 存在重复值")
    return len(values)


def main() -> None:
    """持续验证已选定的自然冲突键和库存一对多语义。"""
    checks = (
        ("phone_specs.xlsx", "variants", "variant_id"),
        ("business_data.xlsx", "store_products", "sku"),
        ("evaluation_dataset.xlsx", "evaluation", "id"),
        ("evaluation_dataset.xlsx", "evaluation", "question"),
    )
    for filename, sheet, column in checks:
        count = _assert_unique(filename, sheet, column)
        print(f"OK {filename}/{sheet}.{column}: {count} 个唯一值")

    inventory_variants = _column_values(
        "business_data.xlsx", "inventory", "variant_id"
    )
    if len(set(inventory_variants)) == len(inventory_variants):
        raise ValueError("inventory.variant_id 应允许一个 SKU 对应多个仓库")
    print("OK inventory.variant_id 保持仓库维度的一对多关系")


if __name__ == "__main__":
    main()
