import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server forwards /api/* to FastAPI, so the browser talks to one
// origin and the API needs no CORS configuration.
const API_TARGET = process.env.API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': { target: API_TARGET, changeOrigin: true } },
  },
  preview: {
    proxy: { '/api': { target: API_TARGET, changeOrigin: true } },
  },
})
