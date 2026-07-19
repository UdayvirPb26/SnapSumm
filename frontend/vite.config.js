import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/login': 'http://127.0.0.1:5001',
      '/register': 'http://127.0.0.1:5001',
      '/logout': 'http://127.0.0.1:5001',
      '/guest': 'http://127.0.0.1:5001',
      '/summarize': 'http://127.0.0.1:5001',
      '/translate-summary': 'http://127.0.0.1:5001',
      '/save-summary': 'http://127.0.0.1:5001',
      '/summaries': 'http://127.0.0.1:5001',
      '/summary': 'http://127.0.0.1:5001',
      '/admin': 'http://127.0.0.1:5001',
      '/api': 'http://127.0.0.1:5001',
    },
  },
})