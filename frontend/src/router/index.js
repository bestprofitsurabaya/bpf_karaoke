import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeScreen.vue')
  },
  {
    path: '/operator',
    name: 'Operator',
    component: () => import('@/views/OperatorScreen.vue')
  },
  {
    path: '/player',
    name: 'Player',
    component: () => import('@/views/PlayerScreen.vue')
  },
  {
    path: '/remote',
    name: 'Remote',
    component: () => import('@/views/RemoteScreen.vue')
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminScreen.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginScreen.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
