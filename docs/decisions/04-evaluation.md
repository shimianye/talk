# 第 4 章 · 评测方法论决策

> 记录日期：2026-09-06 ｜ 基准 commit：`3f28f4c` ｜ 状态定义见 [README](./README.md)

本章记录「评测在哪儿跑、身份怎么注入、隔离怎么验证、结果怎么复现、报告怎么落盘、指标怎么算」六个层面的取舍。这是「工程可信度」阶段的核心——**先证明能测，再谈优化**。

---

## D4-1 独立评测库：评测不污染主库、主库不影响评测

- **状态**：已采纳
- **背景**：评测会「重置运行态 + 重放种子 + 反复跑 Agent」，若用主库，会污染真实数据；反之主库数据变动也会让评测结果不可复现。
- **决策**：`eval_database_url` 独立建库，评测 runner 先 `reset_eval_runtime_state` 清空运行表，再复用 T-B 的 `sync_seed_data` 恢复受控种子基线，保证每次从同一状态出发。
  - 实现位置：`backend/eval/database.py`（`create_eval_engine` / `reset_eval_runtime_state`）、`run_eval.py::run_evaluation`。
- **放弃的替代方案**：*在主库跑评测*（污染 + 不可复现）——放弃；*每个样本新开一个库*（慢、重）——放弃。
- **失效条件**：评测集膨胀到需要并行分片时，单库顺序跑会变慢，需引入评测编排与库快照隔离。

---

## D4-2 身份映射只在 harness 派生，不修改评测集

- **状态**：已采纳
- **背景**：Owner 隔离评测需要「某条样本绑定真实消费者」；若把 owner 写进评测 xlsx，会污染「评测集」这一共享资产，且真实用户 ID 泄露进仓库。
- **决策**：评测 xlsx 只存「问题 + 期望意图/工具/路由」等**纯语义标注**；owner 身份由 `identity.py` 在 harness 里从评测库**实时派生**（`OWNER_BY_QUESTION_ID` 映射 + 订单表反查真实 owner）。
  - 实现位置：`backend/eval/identity.py`（`identity_for_item` / `owner_isolation_pair`）。
  - 8 条样本绑定真实消费者（如 `U6147`），`AUTO` 表示从评测库实时查得。
- **放弃的替代方案**：*把 owner 写进评测集*（污染共享资产 + 泄露真实 ID）——放弃；*硬编码 owner 到 runner*（换库即失效，脆弱）——放弃。
- **失效条件**：当身份绑定规则复杂到「按样本动态关联多实体」时，静态映射表不够，需把身份派生逻辑做成可声明的配置。

---

## D4-3 Owner 隔离用「对偶探针」独立验证，不经 Agent 图

- **状态**：已采纳
- **背景**：Owner 隔离是安全红线，若只靠 Agent 图里「碰巧走对」来证明，结论不可信——LLM 可能恰好没调订单工具。
- **决策**：单独 `_run_owner_isolation_probe` **直接调用** `query_order` 工具：owner 调 → 必须 success，non-owner 调 → 必须失败且报「无权」。三者（owner 通过 / non_owner 拦截 / 混合错误）单独成指标。
  - 实现位置：`backend/eval/run_eval.py`（`_run_owner_isolation_probe`）、`identity.py::owner_isolation_pair`（固定订单 `ORD202609001` 的 owner/non-owner 对偶）。
  - 当前基线：owner 通过 1 / non_owner 拦截 1 / 混合错误 0。
- **放弃的替代方案**：*只统计 Agent 图里的 owner 命中*（不可信）——放弃。
- **失效条件**：订单工具增多（售后、物流都需隔离）后，单探针不够，需对每个「含 owner 语义的工具」各设一组对偶探针。

---

## D4-4 环境指纹：让每份报告可复现

- **状态**：已采纳
- **背景**：「准确率 43%」若不知道跑在什么 commit、什么模型、什么 embedding 上，就是一句无法复现的空话。
- **决策**：报告落盘时记录 `git_commit / llm_provider / llm_model / embedding_provider / embedding_model / embedding_dim / database_name / alembic_revision / run_at_utc / eval_set_sha256` 十项指纹。
  - 实现位置：`backend/eval/reporting.py`（`build_environment_fingerprint` / `_git_commit`）。
  - `eval_set_sha256` 对评测 xlsx 做哈希，保证「报告对应哪份评测集」可追溯；`git_commit` 优先读取可选的 `GIT_COMMIT` 环境变量，否则从 runner 的 Git 工作区读取当前提交 SHA。
- **放弃的替代方案**：*只记时间戳*（无法复现）——放弃；*靠人工记录*（易漏易错）——放弃。
- **失效条件**：若评测集用数据库表而非 xlsx 管理，`sha256(xlsx)` 失效，需改为对评测集内容做规范化哈希。

---

## D4-5 双格式报告：JSON 机器可读 + Markdown 人工可读

- **状态**：已采纳
- **背景**：CI 需要结构化数据（做断言/归档），招聘评审需要一眼看懂的报告。
- **决策**：同一次运行同时写 `eval-{stamp}.json`（完整指标 + 逐条 detail + errors）和 `eval-{stamp}.md`（指标表 + Owner 隔离 + 失败摘要）。
  - 实现位置：`backend/eval/reporting.py`（`persist_report` / `_markdown`）、`run_eval.py`（`--output-dir`）。
  - CI artifact `eval-report-*` 保留 30 天。
- **放弃的替代方案**：*只出 JSON*（评审看不懂）——放弃；*只出 MD*（无法程序断言）——放弃。
- **失效条件**：需要长期趋势对比时，散落的时间戳文件不够，需落库做历史报告查询。

---

## D4-6 全分母指标 + 单条异常兜底 + 错误脱敏

- **状态**：已采纳
- **背景**：指标若只按「成功的样本」算分母，会系统性高估；单条样本崩溃若中断整个评测，则永远跑不到 100 条；报错里若含 URL 凭据则泄露。
- **决策**：
  1. **全分母**：意图/答案产出等指标按「全部 100 条」为分母，工具/转人工/拒答按各自「相关子集」为分母，口径写在 README 指标栏里。
  2. **单条兜底**：`_run_item` 外 `try/except`，单条异常记入 `errors[]` 并 rollback，继续跑下一条。
  3. **错误脱敏**：`_safe_error_message` 移除 URL 凭据与 Bearer token、压成单行、截断 240 字符。
  - 实现位置：`backend/eval/run_eval.py`（`compute_metrics` / `_safe_error_message`）。
- **放弃的替代方案**：*按成功样本算分母*（虚高）——放弃；*单条失败即中断*（永远跑不满）——放弃。
- **失效条件**：指标口径（分母）随意图类别增加会变复杂，需把「每个指标的分母定义」结构化，避免口径漂移。

---

## D4-7 先立 Mock 基线，再谈真实 LLM

- **状态**：已采纳（待真实 LLM 验证）
- **背景**：在没接 DeepSeek/BGE-M3 前，先跑通「评测基础设施 + 指标口径 + 报告指纹」，用 Mock 得到一组**可复现的基线数字**，作为后续真实 LLM 的对照。
- **决策**：当前 Mock 基线（100 条评测集）——意图准确率 0.43、工具选择 0.2222、转人工 0.4、拒答/拦截 0.3333、答案产出 1.0、P50 4.4ms / P95 13.9ms、Owner 隔离 1/1/0。
  - 实现位置：`backend/eval/reports/`（历史报告）、README「指标」双栏。
- **放弃的替代方案**：*没接真实 LLM 就不评测*（推迟发现问题）——放弃；*用 Mock 数字冒充真实质量*（不诚实，违背对外口径）——放弃，所以明确标注为「Mock 基线」。
- **失效条件**：**接真实 LLM 后，这组 Mock 数字全部作废**，必须以真实模型重跑、重新定基线；Mock 基线的价值仅在于「证明了评测链路和口径是对的」。

---

## 小结

评测层的取舍主线是 **「可信度 = 可复现 + 全口径 + 独立验证」**：独立库保证隔离、环境指纹保证可复现、全分母保证不虚高、对偶探针保证安全红线被独立证实。代价是「评测基础设施比业务本身还重」——但对一个以「工程可信度」为卖点的项目，这恰恰是核心资产，不是负担。
