import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
export default defineConfig({ plugins: [uni()], server: {
  host: '127.0.0.1',
  proxy: {
    '/api': 'http://127.0.0.1:8000',
    '/media': 'http://127.0.0.1:8000',
    '/static': 'http://127.0.0.1:8000',
  },
} })
