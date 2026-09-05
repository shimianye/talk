# 可信工程基线设计

> 日期：2026-09-05  
> 项目：手机电商智能客服 Agent  
> 状态：已获用户与 WorkBuddy 批准，等待书面规格复核

## 1. 背景与目标

当前项目已经具备 FastAPI、LangGraph、PostgreSQL/pgvector、Redis、React、DeepSeek 和离线测试，但数据库结构仍由 `Base.metadata.create_all()` 创建，Alembic 初始迁移为空；Docker 启动后仍需手动初始化；评测入口未使用数据库会话、旁路重复判断意图、会污染业务数据且结果不落盘。这些问题使运行结果难以复现，也无法为简历指标提供可靠证据。

本阶段建立一条可验证的工程基线：

1. Alembic 成为数据库结构的唯一真源，迁移可升级、回滚并检测模型漂移。
2. `docker compose up -d --build` 在干净环境中自动完成迁移和内容同步。
3. 种子和知识库同步可重复执行，内容变化能自动生效，未变化时走快速路径。
4. 自动评测使用独立数据库、真实种子身份和 Agent 最终状态，并生成可追溯报告。
5. CI 在全新 PostgreSQL/pgvector 与 Redis 环境中验证迁移、数据和 100 条 Mock 评测。

本阶段不实现前端 SSE 消费、并发压测、演示视频或云部署。这些工作在工程基线稳定后分别设计和提交。

## 2. 方案选择

采用“可信工程基线”方案。保留 `create_all` 的快速修补无法证明数据库演进能力；引入独立 PostgreSQL 服务、任务队列和对象存储的完整生产化方案超过当前企业级 MVP 与秋招准备所需范围。

现有空迁移 `8fcb26067dd1` 尚未作为有效结构版本发布，因此直接改写为真实初始迁移，保留 `down_revision = None`。不额外保留一个无 DDL 的历史版本。

## 3. 总体架构与启动流

```text
docker compose up
        |
        +--> postgres (healthy) ----+---- main database
        |                           +---- eval database
        +--> redis (healthy)
        |
        +--> init (one-shot)
                1. create eval database if absent
                2. alembic upgrade head on both databases
                3. sync main seed and knowledge data
                4. sync eval seed and knowledge data
                5. verify critical counts and references
                     |
                     +--> exit 0 --> api starts --> frontend available
                     +--> exit != 0 --> api remains blocked
```

`init` 是一次性 Compose 服务，每次 Compose 启动都会进入初始化入口，但迁移、种子和知识库各自具备幂等快速路径。API 依赖 `service_completed_successfully`，避免在半初始化数据库上提供服务。

数据库凭据继续由环境变量注入；`.env` 不进入版本控制。新增 `EVAL_DATABASE_URL`，默认指向同一 PostgreSQL 实例中的 `phone_commerce_eval`。

## 4. 数据库结构管理

### 4.1 Alembic 唯一真源

初始迁移负责：

- `CREATE EXTENSION IF NOT EXISTS vector`；
- 当前 23 张业务表及新增的 `sync_manifests` 同步元数据表、主键、外键、唯一约束和 server default；
- ORM `index=True` 已声明的 B-tree 索引；
- `knowledge_chunks.embedding` 的 HNSW `vector_cosine_ops` 索引；
- 与真实查询路径对应的必要时间或复合索引，新增前必须由查询语句证明用途。

所有应用表、约束和索引都必须先声明在 SQLAlchemy ORM metadata 中，再由 Alembic 初始迁移固化。HNSW 使用模型的 `__table_args__` 声明 `Index`，指定 `postgresql_using="hnsw"` 和 `vector_cosine_ops`；必要的时间或复合索引也遵循同一规则。禁止只在迁移里增加 metadata 不可见的应用索引，也不使用 `include_object` 将其排除在漂移检查之外。

`alembic/env.py` 导入 `pgvector.alembic`，在线和离线配置均启用 `compare_type=True` 与 `compare_server_default=True`。应用启动、测试和初始化脚本不再调用 `Base.metadata.create_all()`。

HNSW 是为未来规模化准备的结构能力，不宣称在当前 20 篇知识文档上产生性能收益。`downgrade()` 必须按依赖逆序删除 HNSW/B-tree 索引和全部应用表，但保留当前数据库中的 `vector` 扩展；扩展不属于应用数据，且可能被同库后续迁移复用。

### 4.2 迁移验证

在干净测试数据库执行固定三连：

```text
alembic upgrade head -> alembic downgrade base -> alembic upgrade head
```

随后运行漂移检查：基于当前 ORM metadata 执行 autogenerate 比对，若产生任何未预期 DDL，CI 失败。它验证 Alembic 结构与模型一致，但不自动生成或提交迁移。

## 5. 幂等内容同步

### 5.1 种子数据

结构迁移和内容同步拆分为独立职责。种子同步保留现有时间序和外键引用预校验，并遵循外键依赖顺序。

- 使用每张表的业务主键作为冲突键；关联表使用组合主键。
- `prices.variant_id` 表达“每个 SKU 只有一条当前官方指导价”的业务不变量；若未来支持历史价或分渠道价格，新增 `price_history` 等历史表，不放宽当前价唯一约束。
- 使用 PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`，不使用 ORM `merge()`。
- 一次同步使用单个事务，任何表失败则整批回滚。
- 计算所有种子 xlsx 的文件哈希与同步器版本，写入 manifest 表。
- 哈希与版本均未变化时跳过业务 upsert；变化时执行完整校验和 upsert。
- 默认同步不传播源文件删除，避免误删运行数据；显式 `--reset` 才按依赖顺序清空并重灌。

manifest 只用于快速判断，不是永久“已初始化”标记。迁移始终执行，内容改变后同步自动恢复。

### 5.2 知识库增量更新

保留现有 Markdown 解析与内容哈希机制，将文档版本键升级为：

```text
(content_hash, chunk_config_hash, embedding_model_name, embedding_dim)
```

`chunk_config_hash` 由稳定序列化后的切分参数计算，至少包含 chunk size、overlap、分隔策略和版本号。Embedding provider 对外暴露真实模型名与维度，移除 `mock-hash` 硬编码。

版本键未变化时复用文档和向量；任一字段变化时在同一事务中替换该文档的 chunks。同步结束后对源目录已删除的受管文档执行孤儿清理；仅清理带有本地种子来源标识的文档，避免误删后台上传内容。

## 6. 评测隔离与可复现性

### 6.1 独立数据库

评测使用同一 PostgreSQL 实例中的独立 database，而不是主库 schema 或长事务回滚。评测入口创建专用 engine/session factory，并在执行前同时校验：

- `EVAL_DATABASE_URL` 已设置；
- 解析后的 database 名与主库不同；
- database 名符合允许的评测库命名规则；
- 连接后的 `current_database()` 与配置一致。

防呆断言放在评测运行入口，而不是全局配置加载阶段，保证普通 API 启动不依赖评测库，同时所有 CLI/API 评测路径复用同一校验。

### 6.2 基线恢复白名单

每次评测前保留下列只读基线表：

`products`、`product_variants`、`prices`、`inventory`、`promotions`、`sources`、`store_products`、`knowledge_documents`、`knowledge_chunks`、`intent_taxonomy`、`users`、`roles`、`user_roles`、`evaluation_dataset`。

其余应用表默认清空并根据需要恢复种子数据。实现由 metadata 枚举全部表并减去白名单，新增表因此默认进入重置集合。知识向量不重复生成，除非四维版本键发生变化。

评测身份来自真实种子用户：owner 用于正常订单和售后查询；non-owner 用于他人订单归属拦截；另使用低权限身份验证角色越权。评测用例显式记录所需身份，不再统一使用不存在的 `eval-user`。

### 6.3 指标和错误语义

每条样本只运行一次完整 Agent 图：

1. 从开始运行前计时；
2. 调用 `run_turn`；
3. 从最终 `AgentState` 读取 `intent`、工具结果、转人工、安全标记和回答；
4. 捕获单条异常，记录错误类型与脱敏消息后继续；
5. 指标分母同时报告总样本数、成功执行数和失败数，避免异常被静默排除。

删除额外的 `llm.complete_json` 旁路调用。P50/P95 覆盖意图提取、工具循环、数据库访问和回答生成的完整 Agent 链路。写操作仍经过确认门控；需要验证实际写入的样本使用明确的评测确认阶段，并在下一轮基线恢复时清理。

### 6.4 报告

每次运行写入：

- `eval/reports/eval-<UTC timestamp>.json`：完整机器可读结果；
- 同名 `.md`：指标、失败摘要和类别分布。

报告包含以下环境指纹：

`git_commit`、`llm_provider`、`llm_model`、`embedding_provider`、`embedding_model`、`embedding_dim`、`database_name`、`run_at_utc`、`eval_set_hash`。

报告不包含 API Key、JWT、完整 PII 或数据库密码。代表性 Mock 与真实 DeepSeek 报告纳入版本控制，临时调试报告可忽略。

## 7. 错误处理与可观测性

- 迁移、种子校验或知识同步失败时，`init` 非零退出，API 不启动。
- 种子同步在单事务内回滚，并输出失败阶段、表名和不含敏感值的原因。
- 单篇知识文档更新失败时整次知识同步回滚，旧版本继续可用。
- 评测库防呆失败时拒绝执行，绝不降级到主库。
- 单条评测异常不终止批次；基础设施级错误数量大于 0，或样本异常率超过 10% 时，评测进程返回非零状态。
- CI 日志输出迁移版本、导入统计、评测摘要；不输出 `.env` 或密钥。

## 8. CI 验收矩阵

现有 26 个测试是纯单元测试，不覆盖数据库。CI 必须承担以下集成验收：

| 验收项 | 环境 | 失败条件 |
|---|---|---|
| 26 个单元测试 | Python 3.12 | 任一失败 |
| 迁移三连 | 干净 pgvector PostgreSQL | upgrade/downgrade 任一步失败 |
| ORM 漂移检查 | 三连后的数据库 | autogenerate 比对非空 |
| 幂等同步 | 连续执行两次 | 第二次失败、重复行或关键计数变化 |
| 数据后置校验 | 同步后的数据库 | 关键表计数、外键引用或订单时间序异常 |
| Mock 评测 | 独立 eval database + Redis | 未完成 100 条、基础设施错误或报告缺字段 |

CI 使用 GitHub Actions service containers 启动 pgvector PostgreSQL 和 Redis，不调用 DeepSeek，不读取真实密钥。工作流成功后 README 展示状态徽章。

## 9. 测试策略

除 CI 集成链路外，新增针对以下边界的自动测试：

- 种子哈希一致时走快速路径，文件变化时触发 upsert；
- 两次同步的关键表行数一致且更新字段生效；
- `--reset` 删除运行期数据并恢复种子基线；
- 四维知识版本键各字段变化均触发重嵌，未变化不调用 embedding；
- 已删除的受管知识文档被清理，后台文档不受影响；
- 主库 URL、别名主库 URL和不允许的库名均被评测防呆拒绝；
- owner、non-owner 和角色越权用例产生预期结果；
- 单条评测异常被记录，后续样本继续执行；
- JSON/Markdown 报告指标一致且环境指纹完整。

## 10. 交付与提交边界

实施按依赖顺序拆分，每组完成验证后单独提交：

1. `feat(db): establish real Alembic baseline migration`
2. `feat(seed): add idempotent seed and knowledge synchronization`
3. `feat(deploy): initialize databases before API startup`
4. `fix(eval): isolate evaluation database and align agent metrics`
5. `feat(eval): persist reproducible evaluation reports`
6. `ci: verify migrations seed data tests and mock evaluation`
7. `docs: document trustworthy engineering baseline`

不通过空提交或无意义拆分制造提交数量。每个提交应具备独立目的、对应测试和可审查差异。

## 11. 完成定义

本阶段只有在以下条件全部满足时完成：

- 删除数据卷后，仅执行 `docker compose up -d --build` 即可访问 API 和前端；
- 主库和评测库均处于 Alembic head，应用路径不存在 `create_all`；
- 迁移三连和 ORM 漂移检查通过；
- 初始化连续运行两次无重复数据，变更种子后能更新，知识版本变化能重嵌；
- 评测无法误连主库，100 条 Mock 样本跑完并产出完整报告；
- 现有 26 个测试和新增测试全部通过；
- GitHub Actions 工作流定义有效，推送后可在 GitHub 上验证为绿色；
- README 的启动方式、架构图和指标口径与实现一致。

真实 DeepSeek 100 条评测属于后续证据生成动作：工程链路完成后使用用户已配置的 Key 明确执行，报告真实标记 provider，不把 Mock 数字包装成真实模型指标。
