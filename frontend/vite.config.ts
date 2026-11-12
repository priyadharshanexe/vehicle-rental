import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/react/' : '/app/',
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(['/api', '/auth', '/accounts', '/media', '/download-receipt'].map(prefix => [
      prefix, 'http://127.0.0.1:8000',
    ])),
  },
}))
