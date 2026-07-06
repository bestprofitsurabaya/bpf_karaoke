<template>
  <div class="player-screen" @click="handleFirstInteraction">
    <div class="bg-animation">
      <div class="bg-circle c1"></div>
      <div class="bg-circle c2"></div>
    </div>

    <div class="video-container" v-if="store.currentSong">
      <div class="now-playing-hero">
        <div class="np-artwork">
          <div class="artwork-circle">
            <video 
              ref="videoPlayer"
              :src="videoUrl"
              autoplay
              playsinline
              controls
              style="width: 70vw; height: 60vh; border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,0.5);"
              @ended="songEnded"
              @loadedmetadata="handleMetadataLoaded"
            ></video>
          </div>
        </div>
        <div class="np-details" style="margin-top: 1rem; text-align: center;">
          <h1 class="np-song-title">{{ store.currentSong.song_title }}</h1>
          <p class="np-song-artist">{{ store.currentSong.song_artist || 'Unknown Artist' }}</p>
        </div>
      </div>
    </div>

    <div class="idle-screen" v-else>
      <div class="idle-content">
        <div class="idle-circle"><span>🎤</span></div>
        <h1 class="idle-title"><span class="text-red">BPF</span><span class="text-blue"> Karaoke</span></h1>
        <p class="idle-subtitle">Scan QR Code ini untuk request lagu langsung dari HP Anda</p>
        
        <div class="qr-container">
          <div class="qr-box">
            <img :src="qrCodeUrl" alt="Scan Remote QR Code" style="width: 200px; height: 200px; display: block;" />
          </div>
        </div>
        
        <div class="room-badge">
          <span class="room-dot"></span>
          Lokasi Ruangan: {{ store.roomId }}
        </div>
      </div>
    </div>

    <div v-if="needInteraction" class="interaction-overlay">
      <div class="interaction-card">
        <h2>🎤 Siap Memulai Karaoke?</h2>
        <p>Klik di mana saja pada layar ini untuk mengaktifkan pemutaran audio otomatis.</p>
      </div>
    </div>

    <footer class="player-footer">
      <p>© {{ currentYear }} IT BPF Surabaya - PT BESTPROFIT FUTURES SURABAYA. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'

const store = useKaraokeStore()
const videoPlayer = ref(null)
const currentYear = new Date().getFullYear()
const needInteraction = ref(true)

const videoUrl = computed(() => {
  if (!store.currentSong) return ''
  const path = store.currentSong.file_path.split('/media/lagu/')[1] || store.currentSong.file_path
  return `/media/${path}`
})

const qrCodeUrl = computed(() => {
  const baseRemoteUrl = `https://nasbpfsby.duckdns.org:8443/remote?room=${encodeURIComponent(store.roomId)}`
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(baseRemoteUrl)}`
})

// Mengatasi kebijakan autoplay browser via user click token
const handleFirstInteraction = () => {
  needInteraction.value = false
  if (videoPlayer.value) {
    videoPlayer.value.play().catch(() => {})
  }
}

const handleMetadataLoaded = () => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = store.currentVolume / 100
    videoPlayer.value.play().catch(() => {
      console.log("Autoplay blocked by browser. Interaction required.")
      needInteraction.value = true
    })
  }
}

// Watcher untuk mendeteksi perubahan state lagu (Play/Pause/Next)
watch(() => store.currentSong, (newSong) => {
  if (newSong) {
    needInteraction.value = false
    setTimeout(() => {
      if (videoPlayer.value) {
        videoPlayer.value.load()
        videoPlayer.value.play().catch(() => {
          needInteraction.value = true
        })
      }
    }, 300)
  }
}, { deep: true })

watch(() => store.isPlaying, (newVal) => {
  if (!videoPlayer.value) return
  if (newVal) {
    videoPlayer.value.play().catch(() => { needInteraction.value = true })
  } else {
    videoPlayer.value.pause()
  }
})

watch(() => store.currentVolume, (newVal) => {
  if (videoPlayer.value) {
    videoPlayer.value.volume = newVal / 100
  }
})

// Fungsi otomatis eksekusi antrian berikutnya jika lagu selesai
const songEnded = async () => {
  const currentQueueId = store.currentSong?.queue_id
  store.currentSong = null
  store.isPlaying = false
  
  // Kirim perintah skip ke backend via socket agar antrian di-clear
  await store.skipSong(currentQueueId)
  
  // Berikan jeda 1 detik, lalu ambil antrian berikutnya secara otomatis jika tersedia
  setTimeout(async () => {
    await store.fetchQueue()
    if (store.waitingQueue.length > 0) {
      const nextItem = store.waitingQueue[0]
      store.playSong(nextItem.song_id, nextItem.id)
    }
  }, 1000)
}

onMounted(() => {
  store.setScreenType('player')
  store.fetchQueue()
  store.connectSocket()
})
</script>

<style scoped>
.player-screen { width: 100vw; height: 100vh; background: #0a0a0a; position: relative; overflow: hidden; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; }
.bg-animation { position: absolute; inset: 0; overflow: hidden; z-index: 0; }
.bg-circle { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.15; }
.c1 { width: 500px; height: 500px; background: #ef4444; top: -100px; right: -100px; }
.c2 { width: 400px; height: 400px; background: #3b82f6; bottom: -100px; left: -100px; }
.video-container, .idle-screen { position: relative; z-index: 1; text-align: center; }
.idle-circle { width: 100px; height: 100px; background: linear-gradient(135deg, #ef4444, #3b82f6); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 2.5rem; }
.idle-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem; }
.text-red { color: #ef4444; }
.text-blue { color: #3b82f6; }
.idle-subtitle { color: #a1a1aa; margin-bottom: 1.5rem; }
.qr-box { background: white; padding: 0.75rem; border-radius: 12px; display: inline-block; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
.room-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1.5rem; background: rgba(255,255,255,0.05); border-radius: 30px; margin-top: 1.5rem; color: #d4d4d8; }
.room-dot { width: 8px; height: 8px; background: #10b981; border-radius: 50%; }
.np-song-title { font-size: 2rem; margin-bottom: 0.25rem; font-weight: 700; }
.np-song-artist { font-size: 1.2rem; color: #a1a1aa; }
.interaction-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; z-index: 999; }
.interaction-card { background: #1f2937; padding: 2rem; border-radius: 16px; text-align: center; border: 1px solid #374151; max-width: 400px; }
.interaction-card h2 { margin-bottom: 0.5rem; color: #ef4444; }
.player-footer { position: absolute; bottom: 1rem; color: #52525b; font-size: 0.8rem; text-align: center; width: 100%; }
</style>
