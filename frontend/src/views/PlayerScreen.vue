<template>
  <div class="player-screen" @click="toggleControls">
    <!-- Animated Background -->
    <div class="bg-animation">
      <div class="bg-orb orb-1"></div>
      <div class="bg-orb orb-2"></div>
      <div class="bg-orb orb-3"></div>
      <div class="bg-particles">
        <span v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)"></span>
      </div>
    </div>

    <!-- ============================================ -->
    <!-- PLAYING STATE -->
    <!-- ============================================ -->
    <div v-if="store.currentSong" class="playing-state">
      <!-- Top Bar -->
      <div class="top-bar">
        <div class="room-info">
          <span class="room-dot"></span>
          Room {{ store.roomId }}
        </div>
        <div class="brand-info">
          <img src="/icons/icon-512x512.png" alt="BPF" class="brand-logo" />
          <span class="brand-text">BPF Karaoke</span>
        </div>
        <div class="time-display">{{ currentTime }}</div>
      </div>

      <!-- Main Content -->
      <div class="playing-main">
        <!-- Album Art -->
        <div class="album-art-section">
          <div class="album-art-container">
            <img src="/icons/icon-512x512.png" alt="Cover" class="album-art" />
            <div class="art-glow"></div>
          </div>
        </div>

        <!-- Song Info -->
        <div class="song-info-section">
          <div class="now-playing-label">
            <span class="np-dot"></span>
            NOW PLAYING
          </div>
          <h1 class="song-title">{{ store.currentSong.song_title || 'Unknown Song' }}</h1>
          <p class="song-artist">{{ store.currentSong.song_artist || 'Unknown Artist' }}</p>
          
          <!-- Progress Bar -->
          <div class="progress-section">
            <span class="time-elapsed">2:15</span>
            <div class="progress-bar">
              <div class="progress-fill"></div>
            </div>
            <span class="time-total">4:30</span>
          </div>

          <!-- Vocal Mode Indicator -->
          <div class="vocal-indicator" v-if="store.vocalMode !== 'stereo'">
            <span class="vocal-icon">🎤</span>
            Vocal: {{ store.vocalMode === 'left' ? 'Kiri' : 'Kanan' }}
          </div>
        </div>
      </div>

      <!-- Next Song Preview -->
      <div class="next-song-bar" v-if="store.waitingQueue.length > 0">
        <div class="next-label">
          <span class="next-icon">🎵</span>
          NEXT:
        </div>
        <div class="next-info">
          <span class="next-title">{{ store.waitingQueue[0]?.song?.title || '...' }}</span>
          <span class="next-separator">•</span>
          <span class="next-artist">{{ store.waitingQueue[0]?.song?.artist || '...' }}</span>
        </div>
        <div class="queue-count-badge">
          {{ store.waitingQueue.length }} lagu
        </div>
      </div>
    </div>

    <!-- ============================================ -->
    <!-- IDLE STATE -->
    <!-- ============================================ -->
    <div v-else class="idle-state">
      <div class="idle-content">
        <!-- Logo -->
        <div class="idle-logo-section">
          <img src="/icons/icon-512x512.png" alt="BPF Karaoke" class="idle-logo" />
          <div class="idle-logo-ring"></div>
        </div>

        <!-- Title -->
        <h1 class="idle-title">
          <span class="text-red">BPF</span>
          <span class="text-blue"> Karaoke</span>
        </h1>
        <p class="idle-subtitle">Best Profit Futures Entertainment</p>

        <!-- QR Code Section -->
        <div class="qr-section">
          <div class="qr-card">
            <div class="qr-code">
              <!-- SVG QR Code Pattern -->
              <svg viewBox="0 0 100 100" class="qr-svg">
                <!-- Outer squares -->
                <rect x="10" y="10" width="30" height="30" rx="4" fill="#ef4444"/>
                <rect x="60" y="10" width="30" height="30" rx="4" fill="#ef4444"/>
                <rect x="10" y="60" width="30" height="30" rx="4" fill="#3b82f6"/>
                <!-- Inner squares -->
                <rect x="17" y="17" width="16" height="16" rx="2" fill="white"/>
                <rect x="67" y="17" width="16" height="16" rx="2" fill="white"/>
                <rect x="17" y="67" width="16" height="16" rx="2" fill="white"/>
                <!-- Center dots -->
                <circle cx="25" cy="25" r="3" fill="#ef4444"/>
                <circle cx="75" cy="25" r="3" fill="#ef4444"/>
                <circle cx="25" cy="75" r="3" fill="#3b82f6"/>
                <!-- Center pattern -->
                <rect x="60" y="60" width="30" height="30" rx="4" fill="#3b82f6"/>
                <rect x="67" y="67" width="16" height="16" rx="2" fill="white"/>
                <circle cx="75" cy="75" r="3" fill="#3b82f6"/>
              </svg>
            </div>
            <p class="qr-text">Scan untuk request lagu</p>
          </div>
        </div>

        <!-- Room Info -->
        <div class="idle-room-info">
          <span class="room-pulse"></span>
          Room: {{ store.roomId }}
        </div>
      </div>
    </div>

    <!-- ============================================ -->
    <!-- FLOATING CONTROLS (Tap to show) -->
    <!-- ============================================ -->
    <transition name="controls-fade">
      <div v-if="showControls && store.currentSong" class="floating-controls">
        <button @click.stop="store.isPlaying ? store.pauseSong() : store.resumeSong()" class="ctrl-btn play-btn">
          <span class="ctrl-icon">{{ store.isPlaying ? '⏸' : '▶' }}</span>
        </button>
        <button @click.stop="store.skipSong(store.currentSong?.queue_id)" class="ctrl-btn">
          <span class="ctrl-icon">⏭</span>
        </button>
        <button @click.stop="cycleVocal" class="ctrl-btn vocal-btn">
          <span class="ctrl-icon">🎤</span>
          <span class="vocal-label">{{ store.vocalMode }}</span>
        </button>
        <div class="volume-control">
          <span class="vol-icon">🔊</span>
          <input 
            type="range" 
            min="0" 
            max="100" 
            :value="store.currentVolume"
            @input="store.setVolume($event.target.value)" 
            @click.stop
            class="vol-slider"
          />
        </div>
      </div>
    </transition>

    <!-- Tap Hint -->
    <transition name="hint-fade">
      <div v-if="!showControls && store.currentSong" class="tap-hint">
        <span class="hint-icon">👆</span>
        Tap layar untuk kontrol
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'

const store = useKaraokeStore()
const showControls = ref(false)
const currentTime = ref('')

let controlsTimer
let clockTimer

// Update clock
const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
}

// Toggle controls on tap
const toggleControls = () => {
  showControls.value = !showControls.value
  if (showControls.value) {
    clearTimeout(controlsTimer)
    controlsTimer = setTimeout(() => {
      showControls.value = false
    }, 5000)
  }
}

// Cycle vocal mode
const cycleVocal = () => {
  const modes = ['stereo', 'left', 'right']
  const currentIndex = modes.indexOf(store.vocalMode)
  const nextMode = modes[(currentIndex + 1) % modes.length]
  store.toggleVocal(nextMode)
}

// Generate random particle styles
const particleStyle = (index) => {
  const colors = ['#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899']
  return {
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    animationDelay: `${Math.random() * 5}s`,
    animationDuration: `${3 + Math.random() * 4}s`,
    background: colors[index % colors.length],
    width: `${2 + Math.random() * 4}px`,
    height: `${2 + Math.random() * 4}px`,
  }
}

onMounted(() => {
  store.fetchQueue()
  store.connectSocket()
  updateClock()
  clockTimer = setInterval(updateClock, 30000)
})

onUnmounted(() => {
  clearTimeout(controlsTimer)
  clearInterval(clockTimer)
})
</script>

<style scoped>
/* ============================================ */
/* BASE */
/* ============================================ */
.player-screen {
  width: 100vw;
  height: 100vh;
  background: #0a0a0f;
  position: relative;
  cursor: none;
  overflow: hidden;
  font-family: 'Poppins', 'Inter', sans-serif;
  color: white;
}

/* ============================================ */
/* BACKGROUND ANIMATION */
/* ============================================ */
.bg-animation {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.15;
  animation: orbFloat 12s ease-in-out infinite;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: #ef4444;
  top: -150px;
  right: -100px;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: #3b82f6;
  bottom: -120px;
  left: -80px;
  animation-delay: 4s;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: #8b5cf6;
  top: 40%;
  left: 40%;
  animation-delay: 8s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -30px) scale(1.1); }
  50% { transform: translate(-20px, 20px) scale(0.9); }
  75% { transform: translate(-30px, -10px) scale(1.05); }
}

.bg-particles {
  position: absolute;
  inset: 0;
}

.particle {
  position: absolute;
  border-radius: 50%;
  animation: particleFloat 4s ease-in-out infinite;
  opacity: 0.3;
}

@keyframes particleFloat {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.3; }
  50% { transform: translateY(-20px) scale(1.5); opacity: 0.6; }
}

/* ============================================ */
/* PLAYING STATE */
/* ============================================ */
.playing-state {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Top Bar */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 2.5rem;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.room-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  font-weight: 500;
  opacity: 0.7;
}

.room-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.brand-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  object-fit: contain;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px;
}

.brand-text {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.time-display {
  font-size: 0.9rem;
  font-weight: 500;
  opacity: 0.6;
  font-variant-numeric: tabular-nums;
}

/* Main Content */
.playing-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4rem;
  padding: 2rem 4rem;
}

/* Album Art */
.album-art-section {
  flex-shrink: 0;
}

.album-art-container {
  position: relative;
  width: 280px;
  height: 280px;
}

.album-art {
  width: 100%;
  height: 100%;
  border-radius: 20px;
  object-fit: contain;
  background: rgba(255, 255, 255, 0.05);
  padding: 15px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
  position: relative;
  z-index: 1;
}

.art-glow {
  position: absolute;
  inset: -20px;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  border-radius: 30px;
  filter: blur(30px);
  opacity: 0.4;
  z-index: 0;
  animation: glowPulse 3s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

/* Song Info */
.song-info-section {
  flex: 1;
  max-width: 600px;
}

.now-playing-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 3px;
  color: #f59e0b;
  margin-bottom: 1rem;
  text-transform: uppercase;
}

.np-dot {
  width: 6px;
  height: 6px;
  background: #f59e0b;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

.song-title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 0.5rem;
  text-shadow: 0 0 40px rgba(239, 68, 68, 0.3);
  word-break: break-word;
}

.song-artist {
  font-size: 1.8rem;
  font-weight: 400;
  opacity: 0.7;
  margin-bottom: 2rem;
}

/* Progress Bar */
.progress-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.time-elapsed,
.time-total {
  font-size: 0.8rem;
  opacity: 0.5;
  font-variant-numeric: tabular-nums;
  min-width: 35px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  width: 48%;
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #3b82f6);
  border-radius: 2px;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  right: 0;
  top: 50%;
  transform: translate(50%, -50%);
  width: 12px;
  height: 12px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}

/* Vocal Indicator */
.vocal-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  font-size: 0.8rem;
  opacity: 0.8;
}

/* Next Song Bar */
.next-song-bar {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.25rem 2.5rem;
  background: rgba(255, 255, 255, 0.03);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.next-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 1px;
  color: #f59e0b;
  text-transform: uppercase;
}

.next-icon {
  font-size: 1rem;
}

.next-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1rem;
}

.next-title {
  font-weight: 600;
}

.next-separator {
  opacity: 0.3;
}

.next-artist {
  opacity: 0.6;
}

.queue-count-badge {
  padding: 0.35rem 0.875rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
  opacity: 0.7;
}

/* ============================================ */
/* IDLE STATE */
/* ============================================ */
.idle-state {
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

.idle-logo-section {
  position: relative;
  display: inline-block;
  margin-bottom: 2rem;
}

.idle-logo {
  width: 140px;
  height: 140px;
  border-radius: 28px;
  object-fit: contain;
  background: rgba(255, 255, 255, 0.05);
  padding: 12px;
  position: relative;
  z-index: 1;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
}

.idle-logo-ring {
  position: absolute;
  inset: -15px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 35px;
  animation: spin 20s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.idle-title {
  font-size: 3.5rem;
  font-weight: 900;
  margin-bottom: 0.5rem;
  font-family: 'Poppins', sans-serif;
}

.text-red { color: #ef4444; }
.text-blue { color: #3b82f6; }

.idle-subtitle {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 2.5rem;
  letter-spacing: 1px;
}

/* QR Section */
.qr-section {
  margin-bottom: 2rem;
}

.qr-card {
  display: inline-block;
  background: white;
  padding: 1.5rem;
  border-radius: 20px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.qr-code {
  width: 180px;
  height: 180px;
}

.qr-svg {
  width: 100%;
  height: 100%;
}

.qr-text {
  margin-top: 1rem;
  font-size: 0.85rem;
  color: #4b5563;
  font-weight: 500;
}

.idle-room-info {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 30px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
}

.room-pulse {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

/* ============================================ */
/* FLOATING CONTROLS */
/* ============================================ */
.floating-controls {
  position: fixed;
  bottom: 2.5rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(15, 15, 25, 0.9);
  backdrop-filter: blur(20px);
  padding: 0.875rem 2rem;
  border-radius: 60px;
  z-index: 100;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.ctrl-btn {
  width: 48px;
  height: 48px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  font-size: 1.1rem;
}

.ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: scale(1.05);
}

.play-btn {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.4);
}

.play-btn:hover {
  box-shadow: 0 6px 30px rgba(239, 68, 68, 0.6);
}

.vocal-btn {
  width: auto;
  padding: 0 1.25rem;
  border-radius: 30px;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.vocal-label {
  text-transform: uppercase;
  font-weight: 600;
  font-size: 0.7rem;
  letter-spacing: 0.5px;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-left: 0.5rem;
}

.vol-icon {
  font-size: 1.1rem;
  opacity: 0.7;
}

.vol-slider {
  width: 100px;
  accent-color: #ef4444;
  cursor: pointer;
}

/* Tap Hint */
.tap-hint {
  position: fixed;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.25);
  z-index: 50;
}

.hint-icon {
  font-size: 1rem;
}

/* ============================================ */
/* TRANSITIONS */
/* ============================================ */
.controls-fade-enter-active,
.controls-fade-leave-active {
  transition: all 0.4s ease;
}

.controls-fade-enter-from,
.controls-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

.hint-fade-enter-active,
.hint-fade-leave-active {
  transition: all 0.3s ease;
}

.hint-fade-enter-from,
.hint-fade-leave-to {
  opacity: 0;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ============================================ */
/* RESPONSIVE */
/* ============================================ */
@media (max-width: 1024px) {
  .playing-main {
    gap: 2rem;
    padding: 1.5rem;
  }
  
  .album-art-container {
    width: 200px;
    height: 200px;
  }
  
  .song-title {
    font-size: 2.5rem;
  }
  
  .song-artist {
    font-size: 1.3rem;
  }
}

@media (max-width: 768px) {
  .playing-main {
    flex-direction: column;
    text-align: center;
    gap: 1.5rem;
  }
  
  .album-art-container {
    width: 160px;
    height: 160px;
  }
  
  .song-title {
    font-size: 2rem;
  }
  
  .song-artist {
    font-size: 1.1rem;
  }
  
  .top-bar {
    padding: 1rem 1.5rem;
  }
  
  .next-song-bar {
    padding: 1rem 1.5rem;
  }
  
  .idle-title {
    font-size: 2.5rem;
  }
  
  .idle-logo {
    width: 100px;
    height: 100px;
  }
  
  .floating-controls {
    padding: 0.75rem 1.5rem;
    gap: 0.75rem;
  }
}
</style>
