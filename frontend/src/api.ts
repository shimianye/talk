// API 客户端：统一鉴权与错误处理
const API_BASE = import.meta.env.VITE_API_BASE ?? ''

export function getToken(): string | null {
  return localStorage.getItem('token')
}

export function setToken(token: string): void {
  localStorage.setItem('token', token)
}

export function clearToken(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export function getUser(): { display_name: string; role: string; user_id: string } | null {
  const raw = localStorage.getItem('user')
  return raw ? JSON.parse(raw) : null
}

export function setUser(u: { display_name: string; role: string; user_id: string }): void {
  localStorage.setItem('user', JSON.stringify(u))
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string>),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers })
  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('未登录')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail || `请求失败 ${res.status}`)
  }
  return res.json() as Promise<T>
}

export interface ChatStreamMeta {
  session_id: string
  pending_confirmation: boolean
  handoff_required: boolean
  intent?: string
  decision_summary?: DecisionSummary
}

export interface DecisionSummary {
  trace_id: string
  intent: string
  intent_label: string
  actions: Array<{ name: string; label: string; success: boolean }>
  sources: Array<{ document_id: string; title: string; version?: string }>
  safety: Array<{ code: string; label: string }>
  handoff_required: boolean
  mode: string
}

export interface ChatStreamHandlers {
  onMeta?: (meta: ChatStreamMeta) => void
  onToken?: (token: string) => void
  onMessageEnd?: (answer: string) => void
}

/** 消费 POST SSE 聊天流；解析跨网络分块的标准 SSE 帧。 */
async function chatStream(
  message: string,
  sessionId: string | undefined,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  })
  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('未登录')
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail || `请求失败 ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let event = ''
  let dataLines: string[] = []
  let finished = false

  const processFrame = (frame: string): void => {
    for (const line of frame.split(/\r?\n/)) {
      if (!line || line.startsWith(':')) continue
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (!event || dataLines.length === 0) {
      event = ''
      dataLines = []
      return
    }
    const payload = JSON.parse(dataLines.join('\n')) as Record<string, unknown>
    if (event === 'message_start') handlers.onMeta?.(payload as unknown as ChatStreamMeta)
    else if (event === 'token') handlers.onToken?.(String(payload.token ?? ''))
    else if (event === 'message_end') handlers.onMessageEnd?.(String(payload.answer ?? ''))
    else if (event === 'done') finished = true
    event = ''
    dataLines = []
  }

  try {
    while (!finished) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split(/\r?\n\r?\n/)
      buffer = frames.pop() ?? ''
      frames.forEach(processFrame)
    }
    buffer += decoder.decode()
    if (buffer.trim()) processFrame(buffer)
    if (!finished) throw new Error('流式响应未正常结束')
  } finally {
    await reader.cancel().catch(() => undefined)
  }
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; user_id: string; display_name: string; role: string }>(
      '/api/v1/auth/login',
      { method: 'POST', body: JSON.stringify({ username, password }) },
    ),
  chat: (message: string, sessionId?: string) =>
    request<{
      session_id: string
      answer: string
      pending_confirmation: boolean
      handoff_required: boolean
      intent?: string
      decision_summary?: DecisionSummary
      }>('/api/v1/chat', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) }),
  chatStream,
  sessions: () => request<{ sessions: unknown[] }>('/api/v1/sessions'),
  // 管理
  conversations: (status?: string) =>
    request<{ conversations: unknown[] }>(
      `/api/v1/admin/conversations${status ? `?status=${status}` : ''}`,
    ),
  getConversation: (sessionId: string) =>
    request<{ conversation: unknown; messages: unknown[] }>(
      `/api/v1/admin/conversations/${sessionId}`,
    ),
  takeover: (sessionId: string) =>
    request<{ ok: boolean }>(`/api/v1/admin/conversations/${sessionId}/takeover`, {
      method: 'POST',
    }),
  sendHumanMessage: (sessionId: string, content: string, internalNote: boolean) =>
    request<{ ok: boolean }>(`/api/v1/admin/conversations/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content, internal_note: internalNote }),
    }),
  afterSales: () => request<{ cases: unknown[] }>('/api/v1/admin/after-sales'),
  updateAfterSales: (caseId: string, payload: Record<string, unknown>) =>
    request<{ ok: boolean }>(`/api/v1/admin/after-sales/${caseId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  products: () => request<{ products: unknown[] }>('/api/v1/admin/products'),
  knowledge: () => request<{ documents: unknown[] }>('/api/v1/admin/knowledge'),
  traces: () => request<{ traces: unknown[] }>('/api/v1/admin/traces'),
  audit: () => request<{ logs: unknown[] }>('/api/v1/admin/audit'),
  runEval: () => request<{
    total: number
    succeeded: number
    failed: number
    metrics: Record<string, unknown>
    environment?: Record<string, unknown>
    errors?: Array<Record<string, unknown>>
    report_paths?: string[]
  }>('/api/v1/eval/run', { method: 'POST' }),
}
