# 真实 Embedding 双库初始化修复设计

## 背景与目标

项目已将 Embedding Provider 从 Mock 切换为本机 Ollama `bge-m3`，通过 OpenAI 兼容的 `/v1/embeddings` 接口生成 1024 维向量。现有 `bootstrap_databases` 使用多次 `asyncio.run` 分别同步主库和评测库，却复用同一个持有 `httpx.AsyncClient` 的 `RemoteEmbeddingProvider`，导致第二次同步跨事件循环使用客户端并抛出 `RuntimeError: Event loop is closed`。

本次目标是让主库与评测库可在一次初始化中可靠完成真实向量重建，并用真实 DeepSeek + BGE-M3 重新运行全量评测。范围不包括修改评测集、调整业务路由或虚构检索指标。

## 方案选择

采用方案 A：由一个顶层异步编排函数依次完成评测库存在性检查、双库迁移、主库同步和评测库同步；入口只调用一次 `asyncio.run`。Alembic 的异步环境会从同步入口内部调用 `asyncio.run`，因此两次迁移通过 `asyncio.to_thread` 顺序执行，避免嵌套事件循环；真实 Embedding Provider 始终只在主事件循环使用。

未采用的方案：

- 每次请求新建 HTTP 客户端：可规避跨循环问题，但失去连接复用并增加请求开销。
- 为两个数据库分别创建 Provider：可以工作，但 Provider 生命周期由数据库编排层负责，职责耦合更重。

## 数据流与边界

1. 校验主库和评测库 URL。
2. 单次进入事件循环。
3. 确保评测库存在。
4. 通过工作线程顺序执行两个数据库的 Alembic 升级。
5. 使用同一 Provider 依次同步主库、评测库；每个数据库仍使用独立事务。
6. 返回原有统计结构，保持调用方接口不变。

知识库内容版本包含 Embedding 模型签名。由 Mock 切换到 `bge-m3` 后，现有文档会被判定需要更新并重新切块、向量化。真实 `.env` 与 API Key 不进入 Git。

## 错误处理

- 任一数据库的真实向量请求失败时，该数据库当前事务回滚，初始化进程非零退出，避免写入部分向量。
- 已成功提交的前一个数据库不做跨库回滚；再次运行初始化依靠现有幂等同步恢复。
- 保留 HTTP 状态异常向上抛出，防止静默降级为 Mock。

## 测试与验收

- 新增回归测试，使用带事件循环绑定行为的异步 Provider，证明主库和评测库在同一事件循环执行。
- 运行相关单元/集成测试，不放宽既有断言。
- Docker 初始化成功退出，API 健康检查显示 `openai / bge-m3`。
- 主库和评测库各 20 份知识文档的向量元数据均为真实 `bge-m3`，向量维度为 1024。
- 完整运行 100 条真实 DeepSeek Agent 评测并保存报告。报告只将现有意图、工具、转人工和安全指标称为 Agent 指标；若没有人工标注的检索相关性数据，不宣称 Recall@K、MRR 或“Embedding 正确率”。

## 非目标与后续

本次不新增检索基准数据集。若需要量化 Embedding 检索质量，应另建带 `relevant_document_ids` 标注的查询集，计算 Recall@K、MRR 和 nDCG，并与 Mock 哈希向量做同集对照。
