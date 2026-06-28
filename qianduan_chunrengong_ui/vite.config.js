import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/prod-api': {
        target: 'http://192.168.2.57',
        changeOrigin: true,
      },
      '/easy-api': {
        target: 'http://192.168.2.57',
        changeOrigin: true,
      },
      '/flv': {
        target: 'http://127.0.0.1:8088',
        changeOrigin: true,
      },
    },
  },
})
