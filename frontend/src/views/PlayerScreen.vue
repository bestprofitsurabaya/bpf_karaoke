<template>
  <div class="player-screen" @click="toggleControls">
    <!-- Background Animation -->
    <div class="bg-animation">
      <div class="bg-circle c1"></div>
      <div class="bg-circle c2"></div>
      <div class="bg-circle c3"></div>
    </div>

    <!-- Playing State -->
    <div class="video-container" v-if="store.currentSong">
      <div class="now-playing-hero">
        <div class="np-artwork">
          <div class="artwork-circle">
            <span class="artwork-icon">🎤</span>
          </div>
          <div class="artwork-ring"></div>
        </div>
        <div class="np-details">
          <div class="np-badge">NOW PLAYING</div>
          <h1 class="np-song-title">{{ store.currentSong.song_title || 'Unknown Song' }}</h1>
          <p class="np-song-artist">{{ store.currentSong.song_artist || 'Unknown Artist' }}</p>
          <div class="np-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: '45%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Next Song Preview -->
      <div class="next-preview" v-if="store.waitingQueue.length > 0">
        <span class="next-label">🎵 NEXT:</span>
        <span class="next-title">{{ store.waitingQueue[0]?.song?.title }}</span>
        <span class="next-artist">- {{ store.waitingQueue[0]?.song?.artist }}</span>
      </div>
    </div>

    <!-- Idle Screen -->
    <div class="idle-screen" v-else>
      <div class="idle-content">
        <div class="idle-logo">
          <div class="idle-circle">
            <span>🎤</span>
          </div>
        </div>
        <h1 class="idle-title">
          <span class="text-red">BPF</span>
          <span class="text-blue"> Karaoke</span>
        </h1>
        <p class="idle-subtitle">Scan QR Code untuk request lagu dari HP Anda</p>
        <div class="qr-container">
          <div class="qr-box">
            <div class="qr-placeholder">
              <svg viewBox="0 0 100 100" class="qr-svg">
                <rect x="10" y="10" width="80" height="80" rx="5" fill="white"/>
                <rect x="15" y="15" width="30" height="30" fill="#ef4444"/>
                <rect x="55" y="15" width="30" height="30" fill="#ef4444"/>
                <rect x="15" y="55" width="30" height="30" fill="#3b82f6"/>
                <rect x="55" y="55" width="30" height="30" fill="#3b82f6"/>
                <circle cx="30" cy="30" r="5" fill="white"/>
                <circle cx="70" cy="30" r="5" fill="white"/>
                <circle cx="30" cy="70" r="5" fill="white"/>
                <circle cx="70" cy="70" r="5" fill="white"/>
              </svg>
            </div>
          </div>
        </div>
        <div class="room-badge">
          <span class="room-dot"></span>
          Room: {{ store.roomId }}
        </div>
      </div>
    </div>

    <!-- Floating Controls -->
    <div class="player-controls" v-if="showControls && store.currentSong">
      <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()" class="ctrl-main">
        {{ store.isPlaying ? '⏸' : '▶' }}
      </button>
      <button @click="store.skipSong(store.currentSong?.queue_id)" class="ctrl-side">⏭</button>
      <button @click="cycleVocal" class="ctrl-side vocal-btn">
        🎤 <span class="vocal-mode">{{ store.vocalMode }}</span>
      </button>
      <div class="volume-section">
        <span class="vol-icon">🔊</span>
        <input type="range" min="0" max="100" :value="store.currentVolume"
               @input="store.setVolume($event.target.value)" class="vol-slider">
      </div>
    </div>

    <!-- Control Hint -->
    <div class="control-hint" v-if="!showControls && store.currentSong">
      Tap anywhere for controls
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'

const store = useKaraokeStore()
const showControls = ref(false)

let controlsTimer

const toggleControls = () => {
  showControls.value = !showControls.value
  if (showControls.value) {
    clearTimeout(controlsTimer)
    controlsTimer = setTimeout(() => {
      showControls.value = false
    }, 4000)
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
  store.connectSocket()
})

onUnmounted(() => {
  clearTimeout(controlsTimer)
})
</script>

<style scoped>
.player-screen {
  width: 100vw;
  height: 100vh;
  background: #0a0a0a;
  position: relative;
  cursor: none;
  overflow: hidden;
  font-family: 'Poppins', 'Inter', sans-serif;
}

/* Background Animation */
.bg-animation {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
  animation: float 8s ease-in-out infinite;
}

.c1 {
  width: 500px;
  height: 500px;
  background: #ef4444;
  top: -150px;
  right: -100px;
  animation-delay: 0s;
}

.c2 {
  width: 400px;
  height: 400px;
  background: #3b82f6;
  bottom: -100px;
  left: -100px;
  animation-delay: 2s;
}

.c3 {
  width: 300px;
  height: 300px;
  background: #8b5cf6;
  top: 50%;
  left: 50%;
  animation-delay: 4s;
}

/* Playing State */
.video-container {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.now-playing-hero {
  display: flex;
  align-items: center;
  gap: 3rem;
  animation: fadeInUp 0.8s ease-out;
}

.np-artwork {
  position: relative;
}

.artwork-circle {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  background-size: 200% 200%;
  animation: gradient-shift 4s ease infinite;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 20px 60px rgba(239, 68, 68, 0.4);
}

.artwork-icon {
  font-size: 4rem;
  animation: float 3s ease-in-out infinite;
}

.artwork-ring {
  position: absolute;
  inset: -15px;
  border: 3px solid rgba(255,255,255,0.1);
  border-radius: 50%;
  animation: spin 10s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.np-details {
  color: white;
}

.np-badge {
  display: inline-block;
  padding: 0.25rem 1rem;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 20px;
  font-size: 0.7rem;
  letter-spacing: 2px;
  margin-bottom: 1rem;
}

.np-song-title {
  font-size: 3rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  text-shadow: 0 0 40px rgba(239, 68, 68, 0.5);
}

.np-song-artist {
  font-size: 1.5rem;
  font-weight: 400;
  opacity: 0.7;
  margin-bottom: 1.5rem;
}

.np-progress {
  width: 300px;
}

.progress-bar {
  height: 4px;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #3b82f6);
  border-radius: 2px;
  animation: loading 30s linear infinite;
}

/* Next Preview */
.next-preview {
  position: absolute;
  bottom: 2rem;
  background: rgba(255,255,255,0.05);
  backdrop-filter: blur(10px);
  padding: 0.75rem 1.5rem;
  border-radius: 30px;
  color: white;
  font-size: 0.9rem;
  border: 1px solid rgba(255,255,255,0.1);
}

.next-label {
  color: #fbbf24;
  font-weight: 600;
  margin-right: 0.5rem;
}

.next-title {
  font-weight: 600;
}

.next-artist {
  opacity: 0.6;
}

/* Idle Screen */
.idle-screen {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.idle-content {
  text-align: center;
  animation: fadeInUp 0.8s ease-out;
}

.idle-circle {
  width: 150px;
  height: 150px;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  background-size: 200% 200%;
  animation: gradient-shift 4s ease infinite, float 3s ease-in-out infinite;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 2rem;
  box-shadow: 0 20px 60px rgba(239, 68, 68, 0.4);
}

.idle-circle span {
  font-size: 4rem;
}

.idle-title {
  font-size: 3rem;
  font-weight: 900;
  margin-bottom: 0.5rem;
}

.text-red { color: #ef4444; }
.text-blue { color: #3b82f6; }

.idle-subtitle {
  color: rgba(255,255,255,0.6);
  font-size: 1.1rem;
  margin-bottom: 2rem;
}

.qr-container {
  margin-bottom: 1.5rem;
}

.qr-box {
  display: inline-block;
  background: white;
  padding: 1rem;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.qr-placeholder {
  width: 180px;
  height: 180px;
}

.qr-svg {
  width: 100%;
  height: 100%;
}

.room-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.5rem;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 30px;
  color: rgba(255,255,255,0.5);
  font-size: 0.85rem;
}

.room-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
}

/* Player Controls */
.player-controls {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(20px);
  padding: 0.75rem 2rem;
  border-radius: 50px;
  z-index: 100;
  border: 1px solid rgba(255,255,255,0.1);
  animation: fadeInUp 0.3s ease-out;
}

.ctrl-main {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
}

.ctrl-side {
  width: 44px;
  height: 44px;
  background: rgba(255,255,255,0.1);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1rem;
  cursor: pointer;
}

.vocal-btn {
  width: auto;
  padding: 0 1rem;
  border-radius: 30px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.vocal-mode {
  text-transform: uppercase;
  font-weight: 600;
  font-size: 0.7rem;
}

.volume-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.vol-icon {
  font-size: 1.1rem;
}

.vol-slider {
  width: 80px;
  accent-color: #ef4444;
}

/* Hint */
.control-hint {
  position: fixed;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255,255,255,0.3);
  font-size: 0.8rem;
  z-index: 50;
}
</style>
