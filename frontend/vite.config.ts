import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 本地开发：/api 代理到后端 FastAPI（含 SSE 流式）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
