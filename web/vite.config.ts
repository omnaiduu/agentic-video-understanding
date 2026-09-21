import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'

import { tanstackStart } from '@tanstack/react-start/plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const config = defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [devtools(), tailwindcss(), tanstackStart(), viteReact()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,
    hmr: false,
    proxy: {
      '/videos': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 3_600_000,
        proxyTimeout: 3_600_000,
        bypass(req) {
          if (req.method && req.method.toUpperCase() !== 'GET') {
            return
          }
          const accept = String(req.headers.accept ?? '')
          if (accept.includes('application/json')) {
            return
          }
          if (accept.includes('text/html')) {
            return req.url
          }
        },
      },
    },
  },
})

export default config
