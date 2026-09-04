import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Console from './pages/Console'
import Admin from './pages/Admin'
import { getUser } from './api'
import './index.css'

function Layout({ children }: { children: React.ReactNode }) {
  const user = getUser()
  return (
    <div className="layout">
      <header className="topbar">
        <a href="/" className="brand">MAINFRAME / PHONE COMMERCE</a>
        <nav>
          {user?.role === 'consumer' && <a href="/chat">客服对话</a>}
          {(user?.role === 'agent' || user?.role === 'supervisor' || user?.role === 'admin') && (
            <a href="/console">客服工作台</a>
          )}
          {user?.role === 'admin' && <a href="/admin">管理后台</a>}
        </nav>
        <span className="me">
          {user?.display_name || user?.user_id}（{user?.role}）
          <a
            href="/login"
            onClick={() => {
              localStorage.removeItem('token')
              localStorage.removeItem('user')
            }}
            style={{ marginLeft: 10 }}
          >
            退出
          </a>
        </span>
      </header>
      <main className="content">{children}</main>
    </div>
  )
}

function RequireRole({ role, children }: { role: string[]; children: React.ReactNode }) {
  const user = getUser()
  if (!user) return <Navigate to="/login" replace />
  if (!role.includes(user.role)) return <div className="denied">无权限访问该页面</div>
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/chat"
          element={
            <RequireRole role={['consumer', 'agent', 'supervisor', 'admin']}>
              <Layout>
                <Chat />
              </Layout>
            </RequireRole>
          }
        />
        <Route
          path="/console"
          element={
            <RequireRole role={['agent', 'supervisor', 'admin']}>
              <Layout>
                <Console />
              </Layout>
            </RequireRole>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireRole role={['admin']}>
              <Layout>
                <Admin />
              </Layout>
            </RequireRole>
          }
        />
        <Route path="/" element={<Navigate to="/chat" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
