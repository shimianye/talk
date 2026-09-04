import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken, setUser } from '../api'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<{ llm_provider: string; embedding_provider: string } | null>(null)
  const nav = useNavigate()

  useEffect(() => {
    fetch('/api/v1/health')
      .then((r) => r.json())
      .then((d) => setMode(d.mode))
      .catch(() => setMode(null))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await api.login(username, password)
      setToken(r.access_token)
      setUser({ display_name: r.display_name, role: r.role, user_id: r.user_id })
      nav(r.role === 'consumer' ? '/chat' : '/console')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>📱 手机电商智能客服</h1>
        <p className="sub">登录以开始</p>
        <label>用户名</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="如 admin1 / agent1 / U6147" />
        <label>密码</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <div className="err">{error}</div>}
        <button disabled={loading}>{loading ? '登录中…' : '登录'}</button>
        <div className="hint">
          演示账号（密码均为 password123）：
          <br />
          消费者 U6147 · 客服 agent1 · 管理员 admin1
        </div>
        {mode && (
          <div className="hint">
            当前模式：LLM <b>{mode.llm_provider}</b> · Embedding <b>{mode.embedding_provider}</b>
          </div>
        )}
      </form>
    </div>
  )
}
