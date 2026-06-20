import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3001,
    proxy: {
      '/api': {
        // TODO: 改成你自己 VM 的 IP 地址
        target: 'http://192.168.44.100:8006',
        changeOrigin: true
      }
    }
  }
})
