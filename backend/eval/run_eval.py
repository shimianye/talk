"""评测运行器：离线可跑的自动化评测（Mock LLM，无需外部 Key）。

从 evaluation_dataset.xlsx 加载 100 条评测集，逐条跑 Agent 图，计算：
意图准确率、工具选择准确率、转人工准确率、拒答拦截率、答案产出率、
P50/P95 延迟、平均工具调用数。
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import openpyxl

from app.core.agent.graph import run_turn
from app.core.llm.factory import get_llm_client

EVAL_XLSX = Path(__file__).resolve().parents[2] / "data" / "seed" / "evaluation_dataset.xlsx"

# expected_tool_name 中的别名 → 实际工具名
_TOOL_ALIAS = {"query_promotion": "query_price", "create_after_sales": "create_after_sales_case"}


def load_eval_items(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or EVAL_XLSX
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    ws = wb["evaluation"]
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    items = []
    for r in rows:
        items.append({h: v for h, v in zip(header, r)})
    wb.close()
    return items


async def run_evaluation(db: Any = None, limit: int | None = None) -> dict:
    items = load_eval_items()
    if limit:
        items = items[:limit]

    llm = get_llm_client()
    latencies: list[float] = []
    tool_counts: list[int] = []
    per_item: list[dict] = []

    for item in items:
        q = item["question"]
        # 意图分类
        intent = (await llm.complete_json([{"role": "user", "content": q}])).get("intent", "unknown")

        t0 = time.perf_counter()
        state = await run_turn(
            messages=[{"role": "user", "content": q}],
            user_id="eval-user",
            role="consumer",
            session_id=f"eval-{item['id']}",
            db=db,
        )
        lat = (time.perf_counter() - t0) * 1000
        latencies.append(lat)

        called_tools = [
            r.get("tool") for r in state.get("tool_results", []) if r.get("tool")
        ]
        tool_counts.append(len(called_tools))
        final_answer = state.get("final_answer") or ""
        handoff = state.get("handoff_required", False)
        blocked = "blocked" in state.get("guardrail_flags", [])

        per_item.append(
            {
                "id": item["id"],
                "category": item["category"],
                "expected_intent": item["intent"],
                "actual_intent": intent,
                "expected_tool": item["expected_tool_name"],
                "called_tools": called_tools,
                "should_transfer": item["should_transfer_human"],
                "handoff": handoff,
                "expected_route": item["expected_route"],
                "blocked": blocked,
                "has_answer": bool(final_answer),
                "latency_ms": round(lat, 1),
            }
        )

    return compute_metrics(per_item, items)


def compute_metrics(per_item: list[dict], items: list[dict]) -> dict:
    n = len(per_item) or 1

    intent_ok = sum(
        1 for r in per_item if r["actual_intent"] == r["expected_intent"]
    )
    tool_ok = sum(
        1
        for r in per_item
        if r["expected_tool"] not in ("无", None)
        and _TOOL_ALIAS.get(r["expected_tool"], r["expected_tool"]) in r["called_tools"]
    )
    tool_total = sum(1 for r in per_item if r["expected_tool"] not in ("无", None))

    transfer_ok = sum(
        1 for r in per_item if r["should_transfer"] == "是" and r["handoff"]
    )
    transfer_total = sum(1 for r in per_item if r["should_transfer"] == "是")

    refuse_ok = sum(
        1
        for r in per_item
        if r["expected_route"] in ("拒答", "人工") and (r["blocked"] or r["handoff"])
    )
    refuse_total = sum(1 for r in per_item if r["expected_route"] in ("拒答", "人工"))

    answer_ok = sum(1 for r in per_item if r["has_answer"])

    latencies = sorted(r["latency_ms"] for r in per_item)
    p50 = latencies[int(len(latencies) * 0.5)] if latencies else 0
    p95 = latencies[min(int(len(latencies) * 0.95), len(latencies) - 1)] if latencies else 0
    avg_tools = round(sum(len(r["called_tools"]) for r in per_item) / n, 2)

    return {
        "total": len(per_item),
        "metrics": {
            "意图准确率": round(intent_ok / n, 4),
            "工具选择准确率": round(tool_ok / tool_total, 4) if tool_total else None,
            "转人工准确率": round(transfer_ok / transfer_total, 4) if transfer_total else None,
            "拒答/拦截率": round(refuse_ok / refuse_total, 4) if refuse_total else None,
            "答案产出率": round(answer_ok / n, 4),
            "P50延迟(ms)": round(p50, 1),
            "P95延迟(ms)": round(p95, 1),
            "平均工具调用数": avg_tools,
        },
        "detail": per_item,
    }


async def main() -> None:
    result = await run_evaluation(limit=None)
    print("=" * 50)
    print("评测完成，指标：")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
