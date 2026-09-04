import { useState } from 'react'
import { api } from '../api'

interface Msg {
  sender: 'user' | 'agent'
  content: string
  handoff?: boolean
}

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)

  async function send() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setMessages((m) => [...m, { sender: 'user', content: text }])
    setLoading(true)
    try {
      const r = await api.chat(text, sessionId)
      setSessionId(r.session_id)
      setMessages((m) => [...m, { sender: 'agent', content: r.answer, handoff: r.handoff_required }])
    } catch (err) {
      setMessages((m) => [...m, { sender: 'agent', content: `出错了：${(err as Error).message}` }])
    } finally {
      setLoading(false)
    }
  }

  const quick = ['iPhone 16 的处理器是什么？', '小米 15 现在多少钱？', '怎么退货？', '我要转人工']

  return (
    <div className="chat">
      <div className="chat-box">
        {messages.length === 0 && (
          <div className="empty">
            <p>我是智能客服，可以帮您查商品、价格、库存、订单物流和售后。</p>
            <div className="quick">
              {quick.map((q) => (
                <button key={q} onClick={() => setInput(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.sender}`}>
            <div className="bubble">
              {m.content}
              {m.handoff && <span className="tag">已转人工</span>}
            </div>
          </div>
        ))}
        {loading && (
          <div className="msg agent">
            <div className="bubble">正在思考…</div>
          </div>
        )}
      </div>
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="输入你的问题…"
        />
        <button onClick={send} disabled={loading}>
          发送
        </button>
      </div>
    </div>
  )
}
