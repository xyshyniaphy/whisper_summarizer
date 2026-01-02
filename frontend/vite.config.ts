import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true
    },
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        // Enable WebSocket support (also helps with SSE streaming)
        ws: true,
        // Configure proxy to NOT buffer SSE responses
        configure: (proxy, options) => {
          proxy.on('proxyRes', (proxyRes: any, req: any, res: any) => {
            // Disable buffering for SSE endpoints
            if (req.url?.includes('/chat/stream') || proxyRes.headers['content-type']?.includes('text/event-stream')) {
              // Ensure no buffering
              delete proxyRes.headers['content-length'];
              // Flush immediately
              proxyRes.headers['x-accel-buffering'] = 'no';
              proxyRes.headers['Cache-Control'] = 'no-cache';
            }
          });
        }
      }
    }
  }
})
