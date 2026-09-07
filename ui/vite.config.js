import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: parseInt(process.env.PORT || '5174', 10),
    strictPort: false,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${process.env.BACKEND_PORT || '8080'}`,
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
      }
    }
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    globals: true,
    pool: 'threads',
    testTimeout: 15000,
    maxWorkers: 4,
  },
})
