import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 8005,
    proxy: {
      '/api': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        // SSE 스트리밍을 위한 설정
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // SSE 요청인 경우 버퍼링 비활성화
            if (req.url?.includes('/query-stream')) {
              proxyReq.setHeader('X-Accel-Buffering', 'no');
            }
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            // SSE 응답인 경우 버퍼링 비활성화
            if (req.url?.includes('/query-stream')) {
              proxyRes.headers['x-accel-buffering'] = 'no';
            }
          });
        }
      }
    }
  }
})