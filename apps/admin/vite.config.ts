import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig(({ mode }) => {
  const proxyTarget = loadEnv(mode, '.', 'VITE_API_').VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'
  return { plugins: [vue()], server: { port: 5174, strictPort: true, proxy: {
    '/api': proxyTarget, '/media': proxyTarget, '/static': proxyTarget,
  } } }
})
