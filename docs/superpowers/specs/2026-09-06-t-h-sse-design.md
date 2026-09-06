# T-H 前端 SSE 流式渲染设计

## 目标与边界

本任务为消费者聊天页增加 SSE 打字机式渲染。后端现有 `POST /api/v1/chat/stream`、LLM、Agent 图、评测和数据库链路不改；本任务不宣称真流式或降低首字延迟。

## 数据流

`Chat.send()` 使用带 Authorization 的 `fetch` 请求 SSE 接口，通过 `ReadableStream.getReader()` 读取网络分块。解析器以空行分帧，跨 chunk 保留残片，解析 `event` 与 `data` 字段，并将 `token` 增量写入当前助手消息。

## 生命周期与降级

- 每次请求创建 `AbortController`；组件卸载时 abort 并取消 reader。
- 收到 `done` 才结束 loading；异常会结束 loading 并显示错误。
- 若流在收到消息元数据或 token 前失败，调用既有同步 `api.chat()` 作为降级；已经开始渲染后不重复提交，直接提示流式连接异常。

## 状态映射

`message_start` 的 `session_id` 用于续接会话，`pending_confirmation` 和 `handoff_required` 写入助手消息；`message_end` 仅作为答案完整性事件，最终生命周期以 `done` 为准。

## 验收

`npm run build` 通过；SSE 解析覆盖跨 chunk、CRLF、注释行和多行 data；取消、异常、同步降级和状态标签均有明确路径。
