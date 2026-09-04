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
    }>('/api/v1/chat', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) }),
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
  runEval: () => request<{ metrics: Record<string, unknown> }>('/api/v1/eval/run', { method: 'POST' }),
}
