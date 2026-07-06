<template>
  <div id="app" :class="[themeClass, screenClass]">
    <!-- Splash Screen untuk loading -->
    <div v-if="isLoading" class="splash-screen">
      <div class="splash-content">
        <div class="splash-logo">
          <div class="logo-circle">
            <span>🎤</span>
          </div>
        </div>
        <h1 class="splash-title">
          <span class="text-red">BPF</span>
          <span class="text-blue"> Karaoke</span>
        </h1>
        <p class="splash-subtitle">Loading your entertainment...</p>
        <div class="splash-loader">
          <div class="loader-bar"></div>
        </div>
      </div>
    </div>

    <!-- Main App -->
    <router-view v-slot="{ Component, route }" v-if="!isLoading">
      <transition :name="transitionName" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>

    <!-- Toast Notifications -->
    <div class="toast-container" v-if="toast.show">
      <div :class="['toast', `toast-${toast.type}`]">
        <span class="toast-icon">{{ toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️' }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="hideToast">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useKaraokeStore } from '@/stores/karaoke'

const route = useRoute()
const router = useRouter()
const store = useKaraokeStore()
const isLoading = ref(true)
const toast = ref({ show: false, message: '', type: 'info' })

// Theme
const themeClass = computed(() => {
  const screen = route.query.screen
  if (screen === '2') return 'theme-player'
  return 'theme-light'
})

const screenClass = computed(() => {
  const screen = route.query.screen
  if (screen === '2') return 'player-screen'
  if (screen === 'remote') return 'remote-screen'
  return 'operator-screen'
})

const transitionName = computed(() => {
  return 'fade-slide'
})

// Global toast function
const showToast = (message, type = 'info', duration = 3000) => {
  toast.value = { show: true, message, type }
  setTimeout(() => {
    toast.value.show = false
  }, duration)
}

const hideToast = () => {
  toast.value.show = false
}

provide('showToast', showToast)

onMounted(() => {
  // Simulate loading
  setTimeout(() => {
    isLoading.value = false
  }, 1500)

  // Detect screen type
  const urlParams = new URLSearchParams(window.location.search)
  const screen = urlParams.get('screen')
  const roomId = urlParams.get('room') || 'default'

  store.setScreenType(screen || 'operator')
  store.setRoomId(roomId)
  store.connectSocket()
})
</script>

<style>
/* Reset & Base */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

#app {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* Theme Light (Default) */
.theme-light {
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
  color: #1f2937;
}

/* Theme Player (TV) */
.theme-player {
  background: #000;
  color: white;
}

/* Splash Screen */
.splash-screen {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.splash-content {
  text-align: center;
  animation: fadeInUp 0.8s ease-out;
}

.splash-logo {
  margin-bottom: 2rem;
}

.logo-circle {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  animation: float 3s ease-in-out infinite;
  box-shadow: 0 20px 40px rgba(239, 68, 68, 0.3);
}

.logo-circle span {
  font-size: 3rem;
}

.splash-title {
  font-size: 3rem;
  font-weight: 900;
  margin-bottom: 0.5rem;
}

.text-red {
  color: #ef4444;
}

.text-blue {
  color: #3b82f6;
}

.splash-subtitle {
  color: #6b7280;
  font-size: 1.1rem;
  margin-bottom: 2rem;
}

.splash-loader {
  width: 200px;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  margin: 0 auto;
  overflow: hidden;
}

.loader-bar {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #3b82f6, #ef4444);
  background-size: 200% 100%;
  animation: loading 2s ease-in-out infinite;
  border-radius: 2px;
}

@keyframes loading {
  0% { width: 0%; background-position: 0% 50%; }
  50% { width: 100%; background-position: 100% 50%; }
  100% { width: 0%; background-position: 0% 50%; }
}

/* Transitions */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* Toast Notifications */
.toast-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 10000;
  animation: slideRight 0.4s ease-out;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.15);
  min-width: 300px;
  background: white;
}

.toast-success {
  border-left: 4px solid #10b981;
}

.toast-error {
  border-left: 4px solid #ef4444;
}

.toast-info {
  border-left: 4px solid #3b82f6;
}

.toast-icon {
  font-size: 1.25rem;
}

.toast-message {
  flex: 1;
  font-weight: 500;
}

.toast-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #9ca3af;
  padding: 0.25rem;
}
</style>
