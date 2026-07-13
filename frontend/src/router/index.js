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
    meta: { title: 'BPF Karaoke - Admin', requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginScreen.vue'),
    meta: { title: 'BPF Karaoke - Login' }
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
  scrollBehavior() {
    return { top: 0 }
  }
})

// Navigation guard untuk admin
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'BPF Karaoke System'
  
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      next('/login')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
