<template>
  <div class="player-screen" @click="toggleControls">
    <!-- Video Player -->
    <div class="video-container" v-if="store.currentSong">
      <div class="video-placeholder">
        <div class="now-playing-display">
          <div class="song-title-big">{{ store.currentSong.song_title || 'Waiting...' }}</div>
          <div class="song-artist-big">{{ store.currentSong.song_artist || '' }}</div>
        </div>
        <div class="next-song" v-if="store.waitingQueue.length > 0">
          <span>Next:</span>
          {{ store.waitingQueue[0]?.song?.title }}
        </div>
      </div>
    </div>

    <!-- No song playing -->
    <div class="idle-screen" v-else>
      <div class="idle-content">
        <div class="logo">🎤</div>
        <h1>BPF Karaoke</h1>
        <p>Scan QR Code untuk request lagu</p>
        <div class="qr-code-placeholder" ref="qrContainer"></div>
        <p class="room-info">Room: {{ store.roomId }}</p>
      </div>
    </div>

    <!-- Floating controls (hidden by default) -->
    <div class="player-controls" v-if="showControls && store.currentSong">
      <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()">
        {{ store.isPlaying ? '⏸' : '▶' }}
      </button>
      <button @click="store.skipSong(store.currentSong?.queue_id)">⏭</button>
      <button @click="cycleVocal()">
        🎤 {{ store.vocalMode }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'

const store = useKaraokeStore()
const showControls = ref(false)
const qrContainer = ref(null)

let controlsTimer

const toggleControls = () => {
  showControls.value = !showControls.value
  if (showControls.value) {
    clearTimeout(controlsTimer)
    controlsTimer = setTimeout(() => {
      showControls.value = false
    }, 5000)
  }
}

const cycleVocal = () => {
  const modes = ['stereo', 'left', 'right']
  const currentIndex = modes.indexOf(store.vocalMode)
  const nextMode = modes[(currentIndex + 1) % modes.length]
  store.toggleVocal(nextMode)
}

onMounted(() => {
  store.fetchQueue()
})

onUnmounted(() => {
  clearTimeout(controlsTimer)
})
</script>

<style scoped>
.player-screen {
  width: 100vw;
  height: 100vh;
  background: #000;
  position: relative;
  cursor: none;
  overflow: hidden;
}

.video-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-placeholder {
  text-align: center;
  color: white;
}

.now-playing-display {
  margin-bottom: 2rem;
}

.song-title-big {
  font-size: 3rem;
  font-weight: 800;
  text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
}

.song-artist-big {
  font-size: 2rem;
  opacity: 0.7;
  margin-top: 0.5rem;
}

.next-song {
  font-size: 1.2rem;
  opacity: 0.5;
}

.next-song span {
  color: #667eea;
  font-weight: 600;
}

.idle-screen {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
}

.idle-content {
  text-align: center;
  color: white;
}

.logo {
  font-size: 5rem;
  margin-bottom: 1rem;
}

.idle-content h1 {
  font-size: 2.5rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.idle-content p {
  font-size: 1.1rem;
  opacity: 0.6;
  margin-bottom: 1.5rem;
}

.qr-code-placeholder {
  width: 200px;
  height: 200px;
  background: white;
  border-radius: 1rem;
  margin: 0 auto 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.room-info {
  font-size: 0.9rem;
  opacity: 0.4;
}

.player-controls {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 1rem;
  background: rgba(0, 0, 0, 0.8);
  padding: 0.75rem 1.5rem;
  border-radius: 2rem;
}

.player-controls button {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 0.75rem 1.25rem;
  border-radius: 1.5rem;
  cursor: pointer;
  font-size: 1rem;
}
</style>
