# T-N 交接：真实 BGE-M3 双库重建与全量复测

## 改动

- 将本地运行配置切换为 Ollama `bge-m3` 的 OpenAI 兼容接口（`.env` 未提交）。
- 修复 `bootstrap_databases` 跨多个事件循环复用 `RemoteEmbeddingProvider` 的问题。
- 通过 `asyncio.to_thread` 顺序执行 Alembic，避免其内部 `asyncio.run` 与 bootstrap 主循环嵌套。
- 新增事件循环与 Alembic 生命周期回归测试，并补齐 `.env.example` 的真实 Embedding 配置字段。
- 生成并纳入版本控制的真实栈报告：`backend/eval/reports/eval-20260910053147.{json,md}`。
- 更新 README、面试讲解卡与任务台账，明确 Agent 指标不等于 Embedding 检索正确率。

## 原因

Mock 哈希向量不会建立 HTTP 客户端，因此此前双库 bootstrap 的跨事件循环缺陷没有暴露。真实 `bge-m3` 接入后，主库同步结束会关闭所属循环，评测库复用客户端时触发 `Event loop is closed`；统一主循环后又暴露 Alembic 的嵌套循环约束，因此迁移需放到工作线程。

## 验证

- `docker compose run --rm --no-deps api pytest -q`：48 passed、3 skipped。
- `pca-init`：Exited (0)；`pca-api`：Running。
- API `/api/v1/health`：`deepseek/deepseek-chat`、`openai/bge-m3`。
- 主库 `phone_commerce`：20 文档、87/87 非空向量、`bge-m3:1024`、维度 1024。
- 评测库 `phone_commerce_eval`：20 文档、87/87 非空向量、`bge-m3:1024`、维度 1024。
- 全量评测：100/100 成功；意图 84/100、工具 2/9、转人工 1/5、拒答/拦截 1/6、答案产出 100/100、P50 4579.1ms、P95 10140.4ms。
- 环境指纹：commit `edfb399d2df783f2120d08b29ac19022df61e0de`，eval set hash `88836ef225fbc0bb6c6f3dfc49eaf7d4c064125580ad00eed4577136883adff2`。

## 遗留问题

- 现有评测集没有查询到相关文档的人工标签，不能计算 Recall@K、MRR 或 nDCG。
- 工具、转人工和安全动作指标偏低，应通过确定性映射和独立保留集修复，不能在当前 100 条上反复调参。

## 下一步

另立任务建设带 `relevant_document_ids` 的检索评测集，并在同一查询集上对比 Mock 哈希向量与 BGE-M3；Agent 动作指标与检索指标分别展示。
