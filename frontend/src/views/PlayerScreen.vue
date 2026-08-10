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
      <!-- Lagu YouTube: putar via embed (youtube-nocookie) -->
      <div v-if="currentYoutubeId" class="yt-player-stage">
        <div ref="ytPlayerEl" class="yt-player-el"></div>
      </div>
      <template v-else>
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
      </template>

      <!-- Now Playing Overlay -->
      <div class="np-overlay" :class="{ hidden: overlayHidden }">
        <div class="np-top">
          <div class="np-badge">
            <span class="badge-dot"></span>
            NOW PLAYING
            <span class="eq-bars" aria-hidden="true"><i v-for="n in 4" :key="n"></i></span>
          </div>
        </div>
        <div class="np-bottom">
          <h1 class="np-title">{{ store.currentSong.song_title || '♪' }}</h1>
          <p class="np-artist">{{ store.currentSong.song_artist || '' }}</p>
        </div>
      </div>

      <!-- Progress bar tipis (gaya TV karaoke komersial) -->
      <div class="player-progress" aria-hidden="true">
        <div class="pp-fill" :style="{ width: progressPct + '%' }"></div>
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

        <!-- Sesi Berakhir -->
        <div class="session-ended" v-else-if="sessionEnded">
          <div class="se-icon">🎤</div>
          <h2 class="se-title">Sesi Berakhir</h2>
          <p class="se-sub">Terima kasih telah bernyanyi di BPF Karaoke!</p>
        </div>

        <!-- QR Code -->
        <div class="qr-stage" v-else>
          <div class="qr-header">
            <h2>Request Lagu</h2>
            <p>Scan QR Code dari HP Anda</p>
            <div class="idle-queue-chip" v-if="store.waitingQueue.length > 0">
              🎵 <strong>{{ store.waitingQueue.length }}</strong> lagu dalam antrian
            </div>
            <div class="idle-next-card" v-if="store.waitingQueue.length > 0">
              <span class="in-label">LAGU BERIKUTNYA</span>
              <span class="in-title">{{ store.waitingQueue[0]?.song?.title || '...' }}</span>
              <span class="in-artist">— {{ store.waitingQueue[0]?.song?.artist || '' }}</span>
            </div>
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

    <!-- ROOM SESSION COUNTDOWN (untuk tamu di TV) -->
    <div class="session-timer" v-if="store.roomSession?.active && store.roomSession.session?.end_time" :class="{ urgent: sessionUrgent }">
      <span class="st-label">⏱️ SISA WAKTU</span>
      <span class="st-value">{{ formatRemaining(sessionRemaining) }}</span>
      <span class="st-end">Berakhir {{ formatEndTime(store.roomSession.session?.end_time) }}</span>
    </div>

    <!-- PERINGATAN SISA 5 MENIT (banner besar + beep) -->
    <transition name="warn-pop">
      <div class="session-warning" v-if="sessionWarning">
        <span class="sw-icon">⚠️</span>
        <div class="sw-text">
          <span class="sw-title">WAKTU SESI HAMPIR HABIS</span>
          <span class="sw-sub">Sesi berakhir dalam <strong>{{ formatRemaining(sessionRemaining) }}</strong></span>
        </div>
      </div>
    </transition>

    <!-- CLOCK (bottom left) -->
    <div class="clock-display" v-if="!isIdle">
      <span class="clock-time">{{ currentTime }}</span>
    </div>

    <!-- VOLUME OSD (muncul singkat saat operator ubah volume) -->
    <transition name="osd-fade">
      <div class="volume-osd" v-if="volumeOsd">
        <span class="osd-icon">{{ store.currentVolume === 0 ? '🔇' : '🔊' }}</span>
        <div class="osd-track"><div class="osd-fill" :style="{ width: store.currentVolume + '%' }"></div></div>
        <span class="osd-val">{{ store.currentVolume }}%</span>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import { formatRemaining, formatEndTime } from '@/utils/helpers'
import QRCode from 'qrcode'

const store = useKaraokeStore()

// Refs
const videoPlayer = ref(null)
const qrCanvas = ref(null)
const particlesRef = ref(null)
const ytPlayerEl = ref(null)

// YouTube embed player (lagu yang tidak ada di database)
const currentYoutubeId = computed(() => {
  const cs = store.currentSong
  return cs && cs.file_format === 'youtube' && cs.youtube_id ? cs.youtube_id : ''
})
let ytPlayer = null
let ytApiReady = false
let ytErrorStreak = 0

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
const progressPct = ref(0)
const volumeOsd = ref(false)
const sessionEnded = ref(false)

let overlayTimer, countdownTimer, clockTimer, volumeOsdTimer

// Web Audio untuk vocal channel routing (Kiri/Kanan/Stereo)
// SATU AudioContext dipakai bersama (dibuat/diresume dalam user gesture)
let audioCtx = null
let sourceNode = null
let splitterNode = null
let mergerNode = null
let graphElement = null
let pendingSeek = 0

// Countdown sesi room (durasi pemakaian) untuk tamu
const sessionNow = ref(Date.now())
let sessionTimer = null

const sessionRemaining = computed(() => {
  const s = store.roomSession?.session
  if (!store.roomSession?.active || !s?.end_time) return 0
  const end = new Date(s.end_time).getTime()
  return Math.max(0, Math.floor((end - sessionNow.value) / 1000))
})
const sessionUrgent = computed(() => sessionRemaining.value > 0 && sessionRemaining.value <= 300)

// Peringatan visual + bunyi saat sisa 5 menit (trigger satu kali per sesi)
const sessionWarning = ref(false)
const sessionWarningShown = ref(false)
let sessionWarningTimer = null

function playBeep(type = 'warning') {
  // Gunakan AudioContext yang sama (sudah dibuat saat user gesture). Jika
  // belum ada/belum resume, abaikan pelan-pelan — visual tetap tampil.
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    if (audioCtx.state === 'suspended') audioCtx.resume()
    const now = audioCtx.currentTime
    const notes = type === 'end' ? [1046, 784, 523] : [1046, 1046, 784]  // C6 C6 G5 (warning) / C6 G5 C5 (end)
    notes.forEach((freq, i) => {
      const osc = audioCtx.createOscillator()
      const gain = audioCtx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      const t0 = now + i * 0.28
      gain.gain.setValueAtTime(0.0001, t0)
      gain.gain.exponentialRampToValueAtTime(0.35, t0 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.25)
      osc.connect(gain).connect(audioCtx.destination)
      osc.start(t0)
      osc.stop(t0 + 0.3)
    })
  } catch (e) { /* autoplay policy: visual tetap tampil */ }
}

function showSessionWarning() {
  if (sessionWarningShown.value || !store.roomSession?.active) return
  sessionWarningShown.value = true
  sessionWarning.value = true
  playBeep('warning')
  clearTimeout(sessionWarningTimer)
  // Banner tampil ~20 detik, lalu hilang (timer countdown tetap terlihat & berdenyut)
  sessionWarningTimer = setTimeout(() => { sessionWarning.value = false }, 20000)
}

function hideSessionWarning() {
  sessionWarningShown.value = false
  sessionWarning.value = false
  clearTimeout(sessionWarningTimer)
}

// Constants
const circumference2 = 2 * Math.PI * 52

// Computed
const videoSrc = computed(() => store.currentSong?.song_id ? `/api/media/stream/${store.currentSong.song_id}?key=${store.keyShift}` : '')
const remoteUrl = computed(() => `${window.location.origin}/remote?room=${store.roomId}`)
const countdownOffset2 = computed(() => circumference2 - (countdownSeconds.value / 5) * circumference2)

// Clock
function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' })
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
  // Resume AudioContext dalam user gesture (wajib untuk iOS/Chrome)
  resumeAudioContext()
  if (videoPlayer.value && isMuted.value) {
    unmuteVideo()
  }
}

function resumeAudioContext() {
  try {
    if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume()
  } catch(e) {}
}

function initPlayer() {
  userInteracted.value = true
  isIdle.value = false
  
  // Buat & resume SATU AudioContext dalam user gesture (dipakai juga
  // untuk vocal channel routing). Jangan buat context baru di luar gesture.
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    audioCtx.resume()
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
    resumeAudioContext()
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
  stopProgressEmitter()
  progressPct.value = 100
  isIdle.value = true
  startCountdown()
  
  if (store.socket && store.isConnected) {
    store.socket.emit('song_ended', {
      room_id: store.roomId,
      queue_id: store.currentSong?.queue_id
    })
  }
}

// ============================================
// YOUTUBE EMBED PLAYBACK (YouTube IFrame API)
// ============================================
function loadYouTubeApi() {
  if (window.YT && window.YT.Player) { ytApiReady = true; return }
  if (document.getElementById('yt-iframe-api')) return
  const tag = document.createElement('script')
  tag.id = 'yt-iframe-api'
  tag.src = 'https://www.youtube.com/iframe_api'
  document.head.appendChild(tag)
  window.onYouTubeIframeAPIReady = () => { ytApiReady = true; tryCreateYtPlayer() }
}

function destroyYtPlayer() {
  if (ytPlayer) {
    try { ytPlayer.destroy() } catch (e) {}
    ytPlayer = null
  }
}

function tryCreateYtPlayer() {
  const id = currentYoutubeId.value
  if (!id || !ytApiReady || !ytPlayerEl.value || !window.YT?.Player) return
  ytErrorStreak = 0
  destroyYtPlayer()
  ytPlayer = new window.YT.Player(ytPlayerEl.value, {
    videoId: id,
    playerVars: {
      autoplay: 1,
      rel: 0,
      playsinline: 1,
      modestbranding: 1,
      origin: window.location.origin
    },
    events: {
      onReady: (e) => {
        try { e.target.playVideo() } catch (err) {}
        startProgressEmitter()
      },
      onStateChange: (e) => {
        // YT states: 0=ended, 1=playing, 2=paused, 3=buffering
        if (e.data === 0) onYtEnded()
        else if (e.data === 1) { ytErrorStreak = 0; showPlayOverlay.value = false; store.isPlaying = true }
      },
      onError: () => {
        // Video tidak tersedia (private/deleted). 3x gagal beruntun -> skip
        // lagu ini (jangan auto-advance terus menerus melewati antrian rusak).
        ytErrorStreak++
        if (ytErrorStreak >= 3) {
          ytErrorStreak = 0
          stopProgressEmitter()
          destroyYtPlayer()
          isIdle.value = true
          store.isPlaying = false
          if (store.socket && store.isConnected) {
            store.socket.emit('skip_song', {
              room_id: store.roomId,
              queue_id: store.currentSong?.queue_id
            })
          }
        } else {
          onYtEnded()
        }
      }
    }
  })
}

function onYtEnded() {
  stopProgressEmitter()
  destroyYtPlayer()
  isIdle.value = true
  startCountdown()
  if (store.socket && store.isConnected) {
    store.socket.emit('song_ended', {
      room_id: store.roomId,
      queue_id: store.currentSong?.queue_id
    })
  }
}

// Buat/hancurkan player YouTube saat lagu berganti atau di-resume
watch(currentYoutubeId, async (id) => {
  if (id) {
    isIdle.value = false
    await nextTick()
    loadYouTubeApi()
    tryCreateYtPlayer()
  } else {
    stopProgressEmitter()
    destroyYtPlayer()
  }
})

watch(() => store.isPlaying, (playing) => {
  // Setelah pause (iframe terlepas dari DOM) -> buat ulang saat resume
  if (playing && currentYoutubeId.value) {
    nextTick(() => { loadYouTubeApi(); tryCreateYtPlayer() })
  }
})

function onVideoError(e) {
  const code = e.target?.error?.code
  console.error('Video error:', code, e.target.error?.message)
  stopProgressEmitter()
  isIdle.value = true
  if (userInteracted.value) generateQR()
  // ANTI-NYANGKUT: lagu gagal dimuat harus tetap maju ke lagu berikutnya.
  // Hanya error FATAL (2=network, 4=src tidak didukung) yang memajukan lagu;
  // MEDIA_ERR_ABORTED (1) terjadi saat elemen diganti normal (ganti pitch/key).
  const fatal = code === 2 || code === 4
  if (fatal && store.socket && store.isConnected && store.currentSong?.queue_id) {
    store.socket.emit('song_ended', {
      room_id: store.roomId,
      queue_id: store.currentSong.queue_id
    })
  }
}


// Emit playback progress setiap 1 detik (video lokal ATAU YouTube)
let progressInterval
function startProgressEmitter() {
  clearInterval(progressInterval)
  progressInterval = setInterval(() => {
    if (!store.isPlaying) return
    if (currentYoutubeId.value && ytPlayer && typeof ytPlayer.getCurrentTime === 'function') {
      try {
        const current = ytPlayer.getCurrentTime() || 0
        const duration = ytPlayer.getDuration() || 0
        const pct = duration > 0 ? (current / duration) * 100 : 0
        progressPct.value = pct
        if (store.socket && store.isConnected) {
          store.socket.emit('playback_progress', {
            room_id: store.roomId,
            current_time: current,
            duration: duration,
            percentage: pct,
            song_id: store.currentSong?.song_id
          })
        }
      } catch (e) {}
    } else if (videoPlayer.value) {
      const current = videoPlayer.value.currentTime || 0
      const duration = videoPlayer.value.duration || 0
      const pct = duration > 0 ? (current / duration) * 100 : 0
      progressPct.value = pct
      if (store.socket && store.isConnected) {
        store.socket.emit('playback_progress', {
          room_id: store.roomId,
          current_time: current,
          duration: duration,
          percentage: pct,
          song_id: store.currentSong?.song_id
        })
      }
    }
  }, 1000)
}
function stopProgressEmitter() {
  clearInterval(progressInterval)
}

function onVideoLoaded() {
  if (videoPlayer.value) {
    videoPlayer.value.muted = true
    isMuted.value = true
    // Terapkan volume room & vocal mode pada elemen video baru
    videoPlayer.value.volume = Math.max(0, Math.min(1, (store.currentVolume || 80) / 100))
    if (store.vocalMode && store.vocalMode !== 'stereo') ensureAudioGraph()
    // Kembalikan posisi playback setelah reload (mis. saat pitch/key berubah)
    if (pendingSeek > 0) {
      try { videoPlayer.value.currentTime = pendingSeek } catch (e) {}
      pendingSeek = 0
    }
    videoPlayer.value.play()
      .then(() => {
        if (userInteracted.value) setTimeout(unmuteVideo, 800)
      })
      .catch(() => {
        showPlayOverlay.value = true
      })
    startProgressEmitter()
  }
  
  overlayHidden.value = false
  clearTimeout(overlayTimer)
  overlayTimer = setTimeout(() => { overlayHidden.value = true }, 6000)
}

function onPlaySuccess() {
  showPlayOverlay.value = false
}

// ============================================
// WEB AUDIO - VOCAL CHANNEL ROUTING
// Stereo = 2 kanal, Kiri = hanya kanal 0, Kanan = hanya kanal 1
// ============================================
function ensureAudioGraph() {
  const el = videoPlayer.value
  if (!el) return
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  }
  if (audioCtx.state === 'suspended') audioCtx.resume()

  // Elemen video baru -> buat source baru (1 source per elemen)
  if (sourceNode && graphElement !== el) {
    try { sourceNode.disconnect() } catch (e) {}
    sourceNode = null
    splitterNode = null
  }

  if (!sourceNode) {
    try {
      sourceNode = audioCtx.createMediaElementSource(el)
      graphElement = el
      splitterNode = audioCtx.createChannelSplitter(2)
      sourceNode.connect(splitterNode)
    } catch (e) {
      console.error('Audio graph error:', e)
      return
    }
  }
  applyVocalRouting()
}

function applyVocalRouting() {
  if (!audioCtx || !splitterNode) return
  try { splitterNode.disconnect() } catch (e) {}
  // Lepas merger lama agar tidak bocor (tetap tersambung ke destination)
  if (mergerNode) {
    try { mergerNode.disconnect() } catch (e) {}
    mergerNode = null
  }
  const merger = audioCtx.createChannelMerger(2)
  mergerNode = merger
  const mode = store.vocalMode || 'stereo'
  if (mode === 'left') {
    splitterNode.connect(merger, 0, 0)
    splitterNode.connect(merger, 0, 1)
  } else if (mode === 'right') {
    splitterNode.connect(merger, 1, 0)
    splitterNode.connect(merger, 1, 1)
  } else {
    splitterNode.connect(merger, 0, 0)
    splitterNode.connect(merger, 1, 1)
  }
  merger.connect(audioCtx.destination)
}

// Socket Events
function setupSocket() {
  if (!store.socket) return
  
  store.socket.on('play', (data) => {
    isIdle.value = false
    isCountingDown.value = false
    clearInterval(countdownTimer)
    showPlayOverlay.value = false
    progressPct.value = 0
    sessionEnded.value = false  // lagu diputar lagi -> kembali normal
    // CATATAN: TIDAK me-reset banner peringatan di sini. Jika di-reset, banner
    // + beep akan muncul ulang setiap lagu berganti selama 5 menit terakhir.
    // Reset hanya saat: sesi berakhir, sesi baru (room_session active), atau sisa=0.
    
    store.currentSong = {
      song_id: data.song_id,
      queue_id: data.queue_id,
      song_title: '',
      song_artist: '',
      file_format: '',
      youtube_id: '',
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

  // Sesi room berakhir: tampilkan layar 'Sesi Berakhir' (bukan QR)
  store.socket.on('session_ended', () => {
    sessionEnded.value = true
    isIdle.value = true
    isCountingDown.value = false
    clearInterval(countdownTimer)
    store.currentSong = null
    store.isPlaying = false
    hideSessionWarning()
    // Notifikasi suara khas saat sesi berakhir
    playBeep('end')
  })

  // Sesi baru dimulai (admin) -> kembali ke mode normal (QR)
  store.socket.on('room_session', (data) => {
    if (data && data.status === 'active') {
      sessionEnded.value = false
      hideSessionWarning()
      if (userInteracted.value) generateQR()
    }
  })

  // Vocal channel (Kiri/Kanan/Stereo) dari operator
  store.socket.on('vocal', (data) => {
    store.vocalMode = data.channel || 'stereo'
    ensureAudioGraph()
  })

  // Volume dari operator (simpan ke store agar bertahan saat video reload)
  store.socket.on('vol', (data) => {
    store.currentVolume = Number(data.volume) || 80
    if (videoPlayer.value) {
      videoPlayer.value.volume = Math.max(0, Math.min(1, store.currentVolume / 100))
    }
    // OSD volume singkat di TV (feel karaoke komersial)
    volumeOsd.value = true
    clearTimeout(volumeOsdTimer)
    volumeOsdTimer = setTimeout(() => { volumeOsd.value = false }, 1500)
  })

  // Pitch/key shift: reload video dengan key baru, lalu kembali ke posisi semula
  store.socket.on('key_change', (data) => {
    const shift = Number(data.key_shift) || 0
    const wasPlaying = store.isPlaying
    const pos = videoPlayer.value?.currentTime || 0
    store.keyShift = shift
    if (wasPlaying && store.currentSong?.song_id) {
      pendingSeek = pos
      videoKey.value++
    }
  })
}

async function fetchSongDetail(songId) {
  try {
    const res = await fetch(`/api/songs/${songId}`)
    const song = await res.json()
    if (song && store.currentSong) {
      store.currentSong.song_title = song.title
      store.currentSong.song_artist = song.artist || ''
      store.currentSong.file_format = song.file_format || ''
      store.currentSong.youtube_id = (song.file_format === 'youtube' && String(song.file_path || '').startsWith('yt:'))
        ? String(song.file_path).slice(3) : ''
    }
  } catch(e) {}
}

// Reset progress bar saat berganti lagu (jalur mana pun: play event, fetchQueue)
watch(() => store.currentSong?.song_id, () => { progressPct.value = 0 })

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
  store.fetchRoomSession()
  setupSocket()
  
  if (store.socket) {
    store.socket.emit('register', { type: 'player-screen', room_id: store.roomId })
    store.socket.emit('join_room', { type: 'player', room_id: store.roomId })
  }
  
  updateClock()
  clockTimer = setInterval(updateClock, 10000)
  // Tick countdown sesi room tiap detik (hanya saat ada sesi aktif)
  sessionTimer = setInterval(() => { if (store.roomSession?.active) sessionNow.value = Date.now() }, 1000)
})

// Saat sesi habis (sisa 0) -> refetch agar server menutup sesi expired
watch(sessionRemaining, (val, old) => {
  // Peringatan sisa 5 menit: trigger sekali saat memasuki 300 detik
  if (val > 0 && val <= 300) showSessionWarning()
  if (val === 0 && old > 0) {
    hideSessionWarning()
    store.fetchRoomSession()
  }
})

onUnmounted(() => {
  clearTimeout(overlayTimer)
  clearInterval(countdownTimer)
  clearInterval(clockTimer)
  clearInterval(sessionTimer)
  clearTimeout(volumeOsdTimer)
  clearTimeout(sessionWarningTimer)
  stopProgressEmitter()
  destroyYtPlayer()
  try { if (mergerNode) mergerNode.disconnect() } catch (e) {}
  try { if (sourceNode) sourceNode.disconnect() } catch (e) {}
  try { if (audioCtx) audioCtx.close() } catch (e) {}
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

/* ROOM SESSION COUNTDOWN */
.session-timer {
  position: absolute;
  top: 1.2rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 6;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.45rem 1.1rem;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 2rem;
  color: white;
  pointer-events: none;
  transition: all 0.4s;
}

.st-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: rgba(255,255,255,0.6);
}

.st-value {
  font-size: 1.35rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
  color: #4ade80;
}

.st-end {
  font-size: 0.7rem;
  font-weight: 500;
  color: rgba(255,255,255,0.5);
}

/* Urgent: sisa <= 5 menit */
.session-timer.urgent {
  background: rgba(220, 38, 38, 0.85);
  border-color: rgba(255,255,255,0.25);
  animation: urgentPulse 1s ease-in-out infinite;
}
.session-timer.urgent .st-value { color: #fff; }
.session-timer.urgent .st-label { color: rgba(255,255,255,0.85); }
.session-timer.urgent .st-end { color: rgba(255,255,255,0.75); }

@keyframes urgentPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
  50% { box-shadow: 0 0 25px 4px rgba(239,68,68,0.6); }
}

/* PERINGATAN SISA 5 MENIT */
.session-warning {
  position: absolute;
  top: 5.2rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1rem 1.8rem;
  background: linear-gradient(135deg, rgba(220,38,38,0.95), rgba(153,27,27,0.95));
  border: 2px solid rgba(255,255,255,0.35);
  border-radius: 1.2rem;
  box-shadow: 0 0 40px rgba(239,68,68,0.7), 0 10px 30px rgba(0,0,0,0.4);
  color: white;
  pointer-events: none;
  animation: warnShake 0.5s ease-in-out;
}

.sw-icon {
  font-size: 2rem;
  animation: warnBounce 1s ease-in-out infinite;
}

.sw-text {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.sw-title {
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 2px;
  color: rgba(255,255,255,0.85);
}

.sw-sub {
  font-size: 1.5rem;
  font-weight: 900;
  letter-spacing: 0.5px;
  font-variant-numeric: tabular-nums;
}

.sw-sub strong {
  color: #fde047;
  font-size: 1.7rem;
}

@keyframes warnShake {
  0%, 100% { transform: translateX(-50%); }
  20% { transform: translateX(calc(-50% - 8px)); }
  40% { transform: translateX(calc(-50% + 8px)); }
  60% { transform: translateX(calc(-50% - 5px)); }
  80% { transform: translateX(calc(-50% + 5px)); }
}

@keyframes warnBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.warn-pop-enter-active, .warn-pop-leave-active { transition: opacity 0.35s; }
.warn-pop-enter-from, .warn-pop-leave-to { opacity: 0; }

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

/* YOUTUBE EMBED STAGE */
.yt-player-stage {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
}
.yt-player-el {
  width: 100%;
  height: 100%;
}
.yt-player-el iframe {
  width: 100%;
  height: 100%;
  border: none;
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

/* PROGRESS BAR (bawah, tipis) */
.player-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  z-index: 6;
  background: rgba(255,255,255,0.08);
}
.pp-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #f59e0b, #3b82f6);
  box-shadow: 0 0 12px rgba(239,68,68,0.6);
  transition: width 0.8s linear;
}

/* EQUALIZER (di badge NOW PLAYING) */
.eq-bars {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 12px;
  margin-left: 0.35rem;
}
.eq-bars i {
  width: 3px;
  height: 100%;
  background: linear-gradient(180deg, #f59e0b, #ef4444);
  border-radius: 1px;
  animation: eqBounce 0.9s ease-in-out infinite;
}
.eq-bars i:nth-child(2) { animation-delay: 0.15s; }
.eq-bars i:nth-child(3) { animation-delay: 0.3s; }
.eq-bars i:nth-child(4) { animation-delay: 0.45s; }
@keyframes eqBounce {
  0%, 100% { transform: scaleY(0.35); }
  50% { transform: scaleY(1); }
}

/* IDLE: chip jumlah antrian */
.idle-queue-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  padding: 0.45rem 1.1rem;
  background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.35);
  border-radius: 2rem;
  color: rgba(255,255,255,0.85);
  font-size: 0.85rem;
}
.idle-queue-chip strong {
  color: #f87171;
  font-size: 1rem;
}

/* IDLE: kartu lagu berikutnya */
.idle-next-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  margin-top: 0.9rem;
  padding: 0.7rem 1.4rem;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 1rem;
  animation: fadeIn 0.4s ease-out;
}
.in-label {
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #f59e0b;
}
.in-title {
  color: white;
  font-size: 1.05rem;
  font-weight: 700;
  max-width: 340px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.in-artist {
  color: rgba(255,255,255,0.5);
  font-size: 0.8rem;
}

/* IDLE: sesi berakhir */
.session-ended {
  text-align: center;
  animation: fadeIn 0.6s ease-out;
}
.se-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  animation: pulse 2s infinite;
}
.se-title {
  font-size: 2.5rem;
  font-weight: 900;
  color: white;
  letter-spacing: -0.5px;
  margin-bottom: 0.4rem;
}
.se-sub {
  color: rgba(255,255,255,0.5);
  font-size: 1rem;
}

/* VOLUME OSD */
.volume-osd {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 25;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.8rem 1.4rem;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 1rem;
  color: white;
  pointer-events: none;
}
.osd-icon { font-size: 1.5rem; }
.osd-track {
  width: 160px;
  height: 6px;
  background: rgba(255,255,255,0.15);
  border-radius: 3px;
  overflow: hidden;
}
.osd-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #ef4444);
  border-radius: 3px;
  transition: width 0.15s;
}
.osd-val {
  font-size: 0.95rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  min-width: 3ch;
}
.osd-fade-enter-active, .osd-fade-leave-active { transition: opacity 0.25s, transform 0.25s; }
.osd-fade-enter-from, .osd-fade-leave-to { opacity: 0; transform: translate(-50%, -50%) scale(0.92); }

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
