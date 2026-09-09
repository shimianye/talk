import { useEffect, useState } from 'react'
import { api } from '../api'

type Tab = 'products' | 'knowledge' | 'eval' | 'audit' | 'traces'

export default function Admin() {
  const [tab, setTab] = useState<Tab>('products')
  return (
    <div className="console">
      <div className="tabs">
        <button className={tab === 'products' ? 'on' : ''} onClick={() => setTab('products')}>商品</button>
        <button className={tab === 'knowledge' ? 'on' : ''} onClick={() => setTab('knowledge')}>知识库</button>
        <button className={tab === 'eval' ? 'on' : ''} onClick={() => setTab('eval')}>评测</button>
        <button className={tab === 'traces' ? 'on' : ''} onClick={() => setTab('traces')}>Agent Trace</button>
        <button className={tab === 'audit' ? 'on' : ''} onClick={() => setTab('audit')}>审计日志</button>
      </div>
      {tab === 'products' && <Products />}
      {tab === 'knowledge' && <Knowledge />}
      {tab === 'eval' && <Eval />}
      {tab === 'traces' && <Traces />}
      {tab === 'audit' && <Audit />}
    </div>
  )
}

function useData<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  useEffect(() => {
    loader().then(setData).catch(() => setData(null))
  }, [])
  return data
}

function Products() {
  const data = useData(() => api.products())
  const products = (data?.products ?? []) as any[]
  return (
    <table className="table">
      <thead>
        <tr><th>商品ID</th><th>品牌</th><th>型号</th><th>系列</th><th>上市</th></tr>
      </thead>
      <tbody>
        {products.map((p) => (
          <tr key={p.product_id}>
            <td>{p.product_id}</td><td>{p.brand}</td><td>{p.model}</td><td>{p.series}</td><td>{p.release_date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Knowledge() {
  const data = useData(() => api.knowledge())
  const docs = (data?.documents ?? []) as any[]
  return (
    <table className="table">
      <thead>
        <tr><th>文档ID</th><th>标题</th><th>分类</th><th>版本</th><th>访问级别</th></tr>
      </thead>
      <tbody>
        {docs.map((d) => (
          <tr key={d.document_id}>
            <td>{d.document_id}</td><td>{d.title}</td><td>{d.category}</td><td>{d.version}</td><td>{d.access_level}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Eval() {
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.runEval>> | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  const labels: Record<string, string> = {
    '意图准确率': '意图路由',
    '工具选择准确率': '工具选择',
    '转人工准确率': '转人工',
    '拒答/拦截率': '安全拦截',
    '答案产出率': '答案产出',
    'P50延迟(ms)': 'P50 延迟',
    'P95延迟(ms)': 'P95 延迟',
    '平均工具调用数': '平均工具数',
  }

  function displayMetric(key: string, value: unknown) {
    if (value === null || value === undefined) return '尚未评测'
    if (key.includes('率')) return `${(Number(value) * 100).toFixed(1)}%`
    if (key.includes('延迟')) return `${Number(value).toLocaleString()} ms`
    return String(value)
  }

  function needsAttention(key: string, value: unknown) {
    return key.includes('率') && typeof value === 'number' && value < 0.7
  }

  async function run() {
    setRunning(true)
    setError('')
    try {
      const r = await api.runEval()
      setResult(r)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <button onClick={run} disabled={running}>{running ? '评测中…' : '运行评测（100 条）'}</button>
      <p className="eval-note">Mock 与真实模型必须分开解读；缺失值表示尚未评测，不按 0 处理。</p>
      {error && <p className="eval-error">评测失败：{error}</p>}
      {result && (
        <>
          <div className="eval-summary">
            <strong>{String(result.environment?.llm_provider ?? 'unknown').toUpperCase()}</strong>
            <span>样本 {result.total}</span>
            <span>成功 {result.succeeded}</span>
            <span>异常 {result.failed}</span>
          </div>
          <div className="metric-grid">
            {Object.entries(result.metrics).map(([k, v]) => (
              <article key={k} className={`metric-card ${needsAttention(k, v) ? 'attention' : ''}`}>
                <span>{labels[k] ?? k}</span>
                <strong>{displayMetric(k, v)}</strong>
                {needsAttention(k, v) && <small>需要关注失败样本</small>}
              </article>
            ))}
          </div>
          <p className="eval-note">指标使用固定分母；详细失败样本与环境指纹已写入双格式评测报告。</p>
        </>
      )}
    </div>
  )
}

function Traces() {
  const data = useData(() => api.traces())
  const traces = (data?.traces ?? []) as any[]
  return (
    <table className="table">
      <thead>
        <tr><th>Trace ID</th><th>用户</th><th>意图</th><th>工具调用</th><th>转人工</th><th>Final Answer</th></tr>
      </thead>
      <tbody>
        {traces.map((t) => (
          <tr key={t.trace_id}>
            <td>{t.trace_id?.slice(0, 8)}</td>
            <td>{t.user_id}</td>
            <td>{t.intent ?? '-'}</td>
            <td>{(t.tool_calls ?? []).length}</td>
            <td>{t.handoff_required ? '是' : '否'}</td>
            <td>{t.final_answer?.slice(0, 40)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Audit() {
  const data = useData(() => api.audit())
  const logs = (data?.logs ?? []) as any[]
  return (
    <table className="table">
      <thead>
        <tr><th>操作者</th><th>动作</th><th>资源</th><th>时间</th></tr>
      </thead>
      <tbody>
        {logs.map((l) => (
          <tr key={l.id}>
            <td>{l.actor_user_id}</td><td>{l.action}</td><td>{l.resource_type}/{l.resource_id}</td><td>{l.created_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
