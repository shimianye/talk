# 📱 手机电商智能客服 Agent（企业级 MVP）

> 基于 **LangGraph + DeepSeek Tool Calling** 的手机电商智能客服 Agent，面向手机零售场景，覆盖商品咨询、推荐、订单物流查询、售后协作与人工接管，支持权限校验、审计追踪与自动化评测，本地 Docker Compose 一键可复现。

[![Python](https://img.shields.io/badge/Python-3.12-3776AB)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-blueviolet)](https://langchain-ai.github.io/langgraph/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-4D6BFE)](https://deepseek.com)
[![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL+pgvector-336791)](https://www.postgresql.org)

---

## ✨ 项目定位

本项目不是只能回答 FAQ 的聊天机器人，而是一个**可运行、可交付、可评测**的有状态 Agent，实现：

- 消费者端：商品咨询、参数对比、购买推荐、订单物流查询、售后申请。
- 客服工作台：人工接管、工单处理、内部备注、执行轨迹查看。
- 管理端：商品、知识库、用户权限、评测与审计管理。
- 本地可复现：Docker Compose 一键启动；DeepSeek 不可用时用 Mock LLM 跑测试。

完整设计见 `docs/superpowers/specs/2026-09-03-phone-commerce-agent-design.md`（设计文档源仓库）。

## 🏗 系统架构

```text
React Consumer UI / Agent Console / Admin UI
                         │ HTTP + SSE
                         ▼
                  FastAPI API Gateway
           Auth · Chat · Session · Admin · Eval
                         │
                         ▼
                 LangGraph Agent Runtime
       State · Nodes · Tool Loop · HITL · Trace
                         │
                         ▼
                    Tool Registry
      Product · RAG · Order · Inventory · After-sales
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      PostgreSQL + pgvector          Redis
                         │
                         ▼
                    DeepSeek LLM
```

## 📁 目录结构

```
phone-commerce-agent/
├── backend/                 # FastAPI + LangGraph 后端
│   ├── app/
│   │   ├── api/             # 路由（auth/chat/session/admin/eval）
│   │   ├── core/            # llm / tools / agent / rag / security
│   │   ├── db/              # SQLAlchemy 会话
│   │   ├── models/          # ORM 实体
│   │   └── schemas/         # Pydantic 模型
│   ├── tests/               # 测试
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # Vite + React + TypeScript 三端 UI
├── data/
│   ├── kb-docs/             # 知识库文档（20 篇，商品知识卡 + 政策）
│   └── seed/                # 种子数据（xlsx）
├── eval/                    # 评测集与指标脚本
├── scripts/seedgen/         # 种子数据生成/校验脚本（复用自 Codex 会话）
├── docker-compose.yml
└── .env.example
```

## 🚀 快速开始

```bash
# 1. 准备环境变量
cp .env.example .env          # 按需填写 DEEPSEEK_API_KEY（不填则用 Mock LLM）

# 2. 一键启动（API + 前端 + PostgreSQL/pgvector + Redis）
docker compose up -d --build

# 3. 初始化数据库（建表 + 导入种子数据 + 知识库向量化入库）
docker compose exec api python scripts/init_db.py

# 4. 访问
#    前端       http://localhost:5173   （演示账号见登录页）
#    API 文档   http://localhost:8000/docs
```

### 运行模式（Mock vs 真实）

项目支持两套运行模式，通过 `.env` 切换（登录页会显示当前模式）：

| 模式 | LLM | Embedding | 适用 |
|------|-----|-----------|------|
| **Mock（默认）** | 关键词启发式 Mock | 哈希向量（mock-hash） | 离线测试、无 Key 跑通全链路 |
| **真实** | DeepSeek（OpenAI 兼容） | BGE-M3（TEI/Ollama 兼容 Embedding） | 生产演示、真实评测 |

```bash
# 切换真实模式（.env）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxx
EMBEDDING_PROVIDER=openai          # OpenAI 兼容，接 TEI 部署的 BGE-M3
EMBEDDING_BASE_URL=http://embedding:8080
EMBEDDING_MODEL=bge-m3
```

> 说明：Reranker 重排预留了扩展点（`retriever` 的 `hybrid_retrieve` 已实现 BM25 + 向量 + RRF 三路融合），当前默认不启用独立 Reranker 模型，避免夸大能力。

### 测试与评测

```bash
# 单元测试（26 个，离线可跑）
cd backend && python -m pytest -q

# 自动化评测（100 条，Mock LLM 离线可跑；接 DeepSeek 后指标更真实）
cd backend && python -m eval.run_eval
```

> 前端本地热更新开发：`cd frontend && npm install && npm run dev`（Vite 已代理 /api → localhost:8000）。

## 🧩 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 编排 | LangGraph StateGraph | 有状态执行、工具循环、HITL、Trace |
| LLM | DeepSeek（OpenAI 兼容） | 主模型，含 Mock 兜底 |
| 后端 | FastAPI + SQLAlchemy(async) | 网关、鉴权、SSE |
| 数据库 | PostgreSQL + pgvector | 业务数据 + 向量索引 |
| 缓存 | Redis | 会话 / 缓存 / 限流 / 幂等 |
| 前端 | Vite + React + TS | 三端 UI |
| 部署 | Docker Compose | 一键可复现 |

## 🗺 实现路线图

- [x] **P0 工程骨架** — 目录结构、Docker Compose、配置、健康检查、前后端骨架
- [x] **P1 数据层** — 23 张表 ORM 模型、Alembic 配置、xlsx→DB 导入脚本、users/roles 种子（代码完成，待 Docker 起库后执行 `python scripts/init_db.py`）
- [x] **P2 LLM & 工具** — LLMClient 适配层（DeepSeek+Mock）、Tool Registry、14 个工具（5 组）
- [x] **P3 Agent 运行时** — LangGraph 图（9 节点）、Guardrail、执行限制降级、写操作确认门控、HITL、Trace
- [x] **P4 RAG 管线** — kb-docs 入库（切分/向量化）、BM25+向量混合检索(RRF)+文本降级、引用溯源
- [x] **P5 API & 安全** — JWT/RBAC、归属校验、PII 递归脱敏、审计、SSE 流式（20 条路由）
- [x] **P6 前端** — 消费者对话 / 客服工作台 / 管理后台（Vite + React + TS）
- [x] **P7 评测 & 交付** — 100 条评测集、指标脚本、26 个单元测试、README

## 🔒 安全与评测要点

- 安全链路：输入注入检查 → JWT/RBAC → 资源归属 → 参数校验 → 结果 PII 递归脱敏 → 敏感承诺检查 → 脱敏审计。
- 数据完整性：13 个外键约束（订单/物流/售后/SKU/知识片段/消息级联）；初始化脚本内置订单时间序 + 外键引用校验。
- 评测：100 条评测集，覆盖商品参数/对比/推荐/价格/库存/订单物流/售后/投诉/拒答/越权查询；指标含意图准确率、工具选择准确率、转人工准确率、拒答拦截率、答案产出率、P50/P95 延迟等。

## 📄 License

MIT License
