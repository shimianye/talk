# T-J 聊天接口压测

本目录使用 Locust 压测真实消费者路径 `POST /api/v1/chat`，不压 `/health`。压测数据必须区分 LLM 模式：

- `mock`：测单机 Docker 下 DB + Agent 图 + 工具链开销，不代表真实模型延迟。
- `deepseek`：测真实网络和模型延迟，消耗 API 配额；必须单独运行，不能与 Mock 数字合并。

## 安装与启动

在仓库根目录执行：

```powershell
python -m venv .venv-loadtest
.\.venv-loadtest\Scripts\Activate.ps1
python -m pip install locust
```

启动服务后，先确认 API 和数据库已初始化：

```powershell
docker compose up -d --build
docker compose ps
```

### Mock 基线（推荐先跑）

```powershell
$env:LLM_PROVIDER="mock"
New-Item -ItemType Directory -Force loadtest/reports | Out-Null
locust -f loadtest/locustfile.py --host http://localhost:8000 `
  --headless -u 20 -r 20 -t 60s --csv=loadtest/reports/mock `
  --html=loadtest/reports/mock.html
```

### DeepSeek（单独、限额运行）

先在当前 PowerShell 会话设置真实 Key，不要写入仓库：

```powershell
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="你的真实Key"
New-Item -ItemType Directory -Force loadtest/reports | Out-Null
locust -f loadtest/locustfile.py --host http://localhost:8000 `
  --headless -u 20 -r 20 -t 60s --csv=loadtest/reports/deepseek `
  --html=loadtest/reports/deepseek.html
```

DeepSeek 可能一次聊天触发多次 LLM 调用；20 并发持续 60 秒可能消耗较多 token 或触发 429。正式跑之前建议先用 `-u 2 -r 1 -t 15s` 冒烟，并根据账户余额缩短时长。脚本不伪造指标，也不会绕过服务端限制。

## 推荐压测口径

固定记录：20 个并发用户、启动速率 20 用户/秒、稳态 60 秒、随机问题池、单机 Docker Compose。报告至少包含 P50、P95、RPS、请求数和错误率，并分别标注 Mock/DeepSeek、commit SHA、数据库名、时间、CPU/内存和 Locust 版本。

Locust 结束后，终端会输出 `Aggregated` 行；CSV 中的 `*_stats.csv` 保存请求数、失败数、平均值、P50/P95 和 RPS。HTML 可作为人工评审证据。

## 数据隔离与清理

压测会写入会话、消息和 Trace 等运行态数据。不要直接压生产/主开发库。推荐使用独立 Compose 项目和独立 Postgres volume：

```powershell
docker compose -p pca-loadtest down -v
$env:POSTGRES_DB="phone_commerce_loadtest"
docker compose -p pca-loadtest up -d --build
docker compose -p pca-loadtest exec api python scripts/bootstrap.py
New-Item -ItemType Directory -Force loadtest/reports | Out-Null
locust -f loadtest/locustfile.py --host http://localhost:8000 --headless -u 20 -r 20 -t 60s --csv=loadtest/reports/mock
docker compose -p pca-loadtest down -v
Remove-Item Env:POSTGRES_DB
```

`down -v` 会删除该压测 Compose 项目的独立 volume，等价于清理全部压测数据；请确认项目名为 `pca-loadtest`，不要对开发环境执行 `docker compose down -v`。如果必须复用现有数据库，至少在压测前备份，并由数据库管理员按实际表依赖顺序清理运行态表，不能盲目 TRUNCATE 全库。

## 结果与环境指纹

不要把 `loadtest/reports/` 下的 CSV/HTML 当作业务质量评测。每次报告旁应记录：`git rev-parse HEAD`、`LLM_PROVIDER`、模型、数据库名、Locust 版本、并发/时长、请求问题池版本和机器资源。Mock 与 DeepSeek 报告必须使用不同文件名前缀。
