<template>
  <div id="app" :class="[themeClass, screenClass]">
    <!-- Splash Screen -->
    <div v-if="isLoading" class="splash-screen">
      <div class="splash-content">
        <div class="splash-logo-container">
          <img src="/icons/icon-512x512.png" alt="BPF Karaoke" class="splash-logo-img">
        </div>
        <h1 class="splash-title">
          <span class="text-red">BPF</span>
          <span class="text-blue"> Karaoke</span>
        </h1>
        <p class="splash-subtitle">Best Profit Futures Entertainment System</p>
        <div class="splash-loader">
          <div class="loader-bar"></div>
        </div>
      </div>
    </div>

    <router-view v-slot="{ Component, route }" v-if="!isLoading">
      <transition :name="transitionName" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>

    <div class="toast-container" v-if="toast.show">
      <div :class="['toast', `toast-${toast.type}`]">
        <span class="toast-icon">{{ toastIcon }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="hideToast">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import { useKaraokeStore } from '@/stores/karaoke'

const route = useRoute()
const store = useKaraokeStore()
const isLoading = ref(true)
const toast = ref({ show: false, message: '', type: 'info' })

const themeClass = computed(() => route.query.screen === '2' ? 'theme-player' : 'theme-light')
const screenClass = computed(() => {
  const screen = route.query.screen
  if (screen === '2') return 'player-screen'
  if (screen === 'remote') return 'remote-screen'
  return 'operator-screen'
})
const transitionName = computed(() => 'fade-slide')
const toastIcon = computed(() => toast.value.type === 'success' ? '✅' : toast.value.type === 'error' ? '❌' : 'ℹ️')

const showToast = (message, type = 'info', duration = 3000) => {
  toast.value = { show: true, message, type }
  setTimeout(() => { toast.value.show = false }, duration)
}
const hideToast = () => { toast.value.show = false }

provide('showToast', showToast)

onMounted(() => {
  setTimeout(() => { isLoading.value = false }, 1800)
  const urlParams = new URLSearchParams(window.location.search)
  store.setScreenType(urlParams.get('screen') || 'operator')
  store.setRoomId(urlParams.get('room') || 'default')
  store.connectSocket()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

#app { width: 100vw; height: 100vh; overflow: hidden; }

.theme-light {
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
  color: #1f2937;
}
.theme-player { background: #0a0a0a; color: white; }

/* Splash Screen */
.splash-screen {
  position: fixed; inset: 0; z-index: 9999;
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
  display: flex; align-items: center; justify-content: center;
}
.splash-content { text-align: center; animation: fadeInUp 0.8s ease-out; }
.splash-logo-container { margin-bottom: 1.5rem; }

/* SOLUSI: CSS saja yang atur size, file tetap icon-512x512.png */
.splash-logo-img {
  width: 120px;        /* ← Atur ukuran di sini */
  height: 120px;       /* ← Proporsional */
  border-radius: 24px;
  box-shadow: 0 20px 40px rgba(239,68,68,0.3);
  object-fit: contain; /* ← Menjaga aspect ratio */
  background: white;
  padding: 8px;
}

.splash-title { font-size: 2.5rem; font-weight: 900; font-family: 'Poppins', sans-serif; margin-bottom: 0.5rem; }
.text-red { color: #ef4444; }
.text-blue { color: #3b82f6; }
.splash-subtitle { color: #6b7280; font-size: 1rem; margin-bottom: 2rem; }

.splash-loader {
  width: 200px; height: 4px; background: #e5e7eb;
  border-radius: 2px; margin: 0 auto; overflow: hidden;
}
.loader-bar {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #3b82f6, #ef4444);
  background-size: 200% 100%;
  animation: loading 2s ease-in-out infinite; border-radius: 2px;
}

@keyframes loading {
  0% { width: 0%; background-position: 0% 50%; }
  50% { width: 100%; background-position: 100% 50%; }
  100% { width: 0%; background-position: 0% 50%; }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.4s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateX(30px); }
.fade-slide-leave-to { opacity: 0; transform: translateX(-30px); }

.toast-container { position: fixed; top: 1rem; right: 1rem; z-index: 10000; animation: slideIn 0.4s ease-out; }
@keyframes slideIn {
  from { opacity: 0; transform: translateX(100px); }
  to { opacity: 1; transform: translateX(0); }
}
.toast {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 1rem 1.5rem; border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.15); min-width: 300px; background: white;
}
.toast-success { border-left: 4px solid #10b981; }
.toast-error { border-left: 4px solid #ef4444; }
.toast-info { border-left: 4px solid #3b82f6; }
.toast-icon { font-size: 1.25rem; }
.toast-message { flex: 1; font-weight: 500; }
.toast-close { background: none; border: none; font-size: 1.25rem; cursor: pointer; color: #9ca3af; }
</style>
