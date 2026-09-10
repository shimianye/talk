# Real Embedding Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make main and evaluation database bootstrap share one event loop so a real `bge-m3` HTTP client can safely rebuild both vector stores, then publish a verified real-stack evaluation.

**Architecture:** Move the complete initialization sequence into `_bootstrap_database_contents`, invoked by one `asyncio.run`: ensure the evaluation database exists, run both Alembic migrations sequentially through `asyncio.to_thread` because Alembic owns an inner event loop, then asynchronously sync both databases on the main loop. Preserve the public `bootstrap_databases` signature and result shape.

**Tech Stack:** Python 3.12, asyncio, httpx, SQLAlchemy async, PostgreSQL/pgvector, Ollama `bge-m3`, DeepSeek Chat, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-10-real-embedding-bootstrap-design.md`

## Global Constraints

- Do not commit `.env` or credentials.
- Do not change the 100-case evaluation dataset or relax assertions.
- Embedding model is Ollama `bge-m3`, dimension 1024, accessed through `/v1/embeddings`.
- Existing `bootstrap_databases(main_url, eval_url, docs_dir, embedding, *, data_dir)` interface and return keys remain unchanged.
- Agent routing metrics must not be described as Recall@K, MRR, nDCG, or Embedding correctness.

---

### Task 1: Prove and fix the event-loop lifecycle

**Files:**
- Modify: `backend/tests/test_database_bootstrap.py`
- Modify: `backend/app/services/database_bootstrap.py`

**Interfaces:**
- Consumes: existing `ensure_database_exists`, `migrate_database`, and `sync_database` functions.
- Produces: `_bootstrap_database_contents(main_url: str, eval_url: str, docs_dir: Path, embedding: EmbeddingProvider, *, data_dir: Path) -> dict[str, Any]`; unchanged `bootstrap_databases(...) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing unit test**

Add a monkeypatched test that records `id(asyncio.get_running_loop())` in `ensure_database_exists` and both `sync_database` calls, invokes `bootstrap_databases`, and asserts one unique loop ID plus call order `ensure, migrate main, migrate eval, sync main, sync eval` and the unchanged result structure.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `docker compose run --rm --no-deps api pytest -q tests/test_database_bootstrap.py`

Expected before implementation: failure because the three async operations run in separate event loops.

- [ ] **Step 3: Implement the single-loop orchestration**

Add `_bootstrap_database_contents` that awaits `ensure_database_exists`, awaits `asyncio.to_thread(migrate_database, database_url)` for main and evaluation URLs, then awaits `sync_database` for both URLs in sequence. Change `bootstrap_databases` to call `asyncio.run(_bootstrap_database_contents(...))` exactly once.

- [ ] **Step 4: Run focused and full regression tests**

Run:

```powershell
docker compose run --rm --no-deps api pytest -q tests/test_database_bootstrap.py tests/test_sync.py
docker compose run --rm --no-deps api pytest -q
```

Expected: focused tests pass; full suite has no new failures.

- [ ] **Step 5: Commit the lifecycle fix**

```powershell
git add backend/app/services/database_bootstrap.py backend/tests/test_database_bootstrap.py
git commit -m "fix: share one event loop during database bootstrap`n`n[执行方: codex]"
```

### Task 2: Rebuild and verify real vectors

**Files:**
- Local only: `.env`
- Update: `docs/TASK-LEDGER.md`

**Interfaces:**
- Consumes: Ollama OpenAI-compatible endpoint at `http://host.docker.internal:11434`, model `bge-m3`.
- Produces: main and evaluation databases populated with 1024-dimensional real vectors and an API using `RemoteEmbeddingProvider`.

- [ ] **Step 1: Recreate init and API services**

Run: `docker compose up -d --force-recreate init api`

Expected: `pca-init` exits 0 and `pca-api` becomes healthy/running.

- [ ] **Step 2: Verify runtime provider and database metadata**

Run provider inspection inside `pca-api`, then query both databases for document/chunk counts, non-null vector counts, `embedding_model`, and `vector_dims(embedding)`.

Expected: each database has 20 documents, 87 chunks, all embeddings non-null, model `bge-m3`, dimension 1024.

- [ ] **Step 3: Record verification evidence**

Update the T-N row with exact verified counts and explicitly state that retrieval-quality metrics remain a separate benchmark.

### Task 3: Run and publish the real-stack evaluation

**Files:**
- Generate: `backend/eval/reports/eval-<timestamp>.json`
- Generate: `backend/eval/reports/eval-<timestamp>.md`
- Modify: `README.md`
- Modify: `docs/INTERVIEW-GUIDE.md`
- Modify: `docs/TASK-LEDGER.md`
- Modify/Create: `docs/handoffs/2026-09-10-codex.md`

**Interfaces:**
- Consumes: fixed 100-case evaluation dataset, DeepSeek `deepseek-chat`, real `bge-m3` vectors.
- Produces: timestamped report whose environment fingerprint names both real models and documentation linked to the report.

- [ ] **Step 1: Execute all 100 cases**

Run: `docker compose exec api python -m eval.run_eval`

Expected: 100 results written with `failed_cases = 0`; metric values are accepted as observed and never backfilled.

- [ ] **Step 2: Verify the report**

Check case count, failed case count, LLM provider/model, Embedding provider/model, dataset hash, commit hash, and metric numerators/denominators in both JSON and Markdown.

- [ ] **Step 3: Update portfolio evidence**

Make the new report the primary README and interview-guide evidence. State that it validates a real LLM + real Embedding runtime, while the reported accuracy remains Agent routing/tool/safety accuracy rather than retrieval relevance.

- [ ] **Step 4: Run documentation and secret checks**

Run `git diff --check`, search staged/generated files for credential patterns, and confirm `.env` is untracked/ignored.

- [ ] **Step 5: Commit and push**

Force-add the ignored generated report files, commit documentation/evidence with the executor tag, push `main`, and verify local `HEAD` equals `origin/main`.
