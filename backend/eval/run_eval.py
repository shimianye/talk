"""可信自动评测 runner：独立评测库、真实 Agent state 和可追溯错误。"""
from __future__ import annotations

import asyncio
import argparse
from collections import Counter
import re
import sys
import time
from pathlib import Path
from typing import Any

import openpyxl
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import settings
from app.core.agent.graph import run_turn
from app.core.tools import registry
from app.core.tools.base import ToolContext
from app.services.seed_sync import sync_seed_data
from eval.database import create_eval_engine, reset_eval_runtime_state, verify_eval_connection
from eval.identity import identity_for_item, owner_isolation_pair
from eval.job_slice import JOB_SIGNAL_EVAL_IDS, job_slice_hash, select_job_slice
from eval.reporting import build_environment_fingerprint, persist_report

EVAL_XLSX = Path(__file__).resolve().parents[2] / "data" / "seed" / "evaluation_dataset.xlsx"
REPORT_DIR = Path(__file__).resolve().parent / "reports"
_TOOL_ALIAS = {"query_promotion": "query_price", "create_after_sales": "create_after_sales_case"}


def load_eval_items(path: Path | None = None) -> list[dict[str, Any]]:
    """只读加载评测工作表，不修改评测集结构或内容。"""
    workbook = openpyxl.load_workbook(path or EVAL_XLSX, read_only=True, data_only=True)
    try:
        rows = workbook["evaluation"].iter_rows(values_only=True)
        header = next(rows)
        return [{h: value for h, value in zip(header, row)} for row in rows]
    finally:
        workbook.close()


def _called_tools(state: dict[str, Any]) -> list[str]:
    """从 Agent 最终状态提取实际执行的工具名。"""
    return [r.get("tool") for r in state.get("tool_results", []) if r.get("tool")]


def _safe_error_message(exc: Exception) -> str:
    """移除 URL 凭据和 Bearer token 后生成单行错误摘要。"""
    message = re.sub(r"[\r\n]+", " ", str(exc))
    message = re.sub(r"(://)[^:/\s]+:[^@\s]+@", r"\1***:***@", message)
    message = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._-]+", r"\1***", message)
    return message[:240]


async def _run_item(session, item: dict[str, Any]) -> dict[str, Any]:
    """执行单条评测；确认写操作的第二轮与首轮合并。"""
    identity = await identity_for_item(session, item)
    started = time.perf_counter()
    states = [await run_turn(
        messages=[{"role": "user", "content": str(item["question"])}],
        user_id=identity.user_id, role=identity.role,
        session_id=f"eval-{item['id']}-{time.time_ns()}", db=session,
    )]
    first = states[0]
    if first.get("pending_confirmation") and first.get("pending_tool_call"):
        states.append(await run_turn(
            messages=[{"role": "user", "content": "确认"}], user_id=identity.user_id,
            role=identity.role, session_id=first.get("session_id"), db=session,
            confirmation_granted=True, pending_tool_call=first.get("pending_tool_call"),
        ))
    final = states[-1]
    called_tools = list(dict.fromkeys(tool for state in states for tool in _called_tools(state)))
    return {
        "id": item["id"], "category": item["category"],
        "expected_intent": item["intent"], "actual_intent": first.get("intent", "unknown"),
        "expected_tool": item["expected_tool_name"], "called_tools": called_tools,
        "should_transfer": item["should_transfer_human"], "handoff": bool(final.get("handoff_required")),
        "expected_route": item["expected_route"], "blocked": "blocked" in final.get("guardrail_flags", []),
        "has_answer": bool(final.get("final_answer")), "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "rounds": len(states), "identity_bound": identity.participates_in_owner_metric,
    }


async def _run_owner_isolation_probe(session) -> dict[str, int]:
    """直接调用订单工具验证 owner 可查和 non-owner 在 SQL/工具层被拦截。"""
    order_id, owner, non_owner = await owner_isolation_pair(session)
    tool = registry.get("query_order")
    if tool is None:
        raise RuntimeError("query_order 工具未注册")
    owner_result = await tool.execute(
        ToolContext(user_id=owner, role="consumer", db=session), order_id=order_id
    )
    non_owner_result = await tool.execute(
        ToolContext(user_id=non_owner, role="consumer", db=session), order_id=order_id
    )
    owner_passed = int(owner_result.success)
    non_owner_blocked = int(
        not non_owner_result.success and "无权" in (non_owner_result.error or "")
    )
    return {
        "owner通过数": owner_passed,
        "non_owner拦截数": non_owner_blocked,
        "混合错误数": int(not owner_passed or not non_owner_blocked),
    }


async def run_evaluation(
    db: Any = None,
    limit: int | None = None,
    *,
    output_dir: Path | None = None,
    job_slice: bool = False,
) -> dict[str, Any]:
    """在评测库运行 Agent 图并落盘双格式报告；传入 db 仅用于受控测试。"""
    items = load_eval_items()
    if job_slice:
        items = select_job_slice(items)
    if limit is not None:
        items = items[:limit]
    engine = None
    if db is None:
        engine = create_eval_engine()
        from sqlalchemy.ext.asyncio import async_sessionmaker
        session = async_sessionmaker(engine, expire_on_commit=False)()
    else:
        session = db
    errors: list[dict[str, Any]] = []
    per_item: list[dict[str, Any]] = []
    try:
        database_name = await verify_eval_connection(session)
        alembic_revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        await reset_eval_runtime_state(session)
        # reset 会清理订单等运行表；复用 T-B 同步服务恢复受控种子基线。
        await sync_seed_data(session)
        await session.commit()
        isolation = await _run_owner_isolation_probe(session)
        for item in items:
            try:
                per_item.append(await _run_item(session, item))
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                await session.rollback()
                errors.append({"id": item.get("id"), "error_type": type(exc).__name__,
                               "error_message": _safe_error_message(exc)})
        result = compute_metrics(per_item, items, errors)
        result["owner_isolation"].update(isolation)
        result["execution"] = {
            "one_round_samples": sum(r["rounds"] == 1 for r in per_item),
            "two_round_samples": sum(r["rounds"] == 2 for r in per_item),
        }
        result["category_distribution"] = dict(Counter(str(item["category"]) for item in items))
        result["environment"] = build_environment_fingerprint(
            EVAL_XLSX, database_name, str(alembic_revision or "unknown")
        )
        result["environment"].update({
            "eval_scope": "job-slice-24" if job_slice else "full",
            "eval_item_ids": list(JOB_SIGNAL_EVAL_IDS) if job_slice else "all",
            "eval_slice_hash": job_slice_hash(items),
        })
        result["report_paths"] = [str(path) for path in persist_report(result, output_dir or REPORT_DIR)]
        return result
    finally:
        if engine is not None:
            await engine.dispose()


def compute_metrics(per_item: list[dict], items: list[dict], errors: list[dict] | None = None) -> dict[str, Any]:
    """按全部样本为分母计算指标，并单列失败与身份隔离统计。"""
    errors = errors or []
    n = len(items) or 1
    tool_rows = [r for r in per_item if r["expected_tool"] not in ("无", None)]
    transfer_rows = [r for r in per_item if r["should_transfer"] == "是"]
    refuse_rows = [r for r in per_item if r["expected_route"] in ("拒答", "人工")]
    owner_rows = [r for r in per_item if r.get("identity_bound")]
    latencies = sorted(r["latency_ms"] for r in per_item)
    return {
        "total": len(items), "succeeded": len(per_item), "failed": len(errors),
        "metrics": {
            "意图准确率": round(sum(r["actual_intent"] == r["expected_intent"] for r in per_item) / n, 4),
            "工具选择准确率": round(sum(_TOOL_ALIAS.get(r["expected_tool"], r["expected_tool"]) in r["called_tools"] for r in tool_rows) / len(tool_rows), 4) if tool_rows else None,
            "转人工准确率": round(sum(r["handoff"] for r in transfer_rows) / len(transfer_rows), 4) if transfer_rows else None,
            "拒答/拦截率": round(sum(r["blocked"] or r["handoff"] for r in refuse_rows) / len(refuse_rows), 4) if refuse_rows else None,
            "答案产出率": round(sum(r["has_answer"] for r in per_item) / n, 4),
            "P50延迟(ms)": latencies[len(latencies) // 2] if latencies else 0,
            "P95延迟(ms)": latencies[min(int(len(latencies) * .95), len(latencies) - 1)] if latencies else 0,
            "平均工具调用数": round(sum(len(r["called_tools"]) for r in per_item) / (len(per_item) or 1), 2),
        },
        "owner_isolation": {"身份绑定样本数": len(owner_rows), "owner通过数": 0, "non_owner拦截数": 0, "混合错误数": 0},
        "errors": errors, "detail": per_item,
    }


async def main() -> None:
    """CLI 入口：解析范围、输出位置和错误退出策略。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--job-slice", action="store_true", help="运行固定的 24 条求职评测切片")
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--fail-on-errors", action="store_true")
    args = parser.parse_args()
    result = await run_evaluation(limit=args.limit, output_dir=args.output_dir, job_slice=args.job_slice)
    print(f"评测完成：{result['succeeded']}/{result['total']} 成功，报告：{result['report_paths']}")
    if args.fail_on_errors and result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
