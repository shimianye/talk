# AGENTS.md

本文件是本项目所有 AI 编程助手（WorkBuddy/夜灯、OpenAI Codex 等）的共享约定。**开工前必读。**

## 项目概述

手机电商智能客服 Agent（企业级 MVP）：LangGraph + DeepSeek Tool Calling 的有状态客服 Agent，
覆盖商品咨询、推荐、订单物流、售后协作与人工接管，含权限校验、审计追踪与自动化评测。

- 栈：FastAPI + SQLAlchemy(async) / LangGraph / PostgreSQL + pgvector / Redis / Vite + React + TS
- 运行：`cp .env.example .env` → `docker compose up -d --build`
- 后端工作目录：容器内 `/app`（宿主机 `./backend` 挂载）
- 测试：`cd backend && python -m pytest -q`
- 评测：`cd backend && python -m eval.run_eval`（Mock 模式离线可跑，真实模式需 DEEPSEEK_API_KEY）

## 当前阶段

**阶段一：工程可信度基础**（计划见 `D:\Administrator\WorkBuddy\outputs\工程可信度基础阶段计划.md`）
任务台账见 `docs/TASK-LEDGER.md`。阶段二（SSE、压测、演示视频、云部署）在阶段一全部完成后启动。

## 硬性约束

1. **不要提交 `.env`、密钥、真实 API Key**。`.env` 已在 `.gitignore`。
2. **不要 `git push --force`**，不要改写已有 commit 历史。
3. **不要为了让测试通过而放宽断言或改评测集**——指标下滑先查根因，不要回补数字。
4. **不要引入临时兼容层**：不做旧库迁移兼容，旧 volume 直接 `docker compose down -v` 重建。
5. 数据库结构变更必须走 Alembic 迁移，**禁止再用 `create_all` 建表**。
6. 每个子任务独立 commit，前缀规范：`feat` / `fix` / `test` / `docs` / `ci` / `refactor`。

## 协作规则（多 agent 并行时）

1. **同一时刻只有一个 agent 改代码**。另一个做只读分析、文档或方案设计。
2. **动手前先查 `docs/TASK-LEDGER.md`**，把任务标为 `进行中` 并写上负责方，避免两边改同一批文件。
3. **完成后写交接记录**到 `docs/handoffs/YYYY-MM-DD-<执行方>.md`，内容包含：
   改了哪些文件、为什么这么改、验证方式、遗留问题、下一步建议。
4. **交接后由对方复核再继续**，不要接力式盲改。
5. commit message 末尾标注执行方，例如：

   ```
   fix(eval): 评测读取 state 内真实 intent，删除旁路分类

   [执行方: codex]
   ```

## 对外表述口径

README、文档、简历中的描述必须与实际实现一致，不夸大：

- 不写"企业级迁移体系"，写"结构变更纳入 Alembic 版本管理，支持可重复升级与回滚"
- 指标必须说明口径（如"意图准确率的口径为 Agent 图内实际路由结果"）
- 未实测的能力（并发、压测）不得先写进文档
