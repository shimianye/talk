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
| T-F | README 升级（Mermaid 架构图 / 真实指标双栏 / 4 张截图 / 修正过时描述） | 夜灯 | 已完成 | T-D, T-E | README 已重写（11 节）：CI badge 启用（`shimianye/talk`）、Mermaid 架构图、Mock 指标双栏、安全与评测方法两节、路线图补 P2-P6 工程基线；数字修正 26→45 测试 / 13→15 外键 / 20→19 路由；**badge 已验证 passing**（HTTP 200，绿 `#28A745`）；Mermaid 已做语法加固（`b7ce6d5`），**GitHub 页面已人工确认渲染为架构图**；**远程 main 已推至 `d5a3e79`（含 T-G 决策文档 + 表数 23→24 修正），CI 复验 Run `34007566771` success**（1 warning=Node20 deprecation，非功能性）；**4 张截图已就位**（`docs/screenshots/`：01 部署 / 02 聊天 / 03 评测报告 / 04 CI 绿徽章） |
| T-G | 技术决策文档 v1（架构 / RAG / 安全 / 评测方法论四章） | 夜灯 | 已完成 | T-D | 27 条决策已按真实实现复核；数字口径核对通过（24 张表 / 15 外键 / 19 路由 / 14 工具 / 9 节点 / 100 条评测）；修正 `GIT_COMMIT` 的 CI 表述；T-F 已完成 |

**护栏：9/12 前必须完成 T-A ~ T-D。**

## 阶段二 · 展示与验证（阶段一全部完成后启动）

| ID | 任务 | 负责方 | 状态 | 依赖 |
|----|------|--------|------|------|
| T-H | 前端 SSE 流式消费（改 `frontend/src/api.ts`） | Codex | 已完成 | 阶段一完成 | 方案 A 已实现；含跨 chunk SSE 解析、AbortController 清理、按帧 token 缓冲、done 收尾和同步降级；后端 SSE/LLM 不改；commit `cacd648`；WorkBuddy 只读复核通过（8 项清单全绿，3 个非阻断瑕疵见 `outputs/T-H复核-cacd648.md`） |
| T-I | 聊天页重截图 | 夜灯 | 已完成 | T-H | 单帧完整答案；`02-consumer-chat.png` 已更新（1280×1617，<1MB），内容含登录态、问题与完整客服回复；WorkBuddy 只读复核通过（4 项全绿） |
| T-J | 并发压测（20 虚拟用户 P50/P95） | Codex | 已完成 | T-H | Mock 基线已完成并由 WorkBuddy 复核：20 虚拟用户、1～3 秒思考间隔、60 秒、210 次 chat、0 失败，P50 3100ms / P95 5800ms / RPS 3.56；开发库已按边界清理 4 张运行态表，业务基线保持 products=9 / orders=50 / knowledge_documents=20 / evaluation_dataset=100 |
| T-K | 1 分钟演示视频 | 夜灯 | 已完成 | T-H | 4K/60fps 成片 58.5s：README 架构 + 决策文档 + SSE 打字机 + 评测报告 + CI 绿徽章；补镜头（评测/CI 两张横版图 + 14s 片段）由夜灯用 matplotlib+ffmpeg 生成；视频存仓库外（`E:\失眠夜的探店日记\...\9月6日.mp4`），README 链接待定 |
| T-L | 技术决策文档 v2（补 SSE 章节） | 夜灯 | 已完成 | T-H | 第 5 章 `05-sse-streaming.md` 的 5 条决策已只读复核通过；均与 `4d0748c` 实现一致，明确「前端打字机式渲染、不宣称真流式、不降低首字延迟」；README 索引、交接文档和台账已同步 |
| T-M | 云部署 demo | — | 后置 | T-J | 暂不执行：需要云账号、公网资源、密钥与费用控制；当前本地可复现部署、CI、评测、压测和演示视频已足够支撑求职展示；待明确云平台与预算后再单独立项 |
| T-N | 求职证据增强：真实模型评测、决策依据展示、评测可视化与面试材料 | Codex | 待复核 | T-L | 已修复真实 HTTP Provider 跨事件循环及 Alembic 嵌套循环问题；48 passed / 3 skipped；主库与评测库均核验 20 文档 / 87 向量 / `bge-m3:1024`；DeepSeek + BGE-M3 全量 100/100 成功，意图 84/100、工具 2/9、转人工 1/5、拒答/拦截 1/6，报告 `eval-20260910053147`；未将 Agent 指标包装为检索正确率 |

## 已完成

| ID | 任务 | 负责方 | 完成时间 |
|----|------|--------|----------|
| T-0 | 阶段 0 诊断（D1-D5 结论） | Codex | 2026-09-05 |
| T-A | 真实 Alembic 初始迁移 | Codex | 2026-09-05 |
| T-B | 幂等种子导入 + 知识库按内容版本更新 | Codex | 2026-09-05 |
| T-C | 独立评测库 + init 参数化 | Codex | 2026-09-05 |
| T-D | 评测修复四项 | Codex | 2026-09-05 |
| T-E | GitHub Actions CI（真实 Run 34005144560 success） | Codex | 2026-09-06 |
| T-F | README 升级（架构图 / 指标双栏 / 4 张截图 / 数字修正） | 夜灯 | 2026-09-06 |
| T-G | 技术决策文档 v1（架构 / RAG / 安全 / 评测四章 27 条决策） | 夜灯 | 2026-09-06 |
| T-H | 前端 SSE 流式消费（打字机渲染 + loading 同步 + 降级） | Codex | 2026-09-06 |
| T-I | 聊天页重截图 | 夜灯 | 2026-09-06 |
| T-J | 并发压测（20 虚拟用户 P50/P95） | Codex | 2026-09-06 |
| T-K | 1 分钟演示视频（4K 成片） | 夜灯 | 2026-09-06 |
| T-L | 技术决策文档 v2（补 SSE 章节） | 夜灯 | 2026-09-06 |
