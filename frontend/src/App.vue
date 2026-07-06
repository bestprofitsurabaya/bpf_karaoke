<template>
  <div id="app" :class="[screenClass, themeClass]">
    <router-view v-slot="{ Component, route }">
      <transition name="fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useKaraokeStore } from '@/stores/karaoke'

const route = useRoute()
const store = useKaraokeStore()

const screenClass = computed(() => {
  const screen = route.query.screen
  if (screen === '2') return 'player-screen'
  if (screen === 'remote') return 'remote-screen'
  return 'operator-screen'
})

const themeClass = computed(() => {
  return store.isDarkMode ? 'dark-theme' : 'light-theme'
})

onMounted(() => {
  // Deteksi screen type dari URL
  const urlParams = new URLSearchParams(window.location.search)
  const screen = urlParams.get('screen')
  const roomId = urlParams.get('room') || 'default'

  store.setScreenType(screen || 'operator')
  store.setRoomId(roomId)
  store.connectSocket()
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.dark-theme {
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
  color: #e2e8f0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
