<template>
  <div class="player-screen" @click="toggleControls">
    <!-- Background -->
    <div class="bg-animation">
      <div class="bg-circle c1"></div>
      <div class="bg-circle c2"></div>
      <div class="bg-circle c3"></div>
    </div>

    <!-- VIDEO PLAYER -->
    <div class="video-container" v-if="store.currentSong && store.isPlaying">
      <video
        ref="videoPlayer"
        :key="store.currentSong.song_id"
        class="video-element"
        autoplay
        controls
        @ended="onVideoEnded"
        @error="onVideoError"
        @loadeddata="onVideoLoaded"
      >
        <source :src="videoSrc" type="video/mp4">
        Your browser does not support the video tag.
      </video>
      
      <div class="video-overlay">
        <div class="np-badge pulse">NOW PLAYING</div>
        <h1 class="np-title">{{ store.currentSong.song_title || 'Loading...' }}</h1>
        <p class="np-artist">{{ store.currentSong.song_artist || '' }}</p>
      </div>
    </div>

    <!-- Next Preview -->
    <div class="next-preview" v-if="store.waitingQueue.length > 0 && store.isPlaying">
      <span class="next-label">🎵 NEXT:</span>
      <span class="next-title">{{ store.waitingQueue[0]?.song?.title }}</span>
    </div>

    <!-- IDLE SCREEN -->
    <div class="idle-screen" v-if="!store.currentSong || !store.isPlaying">
      <div class="idle-content">
        <img src="/icons/icon-512x512.png" alt="BPF Karaoke" class="idle-logo" />
        <h1 class="idle-title">
          <span class="text-red">BPF</span>
          <span class="text-blue"> Karaoke</span>
        </h1>
        <p class="idle-subtitle">Scan QR Code untuk request lagu</p>
        
        <div class="qr-container">
          <canvas ref="qrCanvas" class="qr-canvas"></canvas>
        </div>
        
        <div class="room-badge">
          <span class="room-dot"></span>
          Room: {{ store.roomId }}
        </div>
      </div>
    </div>

    <!-- FLOATING CONTROLS -->
    <div class="player-controls" v-if="showControls">
      <button @click="togglePlay" class="ctrl-main">
        {{ store.isPlaying ? '⏸' : '▶' }}
      </button>
      <button @click="skipCurrent" class="ctrl-side">⏭</button>
      <button @click="cycleVocal" class="ctrl-side vocal-btn">
        🎤 {{ store.vocalMode }}
      </button>
      <div class="volume-section">
        <span>🔊</span>
        <input type="range" min="0" max="100" :value="store.currentVolume"
               @input="store.setVolume(Number($event.target.value))" class="vol-slider">
      </div>
    </div>

    <div class="control-hint" v-if="!showControls && store.currentSong">
      Tap anywhere for controls
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import QRCode from 'qrcode'

const store = useKaraokeStore()
const showControls = ref(false)
const videoPlayer = ref(null)
const qrCanvas = ref(null)

let controlsTimer

// VIDEO SOURCE
const videoSrc = computed(() => {
  if (store.currentSong?.song_id) {
    // Gunakan endpoint streaming
    return `/api/media/stream/${store.currentSong.song_id}`
  }
  return ''
})

// QR Code
const remoteUrl = computed(() => `${window.location.origin}/remote?room=${store.roomId}`)

async function generateQRCode() {
  await nextTick()
  if (qrCanvas.value) {
    try {
      await QRCode.toCanvas(qrCanvas.value, remoteUrl.value, {
        width: 200, margin: 2,
        color: { dark: '#1f2937', light: '#ffffff' }
      })
      console.log('QR Code generated for:', remoteUrl.value)
    } catch (err) {
      console.error('QR generation failed:', err)
    }
  }
}

// Controls
function toggleControls() {
  showControls.value = !showControls.value
  if (showControls.value) {
    clearTimeout(controlsTimer)
    controlsTimer = setTimeout(() => { showControls.value = false }, 5000)
  }
}

function togglePlay() {
  if (store.isPlaying) {
    store.pauseSong()
    videoPlayer.value?.pause()
  } else {
    store.resumeSong()
    videoPlayer.value?.play().catch(e => console.log('Play failed:', e))
  }
}

function skipCurrent() {
  store.skipSong(store.currentSong?.queue_id)
}

function cycleVocal() {
  const modes = ['stereo', 'left', 'right']
  const idx = modes.indexOf(store.vocalMode)
  store.toggleVocal(modes[(idx + 1) % modes.length])
}

function onVideoEnded() {
  console.log('Video ended, auto-skip')
  store.skipSong(store.currentSong?.queue_id)
}

function onVideoError(e) {
  console.error('Video error:', e.target.error?.message || 'Unknown error')
}

function onVideoLoaded() {
  console.log('Video loaded successfully')
  videoPlayer.value?.play().catch(e => console.log('Auto-play blocked:', e))
}

// Watch for new song
watch(() => store.currentSong, async (newSong, oldSong) => {
  if (newSong && newSong.song_id !== oldSong?.song_id) {
    console.log('🔄 Song changed to:', newSong.song_id)
    await nextTick()
    if (videoPlayer.value) {
      videoPlayer.value.load()
      setTimeout(() => {
        videoPlayer.value?.play().catch(e => console.log('Play error:', e))
      }, 500)
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
  clearTimeout(controlsTimer)
})
</script>

<style scoped>
.player-screen {
  width: 100vw; height: 100vh;
  background: #000; position: relative; cursor: none; overflow: hidden;
}
.bg-animation { position: absolute; inset: 0; overflow: hidden; }
.bg-circle { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.15; }
.c1 { width: 500px; height: 500px; background: #ef4444; top: -150px; right: -100px; }
.c2 { width: 400px; height: 400px; background: #3b82f6; bottom: -100px; left: -100px; }
.c3 { width: 300px; height: 300px; background: #8b5cf6; top: 50%; left: 50%; }

.video-container { position: relative; z-index: 1; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.video-element { width: 100%; height: 100%; object-fit: contain; background: #000; }
.video-overlay {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  padding: 3rem 2rem 2rem; color: white; pointer-events: none;
}
.np-badge {
  display: inline-block; padding: 0.25rem 1rem;
  background: rgba(239,68,68,0.8); border-radius: 20px;
  font-size: 0.7rem; letter-spacing: 2px; margin-bottom: 0.75rem;
}
.pulse { animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }
.np-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 0.25rem; text-shadow: 0 2px 10px rgba(0,0,0,0.5); }
.np-artist { font-size: 1.2rem; opacity: 0.8; }

.next-preview {
  position: absolute; bottom: 1.5rem; left: 50%; transform: translateX(-50%);
  background: rgba(0,0,0,0.8); backdrop-filter: blur(10px);
  padding: 0.6rem 1.5rem; border-radius: 30px; color: white;
  z-index: 10; font-size: 0.85rem;
}
.next-label { color: #fbbf24; font-weight: 600; margin-right: 0.5rem; }

.idle-screen {
  position: relative; z-index: 1;
  height: 100%; display: flex; align-items: center; justify-content: center;
}
.idle-content { text-align: center; animation: fadeIn 0.8s ease-out; }
@keyframes fadeIn { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
.idle-logo {
  width: 100px; height: 100px; border-radius: 20px;
  object-fit: contain; background: rgba(255,255,255,0.1);
  padding: 8px; margin: 0 auto 1.5rem;
}
.idle-title { font-size: 2.5rem; font-weight: 900; margin-bottom: 0.5rem; }
.text-red { color: #ef4444; } .text-blue { color: #3b82f6; }
.idle-subtitle { color: rgba(255,255,255,0.6); font-size: 1rem; margin-bottom: 1.5rem; }

.qr-container {
  display: inline-block; background: white; padding: 1rem;
  border-radius: 16px; margin-bottom: 1rem;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.qr-canvas { display: block; }

.room-badge {
  display: inline-flex; align-items: center; gap: 0.5rem;
  padding: 0.4rem 1.2rem; background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 20px; color: rgba(255,255,255,0.6); font-size: 0.8rem;
}
.room-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; }

.player-controls {
  position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 0.75rem;
  background: rgba(0,0,0,0.85); backdrop-filter: blur(20px);
  padding: 0.6rem 1.5rem; border-radius: 50px;
  z-index: 100; border: 1px solid rgba(255,255,255,0.1);
  animation: fadeIn 0.3s ease-out;
}
.ctrl-main {
  width: 50px; height: 50px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: none; border-radius: 50%; color: white;
  font-size: 1.3rem; cursor: pointer;
}
.ctrl-side {
  width: 40px; height: 40px;
  background: rgba(255,255,255,0.15); border: none;
  border-radius: 50%; color: white; cursor: pointer;
}
.vocal-btn { width: auto; padding: 0 1rem; border-radius: 20px; font-size: 0.8rem; }
.volume-section { display: flex; align-items: center; gap: 0.4rem; color: white; }
.vol-slider { width: 80px; accent-color: #ef4444; }

.control-hint {
  position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
  color: rgba(255,255,255,0.25); font-size: 0.8rem; z-index: 50;
}
</style>
