# 可信工程基线实施计划

> 日期：2026-09-05  
> 依据：`2026-09-05-trustworthy-engineering-baseline-design.md`  
> 执行协作：Codex 负责 T-A 至 T-E；WorkBuddy 负责逐提交复核，并在 T-D 后执行 T-F/T-G  
> 说明：当前会话未提供 `writing-plans` 技能，本计划按相同的文件级、测试级和提交级标准手工编写。

## 1. 实施纪律

1. 开始子任务前在 `docs/TASK-LEDGER.md` 标为“进行中”并填写负责方。
2. 同一时刻只有一个 Agent 修改项目文件；另一方只读复核。
3. 每个子任务先补失败测试或验证脚本，再实现，再跑该任务测试与全量回归。
4. 每个子任务独立提交，提交正文包含 `[执行方: codex]` 或 `[执行方: 夜灯]`。
5. 每个提交完成后写 `docs/handoffs/YYYY-MM-DD-<执行方>-<task>.md`，交另一方复核。
6. 不提交 `.env`、真实 Key 或带 PII 的评测明细，不修改评测期望来抬高指标。

## 2. 已冻结的实现决策

- HNSW 和新增查询索引先声明在 ORM metadata，再固化到 Alembic；漂移检查不豁免应用索引。
- `alembic/env.py` 优先读取 `ALEMBIC_DATABASE_URL`，不存在时回落 `settings.database_url`。
- 初始迁移 `8fcb26067dd1` 改写为真实基线；应用路径彻底移除 `create_all`。
- 评测库在同一 PostgreSQL 实例中创建，创建动作连接 maintenance database `postgres` 并使用 AUTOCOMMIT。
- 新增 `sync_manifests` 属于只读同步元数据，加入评测保留白名单。
- 评测重置将所有非白名单表放入一条 `TRUNCATE ... RESTART IDENTITY CASCADE`；重置后只恢复这些表需要的运行基线。
- 售后确认场景的首轮与确认轮共同构成一条样本：意图取首轮 Agent state，工具调用取两轮并集，延迟取两轮端到端总和。
- 本地受管知识文档写入 `source="seed:local"`，`file_path` 保存相对 `kb_docs_dir` 的 POSIX 路径；孤儿清理只作用于该 source。
- CI 中基础设施错误数量大于 0，或样本异常率大于 10%，评测命令返回非零；指标不设“必须达到某准确率”的人为门槛。

## 3. T-A：真实 Alembic 初始迁移

### 3.1 先写验证

新增：

- `backend/tests/integration/test_migrations.py`
- `backend/scripts/check_migration_drift.py`
- `backend/scripts/check_seed_uniqueness.py`：持续验证所有自然冲突键，供本地与 CI 复用。
- `backend/app/models/sync.py`：先定义 `SyncManifest`，使其进入唯一且完整的初始结构基线。

测试职责：

1. 读取 `ALEMBIC_DATABASE_URL`，拒绝在未明确提供的数据库上运行破坏性迁移测试。
2. 执行 `upgrade head -> downgrade base -> upgrade head`。
3. 查询 `alembic_version`、24 张应用表（当前 23 张加 `sync_manifests`）、`vector` 扩展和 HNSW 索引。
4. 运行 Alembic `produce_migrations`，发现 upgrade operations 非空即失败。

首次运行应失败，因为当前迁移为空。

### 3.2 模型与迁移

修改：

- `backend/app/models/knowledge.py`
- `backend/app/models/sync.py`
- `backend/app/models/__init__.py`
- 必要时修改存在真实查询依据的其他模型文件
- `backend/alembic/env.py`
- `backend/alembic/versions/8fcb26067dd1_initial_schema.py`

操作：

1. 在 `KnowledgeChunk.__table_args__` 声明 HNSW cosine 索引。
2. 给 `KnowledgeChunk` 增加 `(document_id, chunk_index)` 唯一约束；给 `Price.variant_id`、`StoreProduct.sku` 和 `EvaluationItem.question` 增加经源数据唯一性验证后的唯一约束。`Price` 数据来自 `phone_specs.xlsx/variants`；该约束表达当前官方价一对一，历史价未来拆独立表。
3. 定义 `SyncManifest` 并注册模型，使初始迁移一次性包含 24 张表，后续任务不回改该迁移。
4. 在 Alembic env 注册 pgvector 类型、URL override、类型/default 比较。
5. 使用临时干净数据库 autogenerate 初始 DDL，人工复核表数、外键、默认值、Vector(1024) 和全部索引。
6. 补全 downgrade，逆序删除应用对象但保留 `vector` 扩展。
7. 将 `backend/scripts/init_db.py` 的 `create_all()` 替换为执行 `alembic upgrade head`，保证 T-A 提交单独检出时原初始化命令仍可运行。

### 3.3 验证与提交

运行：

```powershell
docker compose exec -T api pytest -q
docker compose exec -T -e ALEMBIC_DATABASE_URL=<临时测试库URL> api pytest -q tests/integration/test_migrations.py
docker compose exec -T -e ALEMBIC_DATABASE_URL=<临时测试库URL> api python scripts/check_migration_drift.py
```

提交：

```text
feat(db): establish real Alembic baseline migration

[执行方: codex]
```

完成后把 T-A 标为“待复核”，写交接记录；WorkBuddy 重点复核 migration upgrade/downgrade 对称性和漂移结果。

## 4. T-B：幂等种子与知识同步

### 4.1 模型与服务拆分

新增：

- `backend/app/services/seed_sync.py`：xlsx 校验、哈希、upsert、reset 和后置校验。
- `backend/app/services/kb_sync.py`：知识版本键、替换和孤儿清理编排。
- `backend/scripts/sync_data.py`：CLI，仅解析参数和调用服务。
- `backend/tests/test_seed_sync.py`
- `backend/tests/test_kb_sync.py`

修改：

- `backend/app/core/rag/embedding.py`
- `backend/app/core/rag/ingest.py`
- `backend/app/core/rag/chunker.py`（仅在需要暴露稳定配置时）
- `SyncManifest` 已在 T-A 纳入初始基线；T-B 只实现其读写服务，不回改已提交迁移。完成后仍重跑 T-A 三连和漂移检查。

### 4.2 种子同步

1. 将现有 Excel 解析和完整性校验从 `init_db.py` 移入 `seed_sync.py`。
2. 计算按规范路径排序后的 xlsx SHA-256、同步器版本和 schema revision 组合指纹。
3. 哈希未变且 manifest 状态成功时返回 `skipped=True`。
4. 哈希变化时按外键拓扑用 PostgreSQL `insert().on_conflict_do_update()` 写入。
5. 已验证冲突键：`phone_specs.xlsx/variants` 的 `prices.variant_id`、`business_data.xlsx/store_products` 的 `store_products.sku`、`evaluation_dataset.xlsx/evaluation` 的 `evaluation_dataset.id`，其余表使用既有业务主键或组合主键；`check_seed_uniqueness.py` 持续检查，禁止以不可靠字段临时拼键。
6. `users` 没有直接工作表来源：保留现有逻辑，从 orders/after-sales 的 `user_id` 派生消费者，去重后 upsert 用户、角色与 `user_roles`；该路径独立于通用 xlsx 表导入器。
6. 单事务包含业务 upsert、后置验证和 manifest 更新；失败整体回滚。
7. `--reset` 显式清空受管种子表并重新同步，默认模式不删除运行期业务数据。

### 4.3 知识同步

1. `EmbeddingProvider` 增加只读 `model_name` 与 `dim` 契约；Mock 返回 `mock-hash-v1/1024`，远程返回配置模型与配置维度。
2. 切分配置稳定 JSON 序列化后取 SHA-256，包含 size、overlap、separator/version。
3. 使用规范化相对路径定位文档，不再使用内容哈希生成会随内容变化的业务身份。
4. 四维版本键相同则跳过；不同则删除旧 chunks、更新文档、重新嵌入。
5. 仅清理 `source="seed:local"` 且相对路径已不在源目录中的文档。
6. 后台上传或其他 source 的文档永不进入本地目录孤儿清理。

### 4.4 测试与提交

重点测试：两次同步不增行、xlsx 字段修改触发更新、失败回滚、reset 恢复基线、四维版本键逐项变化、孤儿清理边界、真实 embedding 名不再被写为 mock。

提交：

```text
feat(seed): add idempotent seed and knowledge synchronization

[执行方: codex]
```

## 5. T-C：双数据库自动初始化

### 5.1 配置和创建数据库

新增/修改：

- `backend/app/config.py`：`eval_database_url`，不提供危险默认回落。
- `.env.example`：新增 `EVAL_DATABASE_URL`、`ALEMBIC_DATABASE_URL` 使用说明。
- `backend/scripts/bootstrap.py`：创建评测库、迁移双库、同步双库、后置校验。
- `docker-compose.yml`：新增一次性 `init` 服务，API 依赖其成功完成。
- `backend/tests/test_database_safety.py`

`bootstrap.py` 从主库 URL 推导 maintenance URL，仅保留服务地址与凭据、database 改为 `postgres`；使用 SQLAlchemy AUTOCOMMIT 创建经过标识符校验的评测库。数据库已存在视为成功，其他错误直接失败。

### 5.2 Compose 启动顺序

`init` 与 API 使用同一镜像和代码挂载，依赖 PostgreSQL/Redis healthy。顺序为：

1. 确保评测库存在；
2. 分别设置 `ALEMBIC_DATABASE_URL` 执行两个库的 `alembic upgrade head`；
3. 分别使用显式 database URL 运行内容同步；
4. 运行关键计数与引用后置校验；
5. 成功退出后 API 启动。

禁止通过修改全局缓存 `settings` 在同一进程切库；数据库 URL 必须显式传入 service/engine factory。

### 5.3 干净环境验收

```powershell
docker compose down -v
docker compose up -d --build
docker compose ps -a
curl.exe -f http://localhost:8000/api/v1/health
curl.exe -f http://localhost:5173
docker compose up -d
```

验收第二次启动走哈希快速路径，表计数不变。提交：

```text
feat(deploy): initialize databases before API startup

[执行方: codex]
```

## 6. T-D：可信自动评测

### 6.1 评测配置与重置

新增：

- `backend/eval/database.py`：URL 防呆、专用 engine、基线重置。
- `backend/eval/reporting.py`：环境指纹、JSON/Markdown 报告。
- `backend/eval/identity.py`：按样本解析 owner/non-owner/角色身份。
- `backend/tests/test_eval_database.py`
- `backend/tests/test_eval_reporting.py`

修改：

- `backend/eval/run_eval.py`
- `backend/app/api/routes/eval.py`
- 评测 xlsx 只在发现身份字段无法从现有列确定时增加新列；不得修改期望答案以提高分数。

防呆比较规范化后的 host、port、username 和 database，并连接后读取 `current_database()` 二次验证。主库、与主库同名、命名不符合 `_eval` 后缀的 URL 全部拒绝。

基线保留表为设计文档的 14 张表加 `sync_manifests`。由 `Base.metadata.sorted_tables` 枚举其余表，安全引用标识符后合并成一条 `TRUNCATE ... RESTART IDENTITY CASCADE`。

### 6.2 单样本执行

1. 根据样本意图与订单号选择真实种子 owner；越权样本使用持有其他订单的 non-owner；角色越权使用 consumer。
2. 从第一轮 `run_turn` 开始计时，读取其 `intent`，不再旁路调用 LLM。
3. 普通样本记录最终 state；确认写样本把首轮 `pending_tool_call` 传入第二轮，并设置 `confirmation_granted=True`。
4. 两轮视为一条样本：工具结果合并，端到端时间相加，意图使用首轮值。
5. 每条使用独立 session ID；完成后 commit 评测 trace/写操作，确保测试的是真实持久化路径。
6. 单条异常记录 `error_type` 和脱敏 `error_message`，回滚当前 session 后继续。

### 6.3 指标与报告

指标明确报告 `total/succeeded/failed`。分母默认使用全部样本；另提供成功样本诊断值但不作为 README 主指标。延迟对失败样本单列，不混入成功 P50/P95。

报告写入仓库根目录 `eval/reports/`，完整字段按设计文档执行。Git commit 通过 `git rev-parse HEAD` 获取，获取失败标记 `unknown` 而不中断；eval set hash 使用原始 xlsx SHA-256。

CLI 支持 `--limit`、`--output-dir`、`--fail-on-errors`。API 触发复用同一 runner，但生产请求不得接收任意 database URL。

提交拆分：

```text
fix(eval): isolate evaluation and use agent state metrics

[执行方: codex]
```

```text
feat(eval): persist reproducible evaluation reports

[执行方: codex]
```

## 7. T-E：GitHub Actions CI

新增：

- `.github/workflows/ci.yml`
- 必要的 `backend/tests/integration/conftest.py`

工作流使用 Python 3.12、pgvector PostgreSQL service 和 Redis service，按顺序执行：

1. 安装后端依赖；
2. 创建主测试库和评测库；
3. 迁移三连；
4. 漂移检查；
5. 种子同步两次及后置验证；
6. 全量 pytest；
7. 100 条 Mock 评测；
8. 校验 JSON/Markdown 报告环境指纹；
9. 把 Markdown 摘要写入 GitHub job summary，并上传报告 artifact。

CI 不使用真实 DeepSeek Key。工作流语法先用本地解析器校验；真正的绿色状态必须以推送后 GitHub Actions 结果为准，本地不能声称已经通过远程 CI。

提交：

```text
ci: verify migrations seed data and mock evaluation

[执行方: codex]
```

## 8. T-F/T-G：展示与技术决策文档

T-D 完成后由 WorkBuddy 认领：

- T-F 更新 README Mermaid 架构图、一键启动说明、Mock/DeepSeek 指标口径和截图占位；真实 DeepSeek 报告未生成前不得填写真实指标。
- T-G 编写架构、RAG、安全、评测四章技术决策，引用真实文件和报告。

Codex 对 T-F/T-G 只做代码事实复核，并运行 README 中全部命令验证可执行性。截图和文档不得先写 SSE、20 并发或云部署等未完成能力。

## 9. 阶段结束验收

最终执行：

```powershell
docker compose down -v
docker compose up -d --build
docker compose exec -T api pytest -q
docker compose exec -T api python -m eval.run_eval --fail-on-errors
docker compose ps -a
```

检查主库/评测库均为 Alembic head、API/前端 HTTP 200、初始化第二次跳过未变化内容、100 条报告落盘且不含密钥。随后由用户明确决定是否运行会产生 DeepSeek 费用的 100 条真实评测。
