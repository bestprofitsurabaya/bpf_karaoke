const { defineConfig } = require('vite')
const vue = require('@vitejs/plugin-vue')
const path = require('path')

module.exports = defineConfig({
  plugins: [
    vue()
    // PWA plugin DIHAPUS - tidak butuh caching untuk karaoke
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: 'http://karaoke_backend:5000', changeOrigin: true, secure: false },
      '/socket.io': { target: 'http://karaoke_backend:5000', ws: true, changeOrigin: true },
      '/media': { target: 'http://karaoke_backend:5000', changeOrigin: true }
    }
  },
  build: {
    // Cache busting - tambah hash ke nama file
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  }
})
