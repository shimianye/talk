# README 截图素材

README 的「📷 截图」节引用本目录下的 4 张图片。素材由失眠夜在本机截图后放入，文件名固定。

## 素材清单

| # | 场景 | 文件名 | 操作步骤 |
|---|------|--------|----------|
| 1 | 本地一键部署 | `01-deploy-docker-compose.png` | `docker compose up -d --build` 后截终端输出，需看到各服务 healthy；可同框浏览器访问 `http://localhost:5173` 与 `http://localhost:8000/docs` |
| 2 | 消费者聊天页 | `02-consumer-chat.png` | 登录消费者账号，问「iPhone 15 Pro 128G 有货吗？价格多少？」，截到流式回复 |
| 3 | 评测报告（Markdown） | `03-eval-report-md.png` | `cd backend && python -m eval.run_eval` 后打开 `backend/eval/reports/eval-*.md`，截渲染视图 |
| 4 | GitHub Actions 绿徽章 | `04-ci-green-badge.png` | 打开 Actions 页面，截到绿色 ✓ 与 Job 名、时间 |

## 规范

- 格式 PNG，宽度 ≥ 1280px，单文件 < 1MB
- 文件名固定，不含空格与中文（README 按路径直接引用）
- 任何包含真实用户数据或 API key 的区域先打码
- 本目录**不入** `.gitignore`，素材需要随仓库分发
