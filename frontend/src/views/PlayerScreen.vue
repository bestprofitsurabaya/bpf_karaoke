<template>
  <div class="player-screen">
    <!-- BACKGROUND AMBIENT -->
    <div class="bg-ambient">
      <div class="bg-blob blob-1"></div>
      <div class="bg-blob blob-2"></div>
    </div>

    <!-- VIDEO FULLSCREEN -->
    <div class="video-fullscreen" v-if="store.currentSong && store.isPlaying">
      <video
        ref="videoPlayer"
        :key="store.currentSong.song_id"
        class="video-element"
        autoplay
        playsinline
        @ended="onVideoEnded"
        @error="onVideoError"
        @loadeddata="onVideoLoaded"
      >
        <source :src="videoSrc" type="video/mp4">
      </video>
      
      <!-- Minimal Now Playing Overlay (fades out after 5s) -->
      <div class="np-overlay" :class="{ 'fade-out': overlayHidden }">
        <div class="np-badge">🎤 NOW PLAYING</div>
        <h1 class="np-title">{{ store.currentSong.song_title || '♪' }}</h1>
        <p class="np-artist">{{ store.currentSong.song_artist || '' }}</p>
      </div>
    </div>

    <!-- NEXT SONG INDICATOR -->
    <div class="next-indicator" v-if="store.waitingQueue.length > 0 && store.isPlaying">
      <span class="next-dot"></span>
      <span class="next-text">Next: {{ store.waitingQueue[0]?.song?.title || '...' }}</span>
    </div>

    <!-- IDLE SCREEN -->
    <div class="idle-screen" v-if="!store.currentSong || !store.isPlaying">
      <div class="idle-inner">
        <!-- Logo -->
        <div class="idle-logo-ring">
          <img src="/icons/icon-512x512.png" alt="BPF" class="idle-logo-img" />
          <div class="logo-glow"></div>
        </div>
        
        <h1 class="idle-brand">
          <span class="brand-red">BPF</span><span class="brand-blue">Karaoke</span>
        </h1>
        
        <p class="idle-tagline">Scan QR untuk request lagu dari HP Anda</p>
        
        <!-- QR Code -->
        <div class="qr-wrapper">
          <canvas ref="qrCanvas" class="qr-canvas"></canvas>
        </div>
        
        <div class="idle-info">
          <div class="info-room">
            <span class="info-dot"></span>
            Room: {{ store.roomId }}
          </div>
          <p class="info-url">{{ remoteUrl }}</p>
        </div>
      </div>
    </div>

    <!-- WAITING SCREEN (song in queue but not playing) -->
    <div class="waiting-screen" v-if="store.currentSong && !store.isPlaying">
      <div class="waiting-inner">
        <div class="waiting-spinner"></div>
        <h2>Menunggu Diputar</h2>
        <p class="waiting-song">{{ store.currentSong.song_title || 'Loading...' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import QRCode from 'qrcode'

const store = useKaraokeStore()
const videoPlayer = ref(null)
const qrCanvas = ref(null)
const overlayHidden = ref(false)

let overlayTimer

// Video source
const videoSrc = computed(() => {
  if (store.currentSong?.song_id) {
    return `/api/media/stream/${store.currentSong.song_id}`
  }
  return ''
})

// Remote URL
const remoteUrl = computed(() => {
  return `${window.location.origin}/remote?room=${store.roomId}`
})

// QR Code Generation
async function generateQRCode() {
  await nextTick()
  if (qrCanvas.value) {
    try {
      await QRCode.toCanvas(qrCanvas.value, remoteUrl.value, {
        width: 220,
        margin: 1,
        color: { dark: '#1e293b', light: '#ffffff' }
      })
    } catch (err) {
      console.error('QR generation failed:', err)
    }
  }
}

// Video event handlers
function onVideoEnded() {
  store.skipSong(store.currentSong?.queue_id)
}

function onVideoError(e) {
  console.error('Video error:', e.target.error?.message)
}

function onVideoLoaded() {
  videoPlayer.value?.play().catch(e => console.log('Autoplay blocked:', e))
  
  // Show overlay, then hide after 5 seconds
  overlayHidden.value = false
  clearTimeout(overlayTimer)
  overlayTimer = setTimeout(() => {
    overlayHidden.value = true
  }, 5000)
}

// Watch for song changes
watch(() => store.currentSong, async (newSong, oldSong) => {
  if (newSong && newSong.song_id !== oldSong?.song_id) {
    overlayHidden.value = false
    clearTimeout(overlayTimer)
    overlayTimer = setTimeout(() => {
      overlayHidden.value = true
    }, 5000)
    
    await nextTick()
    if (videoPlayer.value) {
      videoPlayer.value.load()
      setTimeout(() => {
        videoPlayer.value?.play().catch(e => console.log('Play error:', e))
      }, 300)
    }
  }
})

// Watch play state
watch(() => store.isPlaying, (playing) => {
  if (playing && videoPlayer.value) {
    videoPlayer.value.play().catch(e => console.log('Resume error:', e))
  } else if (!playing && videoPlayer.value) {
    videoPlayer.value.pause()
  }
})

onMounted(async () => {
  store.setScreenType('player')
  store.setRoomId('default')
  store.connectSocket()
  store.fetchQueue()
  
  if (store.socket) {
    store.socket.emit('register', { type: 'player-screen', room_id: store.roomId })
    store.socket.emit('join_room', { type: 'player', room_id: store.roomId })
  }
  
  await generateQRCode()
})

watch(() => store.roomId, async () => {
  await generateQRCode()
})

onUnmounted(() => {
  clearTimeout(overlayTimer)
})
</script>

<style scoped>
/* ============================================ */
/* PLAYER SCREEN - Fullscreen Video Experience  */
/* ============================================ */

.player-screen {
  width: 100vw;
  height: 100vh;
  background: #000;
  position: relative;
  overflow: hidden;
  font-family: 'Inter', system-ui, sans-serif;
}

/* Ambient Background (idle) */
.bg-ambient {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.12;
  animation: blobFloat 12s ease-in-out infinite;
}

.blob-1 {
  width: 600px;
  height: 600px;
  background: #ef4444;
  top: -200px;
  right: -150px;
}

.blob-2 {
  width: 500px;
  height: 500px;
  background: #3b82f6;
  bottom: -150px;
  left: -150px;
  animation-delay: -6s;
}

@keyframes blobFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

/* ============================================ */
/* FULLSCREEN VIDEO */
/* ============================================ */

.video-fullscreen {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

/* Now Playing Overlay */
.np-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4rem 3rem 2.5rem;
  background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 60%, transparent 100%);
  color: white;
  transition: opacity 1s ease;
  pointer-events: none;
}

.np-overlay.fade-out {
  opacity: 0;
}

.np-badge {
  display: inline-block;
  padding: 0.3rem 1rem;
  background: rgba(239, 68, 68, 0.85);
  border-radius: 2rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
  backdrop-filter: blur(10px);
}

.np-title {
  font-size: 2.8rem;
  font-weight: 800;
  letter-spacing: -0.5px;
  text-shadow: 0 2px 20px rgba(0,0,0,0.5);
  margin-bottom: 0.25rem;
}

.np-artist {
  font-size: 1.3rem;
  font-weight: 400;
  opacity: 0.75;
  text-shadow: 0 1px 10px rgba(0,0,0,0.5);
}

/* Next Song Indicator */
.next-indicator {
  position: absolute;
  top: 1.5rem;
  right: 2rem;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(15px);
  padding: 0.5rem 1.2rem;
  border-radius: 2rem;
  color: white;
  font-size: 0.8rem;
  border: 1px solid rgba(255,255,255,0.1);
}

.next-dot {
  width: 7px;
  height: 7px;
  background: #f59e0b;
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.3); }
}

.next-text {
  font-weight: 500;
  opacity: 0.9;
}

/* ============================================ */
/* IDLE SCREEN */
/* ============================================ */

.idle-screen {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1025 50%, #0f0f1a 100%);
}

.idle-inner {
  text-align: center;
  animation: idleFadeIn 1s ease-out;
}

@keyframes idleFadeIn {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Logo */
.idle-logo-ring {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 1.5rem;
}

.idle-logo-img {
  width: 100%;
  height: 100%;
  border-radius: 24px;
  object-fit: contain;
  background: rgba(255,255,255,0.08);
  padding: 12px;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.1);
}

.logo-glow {
  position: absolute;
  inset: -15px;
  border-radius: 36px;
  background: linear-gradient(135deg, rgba(239,68,68,0.3), rgba(59,130,246,0.3));
  filter: blur(20px);
  animation: glowPulse 3s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
}

.idle-brand {
  font-size: 2.8rem;
  font-weight: 900;
  letter-spacing: -1px;
  margin-bottom: 0.5rem;
}

.brand-red { color: #ef4444; }
.brand-blue { color: #3b82f6; }

.idle-tagline {
  color: rgba(255,255,255,0.5);
  font-size: 1rem;
  font-weight: 400;
  margin-bottom: 2rem;
}

/* QR Code */
.qr-wrapper {
  display: inline-block;
  background: white;
  padding: 1.2rem;
  border-radius: 20px;
  margin-bottom: 1.5rem;
  box-shadow: 0 20px 40px rgba(0,0,0,0.4);
}

.qr-canvas {
  display: block;
}

/* Info */
.idle-info {
  color: rgba(255,255,255,0.4);
  font-size: 0.85rem;
}

.info-room {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1rem;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 2rem;
  margin-bottom: 0.5rem;
}

.info-dot {
  width: 7px;
  height: 7px;
  background: #10b981;
  border-radius: 50%;
}

.info-url {
  font-size: 0.75rem;
  word-break: break-all;
}

/* ============================================ */
/* WAITING SCREEN */
/* ============================================ */

.waiting-screen {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.9);
}

.waiting-inner {
  text-align: center;
  color: white;
}

.waiting-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255,255,255,0.15);
  border-top-color: #ef4444;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.waiting-inner h2 {
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  opacity: 0.8;
}

.waiting-song {
  font-size: 1rem;
  opacity: 0.5;
}
</style>
