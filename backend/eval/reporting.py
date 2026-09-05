"""自动评测结果的环境指纹与 JSON/Markdown 持久化。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.llm.factory import get_llm_client
from app.core.rag.embedding import get_embedding_provider


def _git_commit() -> str:
    """读取当前提交 SHA；非 Git 环境返回可解释的 unknown。"""
    explicit = os.getenv("GIT_COMMIT", "").strip()
    if explicit:
        return explicit
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            check=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    for git_dir in (Path(__file__).resolve().parents[2] / ".git", Path("/repo/.git")):
        head = git_dir / "HEAD"
        if not head.is_file():
            continue
        value = head.read_text(encoding="ascii").strip()
        if not value.startswith("ref: "):
            return value
        reference = value.removeprefix("ref: ")
        ref_path = git_dir / reference
        if ref_path.is_file():
            return ref_path.read_text(encoding="ascii").strip()
        packed_refs = git_dir / "packed-refs"
        if packed_refs.is_file():
            for line in packed_refs.read_text(encoding="ascii").splitlines():
                if line and not line.startswith(("#", "^")):
                    commit, ref = line.split(" ", 1)
                    if ref == reference:
                        return commit
    return "unknown"


def build_environment_fingerprint(
    eval_xlsx: Path, database_name: str | None, alembic_revision: str | None,
) -> dict[str, Any]:
    """生成不含密钥和 PII 的可复现环境指纹。"""
    llm = get_llm_client()
    embedding = get_embedding_provider()
    llm_provider = "deepseek" if llm.__class__.__name__ == "DeepSeekClient" else "mock"
    return {
        "git_commit": _git_commit(),
        "llm_provider": llm_provider,
        "llm_model": settings.deepseek_model if llm_provider == "deepseek" else "mock",
        "embedding_provider": settings.embedding_provider if settings.embedding_provider != "mock" else "mock",
        "embedding_model": embedding.model_name,
        "embedding_dim": embedding.dim,
        "database_name": database_name or "unknown",
        "alembic_revision": alembic_revision or "unknown",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "eval_set_hash": hashlib.sha256(eval_xlsx.read_bytes()).hexdigest(),
    }


def _markdown(result: dict[str, Any]) -> str:
    """将聚合指标和失败摘要渲染为招聘评审可读的 Markdown。"""
    metrics = result.get("metrics", {})
    lines = ["# 自动评测报告", "", f"- 样本总数：{result.get('total', 0)}",
             f"- 成功：{result.get('succeeded', 0)}", f"- 失败：{result.get('failed', 0)}", "",
             "## 环境指纹", ""]
    for key, value in result.get("environment", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## 指标", "", "| 指标 | 值 |", "|---|---:|"])
    lines.extend(f"| {key} | {value} |" for key, value in metrics.items())
    owner = result.get("owner_isolation", {})
    if owner:
        lines.extend(["", "## Owner 隔离", "", "| 指标 | 值 |", "|---|---:|"])
        lines.extend(f"| {key} | {value} |" for key, value in owner.items())
    execution = result.get("execution", {})
    if execution:
        lines.extend(["", "## 执行轮次", "", "| 类型 | 样本数 |", "|---|---:|"])
        lines.extend(f"| {key} | {value} |" for key, value in execution.items())
    categories = result.get("category_distribution", {})
    if categories:
        lines.extend(["", "## 类别分布", "", "| 类别 | 样本数 |", "|---|---:|"])
        lines.extend(f"| {key} | {value} |" for key, value in categories.items())
    errors = result.get("errors", [])
    if errors:
        lines.extend(["", "## 失败摘要", ""])
        lines.extend(f"- 样本 `{item.get('id')}`：{item.get('error_type')} - {item.get('error_message')}" for item in errors)
    return "\n".join(lines) + "\n"


def persist_report(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """按 UTC 时间戳同时写入机器可读 JSON 与 Markdown 报告。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    json_path = output_dir / f"eval-{stamp}.json"
    markdown_path = output_dir / f"eval-{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(result), encoding="utf-8")
    return json_path, markdown_path
