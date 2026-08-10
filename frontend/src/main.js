import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'
import axios from 'axios'

// Global axios interceptor: lampirkan JWT ke SEMUA request
// (termasuk komponen yang memakai axios langsung seperti AdminScreen)
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token') || localStorage.getItem('temp_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Global response interceptor: tangani 401 (session expired) & 423 (akun terkunci)
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('temp_token')
      localStorage.removeItem('user')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    if (error.response?.status === 423) {
      const minutes = error.response?.data?.detail?.match(/(\d+)/)?.[1] || '15'
      alert(`Akun terkunci. Silakan coba lagi dalam ${minutes} menit.`)
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')

// NO Service Worker registration
// NO PWA caching
