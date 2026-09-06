# 第 5 章 · SSE 流式渲染决策（v2 新增）

> 记录日期：2026-09-06 ｜ 基准 commit：`4d0748c`（T-H 最终态）
> 状态定义见 [README](./README.md)。本章为阶段二 T-H「前端 SSE 流式消费」的决策回溯。

本章记录「聊天页怎么把后端 SSE 变成打字机式渲染」这一条链路的关键取舍。核心结论先说在前面：**这是前端打字机式渲染，不宣称真流式、不宣称降低首字延迟**——后端 LLM 仍是完整生成后才返回，只是前端把到达的字符按节奏逐字播放。

---

## D5-1 用 fetch + ReadableStream 手动解析 SSE，而非 EventSource

- **状态**：已采纳
- **背景**：聊天接口是 `POST`，且必须携带 `Authorization: Bearer <token>`。而浏览器原生的 `EventSource` **只支持 GET、无法自定义请求头**，也带不了 POST body。
- **决策**：用 `fetch` 发起 POST，拿到 `response.body` 后用 `getReader()` 读流，配合 `TextDecoder`（`stream: true`）增量解码，手动按 SSE 协议解析帧。
  - 实现位置：`frontend/src/api.ts` 的 `chatStream()`。
- **放弃的替代方案**：
  - *EventSource*：天然适合 SSE 且自带自动重连，但 POST + Header 是硬约束，用不了。放弃。
  - *把认证改到 query 参数*：能迁就 EventSource，但 token 进 URL 会泄露到日志/代理。放弃。
- **失效条件**：若后端改成 GET 流式接口且认证走 Cookie（同源会话），EventSource 更省事，可回退；或改用 WebSocket（需要双向、服务器主动推送场景）。

---

## D5-2 前端打字机式渲染，而非后端真流式

- **状态**：已采纳（明确不宣称真流式）
- **背景**：后端 `POST /chat/stream` 是「伪流式」——`handle_chat()` 先同步跑完整个 Agent 图拿到完整 `final_answer`，再按字符 `yield`。LLM 抽象层（`LLMClient`）只有 `complete`/`complete_json`，没有 `stream` 方法，DeepSeek 客户端也未接 `stream=True`。
- **决策**：T-H 只改前端，把「到达的字符」做成逐字播放的打字机效果；**不碰后端 LLM/LangGraph**，并在文档/提交里明确「不宣称真流式、不降低首字延迟」。
  - 实现位置：`frontend/src/pages/Chat.tsx`（消费 `chatStream`）；后端 `backend/app/api/routes/chat.py::chat_stream`（未改）。
- **放弃的替代方案**：
  - *真 token 级流式*（LLM 边生成边返回）：需要 LLM 层加 `stream` + LangGraph `astream` + 工具调用循环流式，改动面大、风险高，超出 T-H「前端消费」范围。放弃，留待后续独立任务。
- **失效条件**：一旦产品诉求变成「**降低首字等待**」，前端打字机**解决不了**（LLM 仍是先生成完整答案），必须升级后端真流式。届时本决策重估。

---

## D5-3 token 显示队列：30ms/字符定时消费 + loading 同步

- **状态**：已采纳
- **背景**：后端按字符 `yield`，但内容已在内存里、网络又快，token 会「瞬间全到」。若每来一个 token 就 `setState` 一次，React 会在同一帧合并，视觉上变成「一次性出现」，看不到打字机。
- **决策**：token 先进入 `tokenBufferRef` 队列，再由 `drainTokenQueue` **每 30ms 消费 1 个字符**追加到气泡，强制出稳定节奏；`done` 后不立即结束 `loading`，而是等队列 drain 完（`streamDoneRef` + `finishLoadingRef`），防止用户在答案未渲染完时抢发新消息导致上一轮被截断。
  - 实现位置：`frontend/src/pages/Chat.tsx` 的 `drainTokenQueue` / `scheduleTokenDrain` / `streamDoneRef` / `finishLoadingRef`。
- **放弃的替代方案**：
  - *requestAnimationFrame 一次性 flush*：之前版本用它，token 到达快时会整段刷新，无节奏。放弃。
  - *直接逐字符 setState*：不减速，浏览器合并后看不到效果。放弃。
- **失效条件**：单字符粒度太碎——长回答（几百字）会触发几百次 `setState` 且渲染耗时数秒。若回答变长或要求更顺滑，应改为**按词/按块**推送（后端 token 粒度改粗），30ms/字符的固定节奏也会随之重估。

---

## D5-4 同步 `api.chat()` 保留 + 流式失败降级

- **状态**：已采纳
- **背景**：SSE 流可能因网络中断、代理缓冲、解析异常而失败。若失败就报错，可用性差；已有同步 `POST /chat` 是完全可用的完整答案路径。
- **决策**：流式失败时，若**尚未开始渲染**（`!started`），降级调用同步 `api.chat()` 拿完整答案兜底；若已开始渲染则不再重复提交，仅提示「流式连接出错」。
  - 实现位置：`frontend/src/pages/Chat.tsx` 的 `catch` 分支；`frontend/src/api.ts` 保留 `chat()`。
- **放弃的替代方案**：
  - *流式失败直接报错*：可用性差。放弃。
  - *删掉同步接口*：失去兜底路径，且管理端/其它调用方可能仍需要。放弃。
- **失效条件**：若降级掩盖了流式的**系统性 bug**（降级率异常高但无人察觉），需要为降级路径加监控/埋点，而非无条件静默兜底。

---

## D5-5 跨 chunk SSE 解析健壮性

- **状态**：已采纳
- **背景**：TCP/HTTP 分块会把一个 SSE 帧（以空行 `\n\n` 分隔）拆到**多个网络 chunk**，甚至一个 chunk 里含多个帧、或帧的边界落在 chunk 中间。若按「一个 chunk = 一帧」处理，会解析错。
- **决策**：维护 `buffer`，每读到 chunk 追加后按 `/\r?\n\r?\n/` 切帧、`pop()` 保留末尾不完整残片；兼容 `\n\n` 与 `\r\n\r\n`；解析 `event:`/`data:` 字段、忽略注释行、多行 `data` 用 `\n` 拼接；`finally` 里 `reader.cancel()` 兜底释放。
  - 实现位置：`frontend/src/api.ts` 的 `chatStream()` / `processFrame`。
- **放弃的替代方案**：
  - *假设每 chunk 是完整帧*：在代理/移动网络下会错帧。放弃。
  - *引入第三方 SSE 解析库*：功能简单，自写 20 行可控、零依赖。放弃。
- **失效条件**：若未来 SSE 事件变复杂（多行字段、`id:` 重连、心跳），手写解析器需扩展或换库；当前后端事件固定简单，暂不触发。

---

## 小结

SSE 层的取舍主线是 **「后端不动、前端补齐交互体验，且诚实标注边界」**：用 fetch 手动解析解决 POST+Header 约束，用 30ms 显示队列制造打字机节奏，用 loading 同步防止抢发截断，用同步降级保证可用性。代价是「伪流式」——**首字延迟并未降低**，这必须在对外口径里写清楚，不能把打字机效果包装成真流式性能。
