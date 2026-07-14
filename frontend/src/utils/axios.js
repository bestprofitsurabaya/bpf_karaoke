import axios from 'axios'
import router from '@/router'

// Create axios instance
const api = axios.create({
  baseURL: '/',
  timeout: 30000,
})

// Request interceptor - attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token') || localStorage.getItem('temp_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('temp_token')
      localStorage.removeItem('user')
      
      // Jangan redirect jika sudah di halaman login
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    
    // Handle 423 Locked (account locked)
    if (error.response?.status === 423) {
      const minutes = error.response?.data?.detail?.match(/(\d+)/)?.[1] || '15'
      alert(`Akun terkunci. Silakan coba lagi dalam ${minutes} menit.`)
    }
    
    return Promise.reject(error)
  }
)

export default api
