import { useEffect, useState } from 'react'
import { api } from '../api'

type Tab = 'conversations' | 'after-sales'

interface Conv {
  conversation_id: string
  user_id: string
  status: string
  summary?: string
  handoff_required?: boolean
  updated_at?: string
}

interface Case {
  case_id: string
  order_id: string
  user_id: string
  case_type: string
  sub_type?: string
  description?: string
  status: string
  handler?: string
}

export default function Console() {
  const [tab, setTab] = useState<Tab>('conversations')
  return (
    <div className="console">
      <div className="tabs">
        <button className={tab === 'conversations' ? 'on' : ''} onClick={() => setTab('conversations')}>
          会话队列
        </button>
        <button className={tab === 'after-sales' ? 'on' : ''} onClick={() => setTab('after-sales')}>
          售后工单
        </button>
      </div>
      {tab === 'conversations' ? <Conversations /> : <AfterSales />}
    </div>
  )
}

function Conversations() {
  const [convs, setConvs] = useState<Conv[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [msgs, setMsgs] = useState<unknown[]>([])
  const [note, setNote] = useState('')

  async function load() {
    const r = await api.conversations()
    setConvs(r.conversations as Conv[])
  }

  async function open(id: string) {
    setSelected(id)
    const r = await api.getConversation(id)
    setMsgs(r.messages)
  }

  async function takeover() {
    if (!selected) return
    await api.takeover(selected)
    await load()
  }

  async function sendNote() {
    if (!selected || !note.trim()) return
    await api.sendHumanMessage(selected, note.trim(), true)
    setNote('')
    await open(selected)
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="console-grid">
      <div className="list">
        {convs.map((c) => (
          <div
            key={c.conversation_id}
            className={`row ${selected === c.conversation_id ? 'sel' : ''}`}
            onClick={() => open(c.conversation_id)}
          >
            <div className="row-title">{c.user_id}</div>
            <div className="row-sub">
              {c.status}
              {c.handoff_required && ' · 待人工'}
            </div>
          </div>
        ))}
      </div>
      <div className="detail">
        {selected ? (
          <>
            <div className="detail-head">
              <span>会话 {selected}</span>
              <button onClick={takeover}>接管</button>
            </div>
            <div className="msgs">
              {msgs.map((m: any, i) => (
                <div key={i} className={`msg ${m.sender}`}>
                  <div className="bubble">{m.content}</div>
                </div>
              ))}
            </div>
            <div className="note-input">
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="内部备注…" />
              <button onClick={sendNote}>备注</button>
            </div>
          </>
        ) : (
          <div className="empty">选择左侧会话查看详情</div>
        )}
      </div>
    </div>
  )
}

function AfterSales() {
  const [cases, setCases] = useState<Case[]>([])

  async function load() {
    const r = await api.afterSales()
    setCases(r.cases as Case[])
  }

  async function update(caseId: string, status: string, resolution: string) {
    await api.updateAfterSales(caseId, { status, resolution })
    await load()
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <table className="table">
      <thead>
        <tr>
          <th>工单号</th>
          <th>订单</th>
          <th>类型</th>
          <th>描述</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => (
          <tr key={c.case_id}>
            <td>{c.case_id}</td>
            <td>{c.order_id}</td>
            <td>{c.case_type}</td>
            <td>{c.description?.slice(0, 30)}</td>
            <td>{c.status}</td>
            <td>
              {c.status === '已创建' && (
                <button onClick={() => update(c.case_id, '待审核', '已受理')}>受理</button>
              )}
              {c.status === '待审核' && (
                <button onClick={() => update(c.case_id, '已完成', '审核通过，按流程处理')}>结单</button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
