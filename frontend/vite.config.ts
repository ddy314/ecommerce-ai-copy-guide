import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'ant-design',
              test: /node_modules[\\/]ant-design-vue/,
              maxSize: 400_000,
              priority: 30,
            },
            { name: 'motion', test: /node_modules[\\/](motion-v|motion-dom|motion-utils|@vueuse)/, priority: 20 },
            { name: 'vue', test: /node_modules[\\/](@vue|vue)[\\/]/, priority: 10 },
          ],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
