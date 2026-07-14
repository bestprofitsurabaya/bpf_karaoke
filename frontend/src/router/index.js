import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeScreen.vue'),
    meta: { title: 'BPF Karaoke - Home' }
  },
  {
    path: '/operator',
    name: 'Operator',
    component: () => import('@/views/OperatorScreen.vue'),
    meta: { title: 'BPF Karaoke - Operator' }
  },
  {
    path: '/player',
    name: 'Player',
    component: () => import('@/views/PlayerScreen.vue'),
    meta: { title: 'BPF Karaoke - Player' }
  },
  {
    path: '/remote',
    name: 'Remote',
    component: () => import('@/views/RemoteScreen.vue'),
    meta: { title: 'BPF Karaoke - Remote' }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminScreen.vue'),
    meta: { title: 'BPF Karaoke - Admin', requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginScreen.vue'),
    meta: { title: 'BPF Karaoke - Login', guest: true }
  },
  {
    path: '/force-change-password',
    name: 'ForceChangePassword',
    component: () => import('@/views/ForceChangePassword.vue'),
    meta: { title: 'BPF Karaoke - Ganti Password', requiresTempToken: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() { return { top: 0 } }
})

// Navigation Guard (ISO 27001 A.9.4.1)
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'BPF Karaoke System'
  
  const authToken = localStorage.getItem('auth_token')
  const tempToken = localStorage.getItem('temp_token')
  
  // Halaman yang memerlukan autentikasi admin
  if (to.meta.requiresAuth || to.meta.requiresAdmin) {
    if (!authToken && !tempToken) {
      next('/login')
      return
    }
    
    // Cek apakah token sudah expired (simple check)
    if (authToken) {
      try {
        const payload = JSON.parse(atob(authToken.split('.')[1]))
        if (payload.exp * 1000 < Date.now()) {
          localStorage.removeItem('auth_token')
          next('/login')
          return
        }
      } catch(e) {
        // Token invalid, redirect ke login
        localStorage.removeItem('auth_token')
        next('/login')
        return
      }
    }
    
    next()
    return
  }
  
  // Halaman force-change-password
  if (to.meta.requiresTempToken) {
    if (!tempToken && !authToken) {
      next('/login')
      return
    }
    next()
    return
  }
  
  // Halaman login (hanya untuk guest)
  if (to.meta.guest && authToken) {
    next('/admin')
    return
  }
  
  next()
})

export default router
