const { defineConfig } = require('vite')
const vue = require('@vitejs/plugin-vue')
const { VitePWA } = require('vite-plugin-pwa')
const path = require('path')

module.exports = defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/icon-512x512.png', 'icons/icon-192x192.png'],
      manifest: {
        name: 'BPF Karaoke System',
        short_name: 'BPF Karaoke',
        description: 'Best Profit Futures Karaoke Entertainment System',
        theme_color: '#ef4444',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'landscape',
        start_url: '/?source=pwa',
        scope: '/',
        icons: [
          {
            src: '/icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 100, maxAgeSeconds: 86400 }
            }
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:5002', changeOrigin: true },
      '/socket.io': { target: 'http://localhost:5002', ws: true, changeOrigin: true },
      '/media': { target: 'http://localhost:5002', changeOrigin: true }
    }
  }
})
