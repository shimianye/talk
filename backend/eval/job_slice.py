"""Fixed, stratified evaluation slice for portfolio evidence."""
from __future__ import annotations

import hashlib
import json
from typing import Any


# Fixed before the real-model run. The selection spans specs, comparisons,
# recommendations, policy, orders/inventory, complaints, refusal and handoff.
JOB_SIGNAL_EVAL_IDS = (
    1, 8, 16,
    31, 38, 50,
    51, 54, 59,
    66, 69, 74, 75,
    81, 83, 85, 88, 90,
    91, 92, 93, 96, 99, 100,
)


def select_job_slice(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the fixed 24 cases in declared order and fail if the dataset drifted."""
    by_id = {int(item["id"]): item for item in items}
    missing = [item_id for item_id in JOB_SIGNAL_EVAL_IDS if item_id not in by_id]
    if missing:
        raise ValueError(f"求职评测切片缺少样本 ID: {missing}")
    return [by_id[item_id] for item_id in JOB_SIGNAL_EVAL_IDS]


def job_slice_hash(items: list[dict[str, Any]]) -> str:
    """Hash the selected case content so later reports can prove the slice was fixed."""
    encoded = json.dumps(items, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
