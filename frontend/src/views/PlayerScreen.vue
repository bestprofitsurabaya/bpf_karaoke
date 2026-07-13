<template>
  <div class="player-app" @click="handleInteraction">
    <!-- DYNAMIC BACKGROUND -->
    <div class="bg-layer">
      <div class="bg-particles" ref="particlesRef">
        <span v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)"></span>
      </div>
      <div class="bg-gradient"></div>
      <div class="bg-pulse" v-if="store.isPlaying"></div>
    </div>

    <!-- BRAND WATERMARK (Bottom Right - subtle) -->
    <div class="brand-watermark">
      <img src="/icons/icon-512x512.png" alt="BPF" class="watermark-logo" />
    </div>

    <!-- VIDEO PLAYING STATE -->
    <div class="video-stage" v-if="store.currentSong && store.isPlaying && !isIdle">
      <video 
        ref="videoPlayer" 
        :key="videoKey" 
        class="video-element"
        autoplay 
        playsinline 
        muted
        @ended="onVideoEnded" 
        @error="onVideoError" 
        @loadeddata="onVideoLoaded"
        @play="onPlaySuccess"
      >
        <source :src="videoSrc" type="video/mp4">
      </video>

      <!-- Unmute Prompt -->
      <div class="unmute-prompt" v-if="isMuted" @click.stop="unmuteVideo">
        <div class="unmute-ring">
          <span class="unmute-icon">🔊</span>
        </div>
        <span class="unmute-text">Tap untuk mengaktifkan suara</span>
      </div>

      <!-- Now Playing Overlay -->
      <div class="np-overlay" :class="{ hidden: overlayHidden }">
        <div class="np-top">
          <div class="np-badge">
            <span class="badge-dot"></span>
            NOW PLAYING
          </div>
        </div>
        <div class="np-bottom">
          <h1 class="np-title">{{ store.currentSong.song_title || '♪' }}</h1>
          <p class="np-artist">{{ store.currentSong.song_artist || '' }}</p>
        </div>
      </div>

      <!-- Next Song Ticker -->
      <div class="next-ticker" v-if="store.waitingQueue.length > 0">
        <div class="ticker-content">
          <span class="ticker-label">NEXT:</span>
          <span class="ticker-song">{{ store.waitingQueue[0]?.song?.title || '...' }}</span>
          <span class="ticker-artist">— {{ store.waitingQueue[0]?.song?.artist || '' }}</span>
        </div>
      </div>
    </div>

    <!-- IDLE SCREEN -->
    <div class="idle-stage" v-if="isIdle">
      <!-- Initial State: Welcome -->
      <div class="welcome-view" v-if="!userInteracted">
        <div class="welcome-content">
          <!-- Animated Logo -->
          <div class="welcome-logo-container">
            <img src="/icons/icon-512x512.png" alt="BPF Karaoke" class="welcome-logo" />
            <div class="logo-ripple"></div>
            <div class="logo-ripple delay"></div>
          </div>
          
          <h1 class="welcome-brand">
            <span class="brand-red">BPF</span>
            <span class="brand-blue">Karaoke</span>
          </h1>
          
          <p class="welcome-tagline">Best Profit Futures Entertainment</p>
          
          <!-- Start Button -->
          <button class="start-button" @click.stop="initPlayer">
            <span class="start-icon">▶</span>
            <span>Tap to Start</span>
          </button>
          
          <p class="start-hint">Ketuk layar untuk mengaktifkan audio</p>
        </div>
      </div>

      <!-- Post-Interaction: QR Code -->
      <div class="idle-view" v-else>
        <!-- Countdown Timer -->
        <div class="countdown-stage" v-if="isCountingDown">
          <div class="countdown-ring-container">
            <svg class="countdown-ring" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="6"/>
              <circle cx="60" cy="60" r="52" fill="none" stroke="url(#gradient)" stroke-width="6"
                      :stroke-dasharray="circumference2" :stroke-dashoffset="countdownOffset2"
                      transform="rotate(-90 60 60)" stroke-linecap="round"/>
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#ef4444"/>
                  <stop offset="100%" stop-color="#3b82f6"/>
                </linearGradient>
              </defs>
            </svg>
            <div class="countdown-center">
              <span class="countdown-number">{{ countdownSeconds }}</span>
              <span class="countdown-label">detik</span>
            </div>
          </div>
          <p class="countdown-info">Menyiapkan lagu berikutnya...</p>
        </div>

        <!-- QR Code -->
        <div class="qr-stage" v-else>
          <div class="qr-header">
            <h2>Request Lagu</h2>
            <p>Scan QR Code dari HP Anda</p>
          </div>
          
          <div class="qr-card">
            <div class="qr-card-inner">
              <canvas ref="qrCanvas" class="qr-canvas"></canvas>
            </div>
            <div class="qr-card-glow"></div>
          </div>
          
          <div class="room-info-card">
            <div class="room-info-row">
              <span class="room-dot-live"></span>
              <span>Room: <strong>{{ store.roomId }}</strong></span>
            </div>
            <p class="room-url">{{ remoteUrl }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- PLAY OVERLAY FALLBACK -->
    <div class="play-fallback" v-if="showPlayOverlay" @click.stop="forcePlay">
      <div class="fallback-card">
        <div class="fallback-icon">▶️</div>
        <h2>Tap to Play</h2>
        <p>Ketuk di mana saja untuk memulai pemutaran</p>
      </div>
    </div>

    <!-- WAITING / LOADING -->
    <div class="loading-stage" v-if="store.currentSong && !store.isPlaying && !isIdle">
      <div class="loading-spinner">
        <div class="spinner-ring"></div>
      </div>
      <p class="loading-text">Memuat lagu...</p>
    </div>

    <!-- CLOCK (bottom left) -->
    <div class="clock-display" v-if="!isIdle">
      <span class="clock-time">{{ currentTime }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import QRCode from 'qrcode'

const store = useKaraokeStore()

// Refs
const videoPlayer = ref(null)
const qrCanvas = ref(null)
const particlesRef = ref(null)

// State
const overlayHidden = ref(false)
const isIdle = ref(true)
const isCountingDown = ref(false)
const countdownSeconds = ref(5)
const videoKey = ref(0)
const userInteracted = ref(false)
const isMuted = ref(true)
const showPlayOverlay = ref(false)
const currentTime = ref('')

let overlayTimer, countdownTimer, clockTimer

// Constants
const circumference2 = 2 * Math.PI * 52

// Computed
const videoSrc = computed(() => store.currentSong?.song_id ? `/api/media/stream/${store.currentSong.song_id}` : '')
const remoteUrl = computed(() => `${window.location.origin}/remote?room=${store.roomId}`)
const countdownOffset2 = computed(() => circumference2 - (countdownSeconds.value / 5) * circumference2)

// Clock
function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
}

// Particles
function particleStyle(i) {
  const size = Math.random() * 4 + 2
  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${Math.random() * 100}%`,
    top: `${Math.random() * 100}%`,
    animationDelay: `${Math.random() * 8}s`,
    animationDuration: `${Math.random() * 6 + 4}s`,
    opacity: Math.random() * 0.3 + 0.1,
  }
}

// User Interaction
function handleInteraction() {
  if (!userInteracted.value) {
    userInteracted.value = true
  }
  if (videoPlayer.value && isMuted.value) {
    unmuteVideo()
  }
}

function initPlayer() {
  userInteracted.value = true
  isIdle.value = false
  
  // Audio context untuk permission
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    ctx.resume()
  } catch(e) {}
  
  // Trigger queue fetch
  store.fetchQueue()
  
  setTimeout(() => {
    if (!store.currentSong) {
      isIdle.value = true
      generateQR()
    }
  }, 1000)
}

function unmuteVideo() {
  if (videoPlayer.value) {
    videoPlayer.value.muted = false
    isMuted.value = false
    videoPlayer.value.play().catch(() => {})
  }
}

function forcePlay() {
  showPlayOverlay.value = false
  if (videoPlayer.value) {
    videoPlayer.value.muted = false
    isMuted.value = false
    videoPlayer.value.play().catch(() => {})
  }
}

// QR Code
async function generateQR() {
  await nextTick()
  if (qrCanvas.value) {
    try {
      await QRCode.toCanvas(qrCanvas.value, remoteUrl.value, {
        width: 240, margin: 1,
        color: { dark: '#1e293b', light: '#ffffff' }
      })
    } catch(e) {
      console.error('QR error:', e)
    }
  }
}

// Countdown
function startCountdown() {
  isCountingDown.value = true
  countdownSeconds.value = 5
  clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    countdownSeconds.value--
    if (countdownSeconds.value <= 0) {
      clearInterval(countdownTimer)
      isCountingDown.value = false
    }
  }, 1000)
}

// Video Events
function onVideoEnded() {
  isIdle.value = true
  startCountdown()
  
  if (store.socket && store.isConnected) {
    store.socket.emit('song_ended', {
      room_id: store.roomId,
      queue_id: store.currentSong?.queue_id
    })
  }
}

function onVideoError(e) {
  console.error('Video error:', e.target.error?.message)
  isIdle.value = true
  if (userInteracted.value) generateQR()
}

function onVideoLoaded() {
  if (videoPlayer.value) {
    videoPlayer.value.muted = true
    isMuted.value = true
    videoPlayer.value.play()
      .then(() => {
        if (userInteracted.value) setTimeout(unmuteVideo, 800)
      })
      .catch(() => {
        showPlayOverlay.value = true
      })
  }
  
  overlayHidden.value = false
  clearTimeout(overlayTimer)
  overlayTimer = setTimeout(() => { overlayHidden.value = true }, 6000)
}

function onPlaySuccess() {
  showPlayOverlay.value = false
}

// Socket Events
function setupSocket() {
  if (!store.socket) return
  
  store.socket.on('play', (data) => {
    isIdle.value = false
    isCountingDown.value = false
    clearInterval(countdownTimer)
    showPlayOverlay.value = false
    
    store.currentSong = {
      song_id: data.song_id,
      queue_id: data.queue_id,
      song_title: '',
      song_artist: '',
      auto_play: data.auto_play || false
    }
    store.isPlaying = true
    videoKey.value++
    
    fetchSongDetail(data.song_id)
  })
  
  store.socket.on('ctrl', (data) => {
    if (data.action === 'stop') {
      isIdle.value = true
      store.isPlaying = false
      if (userInteracted.value) generateQR()
    }
  })
  
  store.socket.on('queue_empty', () => {
    isIdle.value = true
    isCountingDown.value = false
    clearInterval(countdownTimer)
    store.currentSong = null
    store.isPlaying = false
    if (userInteracted.value) generateQR()
  })
}

async function fetchSongDetail(songId) {
  try {
    const res = await fetch(`/api/songs?limit=1000`)
    const songs = await res.json()
    const song = songs.find(s => s.id === songId)
    if (song && store.currentSong) {
      store.currentSong.song_title = song.title
      store.currentSong.song_artist = song.artist || ''
    }
  } catch(e) {}
}

// Watch idle state
watch(isIdle, async (idle) => {
  if (idle && !isCountingDown.value && userInteracted.value) {
    await nextTick()
    await generateQR()
  }
})

watch(() => store.roomId, async () => {
  if (userInteracted.value) await generateQR()
})

// Lifecycle
onMounted(async () => {
  store.setScreenType('player')
  // Read room from URL parameter
  const urlParams = new URLSearchParams(window.location.search)
  const roomParam = urlParams.get('room') || localStorage.getItem('karaoke_room') || 'Room 1'
  store.setRoomId(roomParam)
  store.connectSocket()
  store.fetchQueue()
  setupSocket()
  
  if (store.socket) {
    store.socket.emit('register', { type: 'player-screen', room_id: store.roomId })
    store.socket.emit('join_room', { type: 'player', room_id: store.roomId })
  }
  
  updateClock()
  clockTimer = setInterval(updateClock, 10000)
})

onUnmounted(() => {
  clearTimeout(overlayTimer)
  clearInterval(countdownTimer)
  clearInterval(clockTimer)
})
</script>

<style scoped>
.player-app {
  width: 100vw;
  height: 100vh;
  background: #060608;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
}

/* BACKGROUND */
.bg-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.bg-gradient {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at center, rgba(15,15,25,0.6) 0%, rgba(6,6,8,0.95) 100%);
}

.bg-pulse {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 50%, rgba(239,68,68,0.05) 0%, transparent 70%);
  animation: bgPulse 4s ease-in-out infinite;
}

@keyframes bgPulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}

.bg-particles {
  position: absolute;
  inset: 0;
}

.particle {
  position: absolute;
  background: rgba(255,255,255,0.3);
  border-radius: 50%;
  animation: floatUp 6s ease-in-out infinite;
}

@keyframes floatUp {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.2; }
  25% { transform: translateY(-30px) translateX(15px); opacity: 0.4; }
  50% { transform: translateY(-60px) translateX(-10px); opacity: 0.1; }
  75% { transform: translateY(-30px) translateX(-20px); opacity: 0.3; }
}

/* BRAND WATERMARK */
.brand-watermark {
  position: absolute;
  bottom: 1.5rem;
  right: 2rem;
  z-index: 5;
  opacity: 0.15;
  pointer-events: none;
}

.watermark-logo {
  width: 60px;
  height: 60px;
  object-fit: contain;
}

/* CLOCK */
.clock-display {
  position: absolute;
  bottom: 1.5rem;
  left: 2rem;
  z-index: 5;
  color: rgba(255,255,255,0.3);
  font-size: 0.9rem;
  font-weight: 300;
  letter-spacing: 1px;
  pointer-events: none;
}

/* VIDEO STAGE */
.video-stage {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* UNMUTE PROMPT */
.unmute-prompt {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  text-align: center;
  cursor: pointer;
  animation: fadeInUp 0.5s ease-out;
}

.unmute-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(239,68,68,0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 0.75rem;
  box-shadow: 0 0 40px rgba(239,68,68,0.4);
  animation: pulse 2s infinite;
}

.unmute-icon {
  font-size: 2rem;
}

.unmute-text {
  color: white;
  font-size: 0.9rem;
  font-weight: 500;
  text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(239,68,68,0.4); }
  50% { box-shadow: 0 0 60px rgba(239,68,68,0.8); }
}

/* NOW PLAYING OVERLAY */
.np-overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  transition: opacity 1.5s ease;
}

.np-overlay.hidden {
  opacity: 0;
}

.np-top {
  position: absolute;
  top: 2rem;
  left: 2rem;
}

.np-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1.2rem;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(20px);
  border-radius: 2rem;
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 2px;
  border: 1px solid rgba(255,255,255,0.1);
}

.badge-dot {
  width: 6px;
  height: 6px;
  background: #ef4444;
  border-radius: 50%;
  animation: dotPulse 1.5s infinite;
}

@keyframes dotPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.np-bottom {
  position: absolute;
  bottom: 3rem;
  left: 2rem;
  right: 2rem;
}

.np-title {
  font-size: 3rem;
  font-weight: 800;
  color: white;
  text-shadow: 0 4px 30px rgba(0,0,0,0.6);
  line-height: 1.1;
  margin-bottom: 0.5rem;
}

.np-artist {
  font-size: 1.4rem;
  color: rgba(255,255,255,0.75);
  text-shadow: 0 2px 15px rgba(0,0,0,0.5);
  font-weight: 400;
}

/* NEXT TICKER */
.next-ticker {
  position: absolute;
  top: 2rem;
  right: 2rem;
  z-index: 4;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(15px);
  padding: 0.5rem 1rem;
  border-radius: 2rem;
  border: 1px solid rgba(255,255,255,0.08);
  max-width: 300px;
  overflow: hidden;
}

.ticker-content {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  white-space: nowrap;
}

.ticker-label {
  color: #f59e0b;
  font-weight: 700;
  font-size: 0.65rem;
}

.ticker-song {
  color: white;
  font-weight: 500;
}

.ticker-artist {
  color: rgba(255,255,255,0.5);
}

/* IDLE STAGE */
.idle-stage {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(ellipse at center, #0f0f1a 0%, #060608 100%);
}

/* WELCOME VIEW */
.welcome-content {
  text-align: center;
  animation: fadeInUp 1s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}

.welcome-logo-container {
  position: relative;
  width: 130px;
  height: 130px;
  margin: 0 auto 2rem;
}

.welcome-logo {
  width: 100%;
  height: 100%;
  border-radius: 28px;
  object-fit: contain;
  background: rgba(255,255,255,0.06);
  padding: 14px;
  position: relative;
  z-index: 1;
  border: 1px solid rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
}

.logo-ripple {
  position: absolute;
  inset: -20px;
  border-radius: 40px;
  border: 2px solid rgba(239,68,68,0.3);
  animation: ripple 3s ease-out infinite;
}

.logo-ripple.delay {
  animation-delay: 1.5s;
}

@keyframes ripple {
  0% { transform: scale(0.9); opacity: 0.8; }
  100% { transform: scale(1.3); opacity: 0; }
}

.welcome-brand {
  font-size: 3rem;
  font-weight: 900;
  letter-spacing: -1px;
  margin-bottom: 0.5rem;
}

.brand-red { color: #ef4444; }
.brand-blue { color: #3b82f6; }

.welcome-tagline {
  color: rgba(255,255,255,0.35);
  font-size: 0.95rem;
  margin-bottom: 2.5rem;
  letter-spacing: 0.5px;
}

/* START BUTTON */
.start-button {
  padding: 1rem 3rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border: none;
  border-radius: 4rem;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  box-shadow: 0 15px 40px rgba(239,68,68,0.4);
  transition: all 0.3s;
  animation: pulse 2s infinite;
}

.start-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 50px rgba(239,68,68,0.5);
}

.start-icon {
  font-size: 1.5rem;
}

.start-hint {
  color: rgba(255,255,255,0.2);
  font-size: 0.8rem;
  margin-top: 1rem;
}

/* COUNTDOWN */
.countdown-stage {
  text-align: center;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.countdown-ring-container {
  width: 120px;
  height: 120px;
  position: relative;
  margin: 0 auto 1.5rem;
}

.countdown-ring {
  width: 100%;
  height: 100%;
}

.countdown-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.countdown-number {
  font-size: 2.5rem;
  font-weight: 800;
  color: white;
  line-height: 1;
}

.countdown-label {
  font-size: 0.7rem;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.countdown-info {
  color: rgba(255,255,255,0.4);
  font-size: 0.9rem;
}

/* QR STAGE */
.qr-stage {
  text-align: center;
  animation: fadeIn 0.5s ease-out;
}

.qr-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: white;
  margin-bottom: 0.25rem;
}

.qr-header p {
  color: rgba(255,255,255,0.4);
  font-size: 0.85rem;
  margin-bottom: 1.5rem;
}

.qr-card {
  position: relative;
  display: inline-block;
  margin-bottom: 1.5rem;
}

.qr-card-inner {
  background: white;
  padding: 1.2rem;
  border-radius: 20px;
  position: relative;
  z-index: 1;
}

.qr-canvas {
  display: block;
  width: 200px;
  height: 200px;
}

.qr-card-glow {
  position: absolute;
  inset: -10px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(239,68,68,0.3), rgba(59,130,246,0.3));
  filter: blur(20px);
  animation: glowShift 4s ease-in-out infinite;
}

@keyframes glowShift {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}

.room-info-card {
  text-align: center;
}

.room-info-row {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1rem;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 2rem;
  color: rgba(255,255,255,0.6);
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
}

.room-dot-live {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
}

.room-url {
  color: rgba(255,255,255,0.25);
  font-size: 0.7rem;
  word-break: break-all;
}

/* PLAY FALLBACK */
.play-fallback {
  position: absolute;
  inset: 0;
  z-index: 20;
  background: rgba(0,0,0,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

.fallback-card {
  text-align: center;
  color: white;
}

.fallback-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  animation: pulse 2s infinite;
}

.fallback-card h2 {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.fallback-card p {
  color: rgba(255,255,255,0.5);
  font-size: 0.9rem;
}

/* LOADING */
.loading-stage {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.9);
}

.loading-spinner {
  margin-bottom: 1rem;
}

.spinner-ring {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #ef4444;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: rgba(255,255,255,0.5);
  font-size: 0.9rem;
}
</style>
