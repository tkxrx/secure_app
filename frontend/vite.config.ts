import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // В dev /api проксируется на локальный backend, как nginx в docker.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
