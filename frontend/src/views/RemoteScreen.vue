<template>
  <div class="remote-app">
    <!-- HEADER COMPACT -->
    <header class="remote-header">
      <div class="header-left">
        <div class="room-pill" @click="showRoomQR = true">
          <span class="room-dot"></span>
          <span>{{ store.roomId }}</span>
        </div>
      </div>
      <div class="header-center">
        <span class="header-logo">🎤</span>
        <span class="header-brand">BPF Karaoke</span>
      </div>
      <div class="header-right">
        <button class="btn-icon" @click="refreshData" title="Refresh">🔄</button>
      </div>
    </header>

    <!-- QR CODE MODAL -->
    <div class="qr-modal" v-if="showRoomQR" @click.self="showRoomQR = false">
      <div class="qr-card">
        <div class="qr-card-header">
          <h3>📱 Scan QR Code</h3>
          <button @click="showRoomQR = false" class="qr-close">✕</button>
        </div>
        <div class="qr-card-body">
          <canvas ref="qrCanvas" class="qr-canvas"></canvas>
        </div>
        <p class="qr-card-text">Bagikan ke teman untuk request bareng!</p>
        <p class="qr-card-url">{{ remoteUrl }}</p>
        <button class="qr-card-btn" @click="copyUrl">📋 Salin URL</button>
      </div>
    </div>

    <!-- NOW PLAYING STRIP -->
    <div class="now-playing-strip" v-if="store.currentSong && store.isPlaying">
      <div class="strip-wave">
        <span class="wbar"></span><span class="wbar"></span><span class="wbar"></span>
      </div>
      <div class="strip-info">
        <div class="strip-title">{{ store.currentSong.song_title || '♪' }}</div>
        <div class="strip-artist">{{ store.currentSong.song_artist || '' }}</div>
      </div>
      <span class="strip-badge">LIVE</span>
    </div>

    <!-- SEARCH BAR -->
    <div class="search-section">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input v-model="searchQuery" type="search" placeholder="Cari lagu favoritmu..." class="search-input" @input="onSearch" />
        <button v-if="searchQuery" class="search-clear" @click="clearSearch">✕</button>
      </div>
    </div>

    <!-- QUICK CHIPS -->
    <div class="chips-scroll">
      <button @click="setMood('party')" class="mood-chip party">🎉 Party</button>
      <button @click="setMood('romantic')" class="mood-chip romantic">💕 Romantic</button>
      <button @click="setMood('nostalgia')" class="mood-chip nostalgia">📻 90an</button>
      <button @click="setMood('chill')" class="mood-chip chill">😌 Chill</button>
      <button @click="setFilter('Pop Indonesia')" class="mood-chip pop">🇮🇩 Pop</button>
      <button @click="setFilter('Dangdut')" class="mood-chip dangdut">🎶 Dangdut</button>
      <button @click="setFilter('K-Pop')" class="mood-chip kpop">🇰🇷 K-Pop</button>
      <button @click="clearAll" class="mood-chip all">🔥 Semua</button>
    </div>

    <!-- SONG LIST -->
    <div class="song-list">
      <div v-if="isLoading" class="skeleton-list">
        <div v-for="i in 5" :key="i" class="skeleton-item">
          <div class="skeleton-thumb"></div>
          <div class="skeleton-lines"><div class="skeleton-line w-75"></div><div class="skeleton-line w-50"></div></div>
        </div>
      </div>

      <div v-for="song in filteredSongs" :key="song.id" class="song-item" :class="{ 'is-added': addedSongs.has(song.id) }" @click="addSong(song)">
        <div class="song-thumb" :style="{ background: thumbColor(song.genre) }">
          <span class="thumb-emoji">🎵</span>
          <span v-if="addedSongs.has(song.id)" class="thumb-check">✓</span>
        </div>
        <div class="song-detail">
          <div class="song-title">{{ song.title }}</div>
          <div class="song-artist">{{ song.artist || 'Unknown' }}</div>
          <div class="song-meta">
            <span v-if="song.genre" class="meta-genre">{{ song.genre }}</span>
            <span class="meta-plays">▶ {{ song.play_count }}x</span>
          </div>
        </div>
        <button class="btn-add-song" :class="{ added: addedSongs.has(song.id) }" @click.stop="addSong(song)">
          {{ addedSongs.has(song.id) ? '✓' : '+' }}
        </button>
      </div>

      <div v-if="!isLoading && filteredSongs.length === 0" class="empty-state">
        <span class="empty-emoji">🔍</span><h3>Lagu tidak ditemukan</h3><p>Coba kata kunci lain</p>
      </div>
    </div>

    <!-- MY QUEUE FAB -->
    <button class="fab-queue" @click="showMyQueue = true" v-if="myQueueCount > 0">
      <span class="fab-count">{{ myQueueCount }}</span>
      <span class="fab-label">Antrian Saya</span>
    </button>

    <!-- MY QUEUE MODAL -->
    <div class="queue-modal" v-if="showMyQueue" @click.self="showMyQueue = false">
      <div class="queue-card">
        <div class="queue-header"><h3>📋 Antrian Saya</h3><span class="queue-total">{{ myQueueCount }} lagu</span></div>
        <div class="queue-list">
          <div v-for="(item, idx) in myQueue" :key="item.id" class="queue-row">
            <span class="queue-num">{{ idx + 1 }}</span>
            <div class="queue-info"><div class="queue-title">{{ item.song?.title || '...' }}</div><div class="queue-artist">{{ item.song?.artist || '' }}</div></div>
            <button @click="removeSong(item.id)" class="btn-remove-queue">✕</button>
          </div>
          <div v-if="myQueue.length === 0" class="queue-empty"><p>Belum ada antrian</p></div>
        </div>
        <button class="btn-close-queue" @click="showMyQueue = false">Tutup</button>
      </div>
    </div>

    <!-- TOAST -->
    <div class="remote-toast" :class="{ show: toastVisible }"><span>{{ toastMessage }}</span></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import axios from 'axios'
import QRCode from 'qrcode'

const store = useKaraokeStore()

const searchQuery = ref('')
const isLoading = ref(false)
const songs = ref([])
const addedSongs = ref(new Set())
const showMyQueue = ref(false)
const showRoomQR = ref(false)
const toastVisible = ref(false)
const toastMessage = ref('')
const qrCanvas = ref(null)

const remoteUrl = computed(() => `${window.location.origin}/remote?room=${store.roomId}`)
const myQueue = computed(() => store.queue.filter(q => q.status === 'waiting'))
const myQueueCount = computed(() => myQueue.value.length)
const filteredSongs = computed(() => songs.value)

function showToast(msg) { toastMessage.value = msg; toastVisible.value = true; setTimeout(() => toastVisible.value = false, 2500) }

// QR Code generation
watch(showRoomQR, async (val) => {
  if (val) {
    await nextTick()
    await generateQR()
  }
})

async function generateQR() {
  await nextTick()
  if (qrCanvas.value) {
    try {
      await QRCode.toCanvas(qrCanvas.value, remoteUrl.value, {
        width: 220, margin: 1,
        color: { dark: '#1e293b', light: '#ffffff' }
      })
      console.log('✅ QR generated')
    } catch(err) { console.error('QR error:', err) }
  }
}

function copyUrl() {
  navigator.clipboard?.writeText(remoteUrl.value).then(() => showToast('📋 URL disalin!')).catch(() => showToast('Gagal menyalin'))
}

// Fetch songs
async function fetchSongs() {
  isLoading.value = true
  try {
    const params = { limit: 50 }
    if (searchQuery.value) params.search = searchQuery.value
    if (store.selectedGenre) params.genre = store.selectedGenre
    const res = await axios.get('/api/songs', { params })
    songs.value = res.data
  } catch(e) { console.error('Fetch songs:', e) }
  isLoading.value = false
}

let searchTimer
function onSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(() => fetchSongs(), 400) }
function clearSearch() { searchQuery.value = ''; fetchSongs() }
function setFilter(genre) { store.selectedGenre = store.selectedGenre === genre ? null : genre; fetchSongs() }
function setMood(mood) { store.selectedGenre = null; searchQuery.value = ''; fetchSongs(); showToast(`🎵 Menampilkan lagu ${mood}!`) }
function clearAll() { store.selectedGenre = null; searchQuery.value = ''; fetchSongs() }

async function addSong(song) {
  if (addedSongs.value.has(song.id)) return
  const ok = await store.addToQueue(song.id)
  if (ok) { addedSongs.value.add(song.id); showToast(`✅ "${song.title}" ditambahkan!`); setTimeout(() => addedSongs.value.delete(song.id), 3000); if (navigator.vibrate) navigator.vibrate(50) }
}

async function removeSong(queueId) { await store.removeFromQueue(queueId); showToast('🗑️ Dihapus') }

function refreshData() { fetchSongs(); store.fetchQueue(); showToast('🔄 Data diperbarui') }

function thumbColor(genre) {
  const map = { 'Pop Indonesia': 'linear-gradient(135deg, #ef4444, #f87171)', 'Dangdut': 'linear-gradient(135deg, #f59e0b, #fbbf24)', 'K-Pop': 'linear-gradient(135deg, #ec4899, #f472b6)', 'Barat': 'linear-gradient(135deg, #3b82f6, #60a5fa)' }
  return map[genre] || 'linear-gradient(135deg, #ef4444, #3b82f6)'
}

onMounted(async () => { store.setScreenType('remote'); store.fetchQueue(); await fetchSongs() })
</script>

<style scoped>
.remote-app { min-height: 100vh; background: linear-gradient(180deg, #fef2f2 0%, #ffffff 20%, #eff6ff 100%); font-family: 'Inter', sans-serif; color: #1e293b; padding-bottom: 80px; max-width: 500px; margin: 0 auto; position: relative; overflow-x: hidden; }

.remote-header { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; background: rgba(255,255,255,0.9); backdrop-filter: blur(20px); position: sticky; top: 0; z-index: 50; border-bottom: 1px solid rgba(0,0,0,0.05); }
.room-pill { display: flex; align-items: center; gap: 0.4rem; background: #f1f5f9; padding: 0.35rem 0.75rem; border-radius: 2rem; font-size: 0.75rem; font-weight: 600; cursor: pointer; }
.room-dot { width: 6px; height: 6px; background: #10b981; border-radius: 50%; }
.header-center { display: flex; align-items: center; gap: 0.35rem; font-weight: 700; font-size: 0.9rem; }
.header-logo { font-size: 1.2rem; }
.btn-icon { background: none; border: none; font-size: 1.1rem; cursor: pointer; padding: 0.25rem; }

/* QR MODAL */
.qr-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200; display: flex; align-items: center; justify-content: center; padding: 1rem; animation: fadeIn 0.2s ease; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
.qr-card { background: white; border-radius: 20px; padding: 1.5rem; max-width: 320px; width: 100%; text-align: center; }
.qr-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.qr-card-header h3 { font-size: 1rem; font-weight: 700; }
.qr-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #94a3b8; }
.qr-card-body { background: #f8fafc; padding: 1rem; border-radius: 12px; display: inline-block; margin-bottom: 0.75rem; }
.qr-canvas { display: block; width: 200px; height: 200px; }
.qr-card-text { font-size: 0.8rem; color: #64748b; margin-bottom: 0.25rem; }
.qr-card-url { font-size: 0.65rem; color: #94a3b8; word-break: break-all; margin-bottom: 0.75rem; }
.qr-card-btn { padding: 0.5rem 1.5rem; background: #f1f5f9; border: none; border-radius: 2rem; cursor: pointer; font-weight: 500; font-size: 0.8rem; }

/* NOW PLAYING */
.now-playing-strip { display: flex; align-items: center; gap: 0.65rem; margin: 0.5rem 1rem; padding: 0.6rem 0.85rem; background: linear-gradient(135deg, #fef2f2, #eff6ff); border-radius: 12px; border: 1px solid #fecaca; }
.strip-wave { display: flex; align-items: flex-end; gap: 1.5px; height: 16px; }
.wbar { width: 2px; background: #ef4444; border-radius: 1px; animation: wave 1s ease-in-out infinite; }
.wbar:nth-child(1) { height: 6px; animation-delay: 0s; } .wbar:nth-child(2) { height: 12px; animation-delay: 0.2s; } .wbar:nth-child(3) { height: 8px; animation-delay: 0.4s; }
@keyframes wave { 0%,100%{transform:scaleY(.5)} 50%{transform:scaleY(1)} }
.strip-info { flex: 1; min-width: 0; }
.strip-title { font-weight: 600; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.strip-artist { font-size: 0.7rem; color: #94a3b8; }
.strip-badge { font-size: 0.55rem; background: #ef4444; color: white; padding: 0.15rem 0.5rem; border-radius: 1rem; font-weight: 700; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }

/* SEARCH */
.search-section { padding: 0.5rem 1rem; position: sticky; top: 48px; z-index: 40; background: rgba(255,255,255,0.9); backdrop-filter: blur(20px); }
.search-box { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 0.75rem; font-size: 0.9rem; z-index: 1; }
.search-input { width: 100%; padding: 0.7rem 1rem 0.7rem 2.5rem; border: 2px solid #e2e8f0; border-radius: 14px; font-size: 0.9rem; background: #f8fafc; transition: all 0.3s; }
.search-input:focus { outline: none; border-color: #ef4444; background: white; box-shadow: 0 0 0 3px rgba(239,68,68,0.08); }
.search-clear { position: absolute; right: 0.6rem; background: #e2e8f0; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 0.7rem; }

/* CHIPS */
.chips-scroll { display: flex; gap: 0.4rem; padding: 0.6rem 1rem; overflow-x: auto; scrollbar-width: none; }
.chips-scroll::-webkit-scrollbar { display: none; }
.mood-chip { padding: 0.45rem 0.85rem; border: none; border-radius: 2rem; font-size: 0.78rem; font-weight: 600; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
.mood-chip:active { transform: scale(0.95); }
.mood-chip.party { background: #fef3c7; color: #92400e; } .mood-chip.romantic { background: #fce7f3; color: #9d174d; } .mood-chip.nostalgia { background: #f3e8ff; color: #6b21a8; } .mood-chip.chill { background: #e0f2fe; color: #075985; }
.mood-chip.pop { background: #fef2f2; color: #dc2626; } .mood-chip.dangdut { background: #fffbeb; color: #d97706; } .mood-chip.kpop { background: #fdf2f8; color: #db2777; } .mood-chip.all { background: #f1f5f9; color: #475569; }

/* SONG LIST */
.song-list { padding: 0 1rem; }
.song-item { display: flex; align-items: center; gap: 0.65rem; padding: 0.65rem; background: white; border-radius: 12px; margin-bottom: 0.4rem; cursor: pointer; transition: all 0.2s; border: 1px solid #f1f5f9; animation: slideUp 0.4s ease-out backwards; }
@keyframes slideUp { from{opacity:0;transform:translateY(15px)} to{opacity:1;transform:translateY(0)} }
.song-item:active { transform: scale(0.98); background: #fafafa; }
.song-item.is-added { border-color: #bbf7d0; background: #f0fdf4; }
.song-thumb { width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; position: relative; }
.thumb-emoji { font-size: 1rem; }
.thumb-check { position: absolute; bottom: -2px; right: -2px; width: 16px; height: 16px; background: #10b981; color: white; border-radius: 50%; font-size: 0.6rem; display: flex; align-items: center; justify-content: center; }
.song-detail { flex: 1; min-width: 0; }
.song-title { font-weight: 600; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.song-artist { font-size: 0.75rem; color: #94a3b8; }
.song-meta { display: flex; gap: 0.35rem; margin-top: 0.1rem; }
.meta-genre { font-size: 0.6rem; padding: 0.08rem 0.35rem; background: #eff6ff; color: #3b82f6; border-radius: 4px; } .meta-plays { font-size: 0.6rem; color: #cbd5e1; }
.btn-add-song { width: 34px; height: 34px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1.1rem; font-weight: 700; cursor: pointer; transition: all 0.2s; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.btn-add-song.added { background: #10b981; border-color: #10b981; color: white; }

/* SKELETON */
.skeleton-item { display: flex; align-items: center; gap: 0.65rem; padding: 0.65rem; margin-bottom: 0.4rem; }
.skeleton-thumb { width: 42px; height: 42px; border-radius: 10px; background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.skeleton-lines { flex: 1; }
.skeleton-line { height: 10px; background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px; margin-bottom: 5px; }
.w-75 { width: 75%; } .w-50 { width: 50%; }
@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

/* EMPTY */
.empty-state { text-align: center; padding: 3rem 1rem; color: #94a3b8; }
.empty-emoji { font-size: 3rem; display: block; margin-bottom: 0.5rem; }

/* FAB */
.fab-queue { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%); background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 0.7rem 1.5rem; border-radius: 3rem; font-weight: 700; font-size: 0.85rem; cursor: pointer; box-shadow: 0 10px 25px rgba(239,68,68,0.4); display: flex; align-items: center; gap: 0.5rem; z-index: 50; animation: bounceIn 0.5s ease-out; }
@keyframes bounceIn { 0%{transform:translateX(-50%) scale(0)} 50%{transform:translateX(-50%) scale(1.1)} 100%{transform:translateX(-50%) scale(1)} }
.fab-count { background: white; color: #ef4444; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 800; }

/* QUEUE MODAL */
.queue-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 150; display: flex; align-items: flex-end; justify-content: center; }
.queue-card { background: white; border-radius: 20px 20px 0 0; width: 100%; max-width: 500px; max-height: 70vh; display: flex; flex-direction: column; animation: slideUp 0.3s ease-out; }
.queue-header { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem; border-bottom: 1px solid #f1f5f9; }
.queue-header h3 { font-size: 1rem; font-weight: 700; } .queue-total { font-size: 0.75rem; color: #94a3b8; }
.queue-list { flex: 1; overflow-y: auto; padding: 0.5rem 1rem; }
.queue-row { display: flex; align-items: center; gap: 0.65rem; padding: 0.6rem 0; border-bottom: 1px solid #f8fafc; }
.queue-num { width: 24px; height: 24px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 700; color: #64748b; flex-shrink: 0; }
.queue-info { flex: 1; min-width: 0; } .queue-title { font-weight: 600; font-size: 0.8rem; } .queue-artist { font-size: 0.7rem; color: #94a3b8; }
.btn-remove-queue { background: none; border: none; color: #ef4444; font-size: 1rem; cursor: pointer; padding: 0.25rem; }
.btn-close-queue { margin: 0.75rem; padding: 0.7rem; background: #f1f5f9; border: none; border-radius: 12px; cursor: pointer; font-weight: 600; font-size: 0.9rem; }
.queue-empty { text-align: center; padding: 2rem; color: #94a3b8; }

/* TOAST */
.remote-toast { position: fixed; bottom: 6rem; left: 50%; transform: translateX(-50%) translateY(20px); background: #1e293b; color: white; padding: 0.55rem 1.25rem; border-radius: 2rem; font-size: 0.8rem; font-weight: 500; z-index: 200; opacity: 0; transition: all 0.3s ease; pointer-events: none; white-space: nowrap; }
.remote-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
