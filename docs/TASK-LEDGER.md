# 任务台账

> 状态：`待认领` / `进行中` / `待复核` / `已完成`
> 规则：动手前把任务改成 `进行中` 并写负责方；同一时刻只有一个 agent 改代码。
> 完整方案见 `D:\Administrator\WorkBuddy\outputs\工程可信度基础阶段计划.md`

## 阶段一 · 工程可信度基础

| ID | 任务 | 负责方 | 状态 | 依赖 | 备注 |
|----|------|--------|------|------|------|
| T-A | 真实 Alembic 初始迁移（autogenerate + 校验 upgrade/downgrade + 移除 create_all） | Codex | 已完成 | 无 | commit `0e050d6`；WorkBuddy 复核通过 |
| T-B | 幂等种子导入 + 知识库按内容版本更新 | Codex | 已完成 | T-A | commit `633d03a`；WorkBuddy 复核通过 |
| T-C | 独立评测库 + init 参数化（--database-url） | Codex | 已完成 | T-A, T-B | commit `3c09783`；WorkBuddy 复核通过 |
| T-D | 评测修复四项：读 state["intent"] / 真实种子用户（owner + 非 owner）/ 单条异常兜底 / 报告落盘 | Codex | 已完成 | T-C | commit `0f16eed`；方案 1、独立库、state 单源、双格式报告和 100 条 Mock 已通过；WorkBuddy 复核通过 |
| T-E | GitHub Actions CI（postgres+redis service、迁移、pytest、Mock 评测、绿徽章） | Codex | 已完成 | T-A, T-D | **真实 CI 已通过**：Run `34005144560` success（head `429ce8e`）；首次 `1c7a5bf` 因 runner 缺 `pg_isready`/`redis-cli` 失败在 readiness step，已由 `429ce8e` 安装 postgresql-client + redis-tools 修复；关键步骤全绿；artifact `eval-report-2-34005144560` 保留 30 天；未改业务代码 / 评测集 / Alembic / seed-kb |
| T-F | README 升级（Mermaid 架构图 / 真实指标双栏 / 4 张截图 / 修正过时描述） | 夜灯 | 进行中（等截图） | T-D, T-E | README 已重写（11 节）：CI badge 启用（`shimianye/talk`）、Mermaid 架构图、Mock 指标双栏、安全与评测方法两节、路线图补 P2-P6 工程基线；数字修正 26→45 测试 / 13→15 外键 / 20→19 路由；**badge 已验证 passing**（HTTP 200，绿 `#28A745`）；Mermaid 已做语法加固（`b7ce6d5`），渲染效果待人工确认（沙箱 Chromium 无法启动）；**远程 main 已推至 `3f28f4c`，CI 复验 Run `34007566771` success**（1 warning=Node20 deprecation，非功能性）；**剩余 4 张截图**需失眠夜提供（沙箱无 docker daemon、无数据库、backend 依赖未装），规范见 `docs/screenshots/README.md` |
| T-G | 技术决策文档 v1（架构 / RAG / 安全 / 评测方法论四章） | 夜灯 | 待复核 | T-D | 每章写"为什么选 + 放弃什么 + 何时失效"；已交付 `docs/decisions/`（README 索引 + 4 章，共 27 条决策），并回填 README「技术决策文档」节链接；基于 `3f28f4c` 真实实现回溯 |

**护栏：9/12 前必须完成 T-A ~ T-D。**

## 阶段二 · 展示与验证（阶段一全部完成后启动）

| ID | 任务 | 负责方 | 状态 | 依赖 |
|----|------|--------|------|------|
| T-H | 前端 SSE 流式消费（改 `frontend/src/api.ts`） | 待认领 | 待认领 | 阶段一完成 |
| T-I | 聊天页重截图 | 待认领 | 待认领 | T-H |
| T-J | 并发压测（20 并发 P50/P95） | 待认领 | 待认领 | T-H |
| T-K | 1 分钟演示视频 | 待认领 | 待认领 | T-H |
| T-L | 技术决策文档 v2（补 SSE 章节） | 待认领（建议 夜灯） | 待认领 | T-H |
| T-M | 云部署 demo | 待认领 | 待认领 | T-J |

## 已完成

| ID | 任务 | 负责方 | 完成时间 |
|----|------|--------|----------|
| T-0 | 阶段 0 诊断（D1-D5 结论） | Codex | 2026-09-05 |
| T-A | 真实 Alembic 初始迁移 | Codex | 2026-09-05 |
| T-B | 幂等种子导入 + 知识库按内容版本更新 | Codex | 2026-09-05 |
| T-C | 独立评测库 + init 参数化 | Codex | 2026-09-05 |
| T-D | 评测修复四项 | Codex | 2026-09-05 |
| T-E | GitHub Actions CI（真实 Run 34005144560 success） | Codex | 2026-09-06 |
