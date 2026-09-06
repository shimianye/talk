# 第 1 章 · 架构决策

> 记录日期：2026-09-06 ｜ 基准 commit：`3f28f4c` ｜ 状态定义见 [README](./README.md)

本章记录「服务怎么组织、Agent 怎么编排、模型怎么接入、数据怎么迁移」四个层面的关键取舍。

---

## D1-1 用 LangGraph 显式状态图编排 Agent，而非手写 while 循环

- **状态**：已采纳
- **背景**：一轮客服对话需要经过「加载上下文 → 输入安检 → LLM 决策 → 工具执行 → 结果校验 → 输出安检 → 落 Trace」多步，且存在循环（工具执行后回到决策）和分支（转人工 / 请求澄清）。用 `if/else` + `while` 手写，控制流会散落在各函数里，既难审计也难测试。
- **决策**：用 `langgraph` 的 `StateGraph` 显式声明 9 个节点 + 3 个条件路由，控制流集中在一处、一眼可见。
  - 实现位置：`backend/app/core/agent/graph.py`（`build_graph`）、`nodes.py`（9 节点）。
  - 节点：`load_session_context → input_guardrail → agent_decision ⇄ tool_execution → validate_tool_result`，旁路 `ask_clarification` / `human_handoff`，终到 `output_guardrail → save_trace`。
  - 路由逻辑独立成纯函数（`route_after_load` / `route_after_decision` / `route_after_tool_execution`），只依赖 state，不碰 IO，单测友好。
- **放弃的替代方案**：
  - *手写 ReAct 循环*：省一个依赖，但控制流不可视、分支测试成本高。放弃。
  - *AutoGPT 式自主循环*（Agent 自己决定何时停）：不可控、不可审计，违背「工程可信度」目标。放弃。
- **失效条件**：当图节点超过约 20 个、或出现「按意图动态拼装不同子图」的需求时，单文件 `build_graph` 会难维护，需引入子图（`StateGraph` 嵌套）或编排器分层。

---

## D1-2 LLM 统一抽象 + 工厂注入 + Mock 优先，密钥与实现解耦

- **状态**：已采纳（待真实 LLM 验证）
- **背景**：DeepSeek 需要 API Key，本地开发、离线 CI、确定性评测都不能依赖真实 Key。若在节点里直接 `import openai` 调 DeepSeek，测试和离线跑通都会卡死。
- **决策**：定义 `LLMClient` 统一接口（`base.py`），提供 `DeepSeekClient`（真实）与 `MockLLMClient`（确定性替身）两个实现，由 `factory.get_llm_client()` 按配置返回；`llm_provider` 默认 `mock`，无 Key 时自动降级。
  - 实现位置：`backend/app/core/llm/{base,deepseek,mock,factory}.py`、`backend/app/config.py`（`llm_provider` / `deepseek_api_key`）。
  - Mock 行为可预测：按关键词映射意图与工具（`mock.py` 的 `_KEYWORD_TO_TOOL` / `_classify_intent`），收到工具结果后转为文本作答，避免空转。
- **放弃的替代方案**：
  - *在业务代码里硬编码 DeepSeek SDK*：无法离线测试、无法复现评测。放弃。
  - *只做 Mock 不做真实实现*：会变成「演示项目」，真实链路是空话。所以真实实现 `DeepSeekClient` 也写好了，只是没接 Key。
- **失效条件**：一旦接入真实 DeepSeek，Mock 的关键词启发式无法覆盖真实意图分布，**Mock 指标会失去参考意义**（见第 4 章 D4-4），必须切换到真实 LLM 重跑评测并重新定基线。

---

## D1-3 工具注册表 + RBAC 角色过滤，作为唯一的工具权限边界

- **状态**：已采纳
- **背景**：LLM 是不可信的执行者。如果让它自由调用任意 Python 函数，注入攻击、越权访问、误操作都无从拦截。
- **决策**：所有工具必须经 `ToolRegistry` 注册（名字唯一），LLM 只能从「当前角色可见」的工具里选；执行时由服务端注入 `ToolContext`（`user_id` / `role` / `db`），**不信任 LLM 传入的身份**。
  - 实现位置：`backend/app/core/tools/registry.py`（`for_role` / `to_openai_tools`）、`base.py`（`Tool` 声明 `permission` / `read_only` / `requires_confirmation`）、`nodes.py::agent_decision`（`registry.to_openai_tools(role)`）。
  - 角色层级：`consumer(0) < agent(1) < supervisor(2) < admin(3)`；14 个工具按 5 组注册（business/product/after_sales/collaboration/knowledge）。
- **放弃的替代方案**：
  - *LLM 直接写 SQL / 调用任意函数*：权限无法收敛，安全红线失守。放弃。
  - *每个工具一个独立服务*：对 14 个工具的规模是过度设计。放弃。
- **失效条件**：工具数量超过约 30 个、或工具需要跨进程/跨服务编排时，单一进程内注册表会不够用，需引入工具网关或 MCP 风格的独立服务。

---

## D1-4 用 Alembic 真实迁移取代 create_all

- **状态**：已采纳
- **背景**：`create_all` 只在「表不存在时建表」，无法处理已有库的列变更，团队协作和上线变更都无法追踪。
- **决策**：全量走 Alembic 迁移链，CI 里做 `upgrade head` + `downgrade base` 的往返校验（T-A 交付）。模型导入集中在 `models/__init__.py` 供 autogenerate 识别。
  - 实现位置：`backend/alembic/`、`backend/app/models/__init__.py`、`backend/scripts/check_migration_drift.py`（迁移漂移校验）。
  - 规模：23 张业务表 + 1 张 `alembic_version`，15 个外键约束，1 条初始迁移（T-A 为真实 autogenerate）。
- **放弃的替代方案**：
  - *`metadata.create_all`*：零迁移历史，不可回滚。放弃。
  - *手工 SQL 脚本迁移*：失去 autogenerate 的模型↔迁移一致性校验。放弃。
- **失效条件**：当出现「多分支并发改 schema」且需数据回填的复杂迁移时，单链式迁移会冲突，需引入 Alembic 多 head 或迁移协作规范（本项目单 Agent 改代码，暂不触发）。

---

## D1-5 分层单向依赖 + 请求作用域 db 注入，不搞全局会话

- **状态**：已采纳
- **背景**：客服 Agent 的每轮对话有独立的 `user_id` 和 DB 会话，若用全局单例 session，并发下会串数据、也难回滚。
- **决策**：依赖方向固定为 `api/routes → services → core(agent/tools/rag/security/llm) → models/db`；DB 会话由路由层创建、经 `AgentState["db"]` 注入到图，工具通过 `ToolContext` 拿到，**离线单测时可传 None 优雅跳过**（`save_trace` 里 `if db is None: return`）。
  - 实现位置：`backend/app/api/deps.py`（会话依赖）、`backend/app/core/agent/state.py`（`db: Any`）、`backend/app/services/chat_service.py`。
- **放弃的替代方案**：
  - *全局 AsyncSession*：并发安全差、事务边界模糊。放弃。
  - *每节点自行开库连接*：连接泄漏、事务不可控。放弃。
- **失效条件**：若未来需要跨多个请求的长事务（如多轮跨会话的分布式事务），请求作用域 session 不够，需引入工作单元 / 事件溯源。

---

## D1-6 服务端执行上限，防止失控与资源耗尽

- **状态**：已采纳
- **背景**：LLM 可能陷入「调工具 → 没解决 → 再调」的空转，或一次调用过多工具，烧 token 也拖垮响应。
- **决策**：在 `agent_decision` 里硬约束 `steps > max_agent_steps(8)` 或 `total_tool_calls >= max_tool_calls(12)` 时降级转人工，并打 `execution_limit` 标记；单工具执行带 `timeout`（默认 10s）。配置全部走环境变量。
  - 实现位置：`backend/app/core/agent/nodes.py::agent_decision`、`config.py`（`max_agent_steps` / `max_tool_calls` / `tool_timeout_seconds`）、`tools/base.py`（`asyncio.wait_for`）。
- **放弃的替代方案**：*不设上限*——不可接受；*硬编码上限*——失去可调性。放弃。
- **失效条件**：真实 LLM 下若 8 步 / 12 次工具仍不够完成复杂售后（如「比价 + 查库存 + 下单 + 改地址」），需按真实流量重新标定上限，而不是继续拍脑袋。

---

## D1-7 配置全部环境变量注入，密钥永不入库

- **状态**：已采纳
- **背景**：数据库密码、DeepSeek Key、JWT 密钥属于敏感信息，写进代码或仓库即泄露风险。
- **决策**：`pydantic-settings` 统一从 `.env` / 环境变量读取，代码里只有默认占位（如 `jwt_secret_key="change-me-in-production"`、`deepseek_api_key=""`）；`.env` 在 `.gitignore`，仓库只留 `.env.example`。
  - 实现位置：`backend/app/config.py`、`.env.example`、`.gitignore`。
- **放弃的替代方案**：*硬编码密钥*（放弃，红线）；*Vault/云密钥管理*（对当前单机部署过度，阶段二云部署时再评估）。
- **失效条件**：进入多实例云部署后，单 `.env` 文件不满足滚动更新和权限隔离，需迁移到 Secrets Manager。

---

## 小结

架构层的取舍主线是 **「可控性优先」**：显式状态图胜过自主循环、注册表胜过自由调用、迁移胜过建表、环境变量胜过硬编码。代价是「样板代码更多」，换来的是「每一步都可审计、可测试、可复现」——这正是「工程可信度」阶段的立身之本。
