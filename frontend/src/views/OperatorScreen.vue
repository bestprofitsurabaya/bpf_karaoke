<template>
  <div class="operator-app" @click.self="showRoomList = false">
    <!-- TOP BAR -->
    <header class="top-bar">
      <div class="bar-left">
        <img src="/icons/icon-512x512.png" alt="BPF" class="bar-logo" />
        <div class="bar-info">
          <span class="bar-title">BPF Karaoke</span>
          <div class="room-select-wrap" @click.stop="showRoomList = !showRoomList">
            <span class="bar-room">{{ store.roomId }}</span>
            <span class="room-arrow">▾</span>
            <div class="room-dropdown" v-if="showRoomList" @click.stop>
              <div v-for="room in rooms" :key="room.id" class="room-option" :class="{ active: room.name === store.roomId }" @click="selectRoom(room)">
                <span>🚪 {{ room.name }}</span>
                <span class="room-cap">👥 {{ room.capacity }}</span>
              </div>
              <div v-if="rooms.length === 0" class="room-empty" @click.stop>Loading rooms...</div>
            </div>
          </div>
        </div>
      </div>
      <div class="bar-center">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input v-model="store.searchQuery" type="text" placeholder="Cari judul lagu atau penyanyi..." class="search-input" @input="debouncedSearch" />
          <button v-if="store.searchQuery" class="search-clear" @click="clearSearch">✕</button>
        </div>
      </div>
      <div class="bar-right">
        <button class="btn-launch" @click="launchPlayer" title="Buka Player di Tab Baru">
          📺 Launch Player
        </button>
        <div class="status-dot" :class="{ online: store.isConnected }"></div>
        <span class="status-text">{{ store.isConnected ? 'Online' : 'Offline' }}</span>
        <button class="btn-icon" @click="refreshAll" title="Refresh">🔄</button>
        <router-link to="/" class="btn-icon" title="Home">🏠</router-link>
      </div>
    </header>

    <!-- MAIN LAYOUT -->
    <div class="main-layout">
      <!-- LEFT: QUEUE PANEL -->
      <aside class="queue-panel">
        <div class="panel-header">
          <h3>📋 Antrian</h3>
          <span class="queue-badge">{{ store.waitingQueue.length }}</span>
        </div>
        <div class="now-playing-card" v-if="store.currentSong && store.isPlaying">
          <div class="np-visual">
            <div class="np-equalizer"><span class="eq-bar"></span><span class="eq-bar"></span><span class="eq-bar"></span><span class="eq-bar"></span><span class="eq-bar"></span></div>
          </div>
          <div class="np-detail">
            <span class="np-label">🎤 SEDANG DIPUTAR</span>
            <div class="np-title">{{ store.currentSong.song_title || '♪' }}</div>
            <div class="np-artist">{{ store.currentSong.song_artist || '' }}</div>
          </div>
        </div>
        <div class="queue-list">
          <div v-for="(item, index) in store.waitingQueue" :key="item.id" class="queue-item" :class="{ 'is-next': index === 0 }">
            <div class="queue-rank" :class="{ 'rank-next': index === 0 }">{{ index + 1 }}</div>
            <div class="queue-detail">
              <div class="queue-song">{{ item.song?.title || 'Unknown' }}</div>
              <div class="queue-artist">{{ item.song?.artist || '-' }}</div>
            </div>
            <div class="queue-actions">
              <button v-if="index === 0" class="btn-play-now" @click="playNow(item)">▶</button>
              <button class="btn-remove" @click="confirmRemove(item)">✕</button>
            </div>
          </div>
          <div v-if="store.waitingQueue.length === 0" class="queue-empty">
            <div class="empty-art">🎶</div><p>Antrian kosong</p><p class="empty-hint">Cari lagu & klik <strong>+</strong></p>
          </div>
        </div>
        <div class="queue-footer">
          <div class="stat-pill"><span>🎵</span><strong>{{ store.stats.total_songs || 0 }}</strong></div>
          <div class="stat-pill"><span>▶️</span><strong>{{ store.stats.total_plays || 0 }}</strong></div>
          <div class="stat-pill"><span>📋</span><strong>{{ store.stats.queue_today || 0 }}</strong></div>
        </div>
      </aside>

      <!-- CENTER: SONG BROWSER -->
      <main class="browser-panel">
        <div class="filter-strip">
          <button v-for="f in quickFilters" :key="f.label" @click="setFilter(f.genre)" class="filter-chip" :class="{ active: store.selectedGenre === f.genre }">
            <span class="chip-emoji">{{ f.emoji }}</span><span class="chip-label">{{ f.label }}</span>
          </button>
        </div>
        <div class="song-grid">
          <div v-for="song in store.filteredSongs" :key="song.id" class="song-card" :class="{ 'is-in-queue': isInQueue(song.id) }" @click="addToQueue(song)">
            <div class="card-thumb" :style="{ background: thumbGradient(song.genre) }"><span class="thumb-icon">🎵</span><span v-if="isInQueue(song.id)" class="thumb-badge">✓</span></div>
            <div class="card-info">
              <div class="card-title">{{ song.title }}</div>
              <div class="card-artist">{{ song.artist || 'Unknown' }}</div>
              <div class="card-meta"><span v-if="song.genre" class="meta-tag">{{ song.genre }}</span><span class="meta-plays">▶ {{ song.play_count }}x</span></div>
            </div>
            <button class="card-add" @click.stop="addToQueue(song)">{{ isInQueue(song.id) ? '✓' : '+' }}</button>
          </div>
          <div v-if="store.filteredSongs.length === 0" class="browser-empty"><span>🔍</span><h3>Tidak ditemukan</h3></div>
        </div>
      </main>

      <!-- RIGHT: CONTROL PANEL -->
      <aside class="control-panel">
        <div class="ctrl-section"><h4 class="ctrl-title">▶️ Playback</h4>
          <div class="playback-btns">
            <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()" class="pb-btn primary" :disabled="!store.currentSong">{{ store.isPlaying ? '⏸ Pause' : '▶ Play' }}</button>
            <button @click="skipCurrent" class="pb-btn" :disabled="!store.currentSong">⏭ Skip</button>
          </div>
          <div class="now-brief" v-if="store.currentSong"><span class="brief-label">Now:</span> <span class="brief-title">{{ store.currentSong.song_title || '-' }}</span></div>
        </div>
        <div class="ctrl-section"><h4 class="ctrl-title">🎹 Pitch / Key</h4>
          <div class="key-display">
            <button @click="changeKey(-1)" class="key-btn" :disabled="store.keyShift <= -12">−</button>
            <div class="key-value" @click="store.changeKey(0)"><span class="key-num">{{ store.keyShift > 0 ? '+' : '' }}{{ store.keyShift }}</span><span class="key-label">{{ store.keyShift === 0 ? 'Original' : 'Semitone' }}</span></div>
            <button @click="changeKey(1)" class="key-btn" :disabled="store.keyShift >= 12">+</button>
          </div>
          <div class="key-presets"><button v-for="k in [-4, -2, 0, 2, 4]" :key="k" @click="store.changeKey(k)" class="preset-btn" :class="{ active: store.keyShift === k }">{{ k === 0 ? '0' : k > 0 ? '+' + k : k }}</button></div>
        </div>
        <div class="ctrl-section"><h4 class="ctrl-title">🎤 Vocal</h4>
          <div class="vocal-btns">
            <button @click="store.toggleVocal('stereo')" class="vocal-btn" :class="{ active: store.vocalMode === 'stereo' }">🎤 Stereo</button>
            <button @click="store.toggleVocal('left')" class="vocal-btn" :class="{ active: store.vocalMode === 'left' }">🔊 Kiri</button>
            <button @click="store.toggleVocal('right')" class="vocal-btn" :class="{ active: store.vocalMode === 'right' }">🔊 Kanan</button>
          </div>
          <button @click="store.vocalAI = !store.vocalAI" class="ai-toggle" :class="{ active: store.vocalAI }">🤖 {{ store.vocalAI ? 'AI Vocal ON' : 'AI Vocal OFF' }}</button>
        </div>
        <div class="ctrl-section"><h4 class="ctrl-title">🔊 Volume</h4>
          <div class="volume-row"><span>🔈</span><input type="range" min="0" max="100" :value="store.currentVolume" @input="store.setVolume(Number($event.target.value))" class="vol-slider" /><span>🔊</span></div>
          <div class="vol-value">{{ store.currentVolume }}%</div>
        </div>
        <div class="ctrl-section ai-section"><h4 class="ctrl-title">🤖 AI Cepat</h4>
          <button @click="store.generatePlaylist('party')" class="ai-btn party">🎉 Party Mix</button>
          <button @click="store.generatePlaylist('romantic')" class="ai-btn romantic">💕 Romantic</button>
          <button @click="store.generatePlaylist('nostalgia')" class="ai-btn nostalgia">📻 90an Hits</button>
          <div class="mood-indicator" v-if="store.roomMood"><span class="mood-emoji">{{ store.roomMood.mood_emoji || '🎵' }}</span><span class="mood-text">Mood: <strong>{{ store.roomMood.current_mood || 'unknown' }}</strong></span></div>
        </div>
      </aside>
    </div>

    <!-- TOAST -->
    <div class="operator-toast" :class="{ show: toast.show }"><span>{{ toast.message }}</span></div>

    <!-- CONFIRM -->
    <div class="confirm-overlay" v-if="confirm.show" @click.self="confirm.show = false">
      <div class="confirm-card"><span class="confirm-icon">⚠️</span><p>{{ confirm.message }}</p>
        <div class="confirm-actions"><button @click="confirm.show = false" class="btn-cancel">Batal</button><button @click="confirm.onConfirm" class="btn-danger">Hapus</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import axios from 'axios'

const store = useKaraokeStore()
const toast = ref({ show: false, message: '' })
const confirm = ref({ show: false, message: '', onConfirm: () => {} })
const showRoomList = ref(false)
const rooms = ref([])

let searchTimer

const quickFilters = [
  { emoji: '🔥', label: 'Semua', genre: null },
  { emoji: '🇮🇩', label: 'Pop Indo', genre: 'Pop Indonesia' },
  { emoji: '🎶', label: 'Dangdut', genre: 'Dangdut' },
  { emoji: '🌍', label: 'Barat', genre: 'Barat' },
  { emoji: '🇰🇷', label: 'K-Pop', genre: 'K-Pop' },
  { emoji: '🇨🇳', label: 'Mandarin', genre: 'Mandarin' },
]

function debouncedSearch() { clearTimeout(searchTimer); searchTimer = setTimeout(() => store.fetchSongs(), 350) }
function clearSearch() { store.searchQuery = ''; store.fetchSongs() }
function setFilter(genre) { store.selectedGenre = store.selectedGenre === genre ? null : genre; store.fetchSongs() }
function isInQueue(songId) { return store.waitingQueue.some(q => q.song_id === songId) }

async function addToQueue(song) {
  if (isInQueue(song.id)) { showToast('Sudah di antrian'); return }
  const ok = await store.addToQueue(song.id)
  if (ok) showToast('✅ Ditambahkan!')
}

function playNow(item) { store.playSong(item.song_id, item.id); showToast('▶️ Diputar') }
function skipCurrent() { store.skipSong(store.currentSong?.queue_id); showToast('⏭ Diskip') }
function changeKey(delta) { store.changeKey(Math.max(-12, Math.min(12, store.keyShift + delta))) }

function confirmRemove(item) {
  confirm.value = { show: true, message: `Hapus "${item.song?.title || 'lagu ini'}"?`, onConfirm: () => { store.removeFromQueue(item.id); confirm.value.show = false; showToast('🗑️ Dihapus') } }
}

function showToast(msg) { toast.value = { show: true, message: msg }; setTimeout(() => toast.value.show = false, 2000) }

async function fetchRooms() {
  try { const res = await axios.get('/api/rooms'); rooms.value = res.data; console.log('Rooms loaded:', res.data) } catch(e) { console.error('Fetch rooms error:', e) }
}

function selectRoom(room) {
  console.log('Selected room:', room.name)
  store.setRoomId(room.name)
  showRoomList.value = false
  store.fetchQueue()
  store.fetchMood()
  showToast('📍 Room: ' + room.name)
}

function refreshAll() { store.fetchSongs(); store.fetchGenres(); store.fetchQueue(); store.fetchStats(); store.fetchMood(); fetchRooms(); showToast('🔄 Data diperbarui') }

function thumbGradient(genre) {
  const map = { 'Pop Indonesia': 'linear-gradient(135deg, #ef4444, #f87171)', 'Dangdut': 'linear-gradient(135deg, #f59e0b, #fbbf24)', 'K-Pop': 'linear-gradient(135deg, #ec4899, #f472b6)', 'Barat': 'linear-gradient(135deg, #3b82f6, #60a5fa)' }
  return map[genre] || 'linear-gradient(135deg, #ef4444, #3b82f6)'
}

function launchPlayer() {
  const room = encodeURIComponent(store.roomId)
  const url = `${window.location.origin}/player?screen=2&room=${room}`
  window.open(url, '_blank', 'width=1280,height=720')
  showToast('📺 Player diluncurkan untuk ' + store.roomId)
}

onMounted(() => { store.setScreenType('operator'); store.fetchSongs(); store.fetchGenres(); store.fetchQueue(); store.fetchStats(); store.fetchMood(); fetchRooms() })
</script>

<style scoped>
.operator-app { height: 100vh; display: flex; flex-direction: column; background: #f1f5f9; font-family: 'Inter', sans-serif; color: #1e293b; overflow: hidden; }

.top-bar { display: flex; align-items: center; padding: 0.5rem 1rem; background: white; border-bottom: 1px solid #e2e8f0; gap: 1rem; z-index: 20; }
.bar-left { display: flex; align-items: center; gap: 0.5rem; min-width: 180px; position: relative; }
.bar-logo { width: 32px; height: 32px; border-radius: 8px; object-fit: contain; }
.bar-title { font-weight: 700; font-size: 0.85rem; display: block; }
.room-select-wrap { position: relative; display: flex; align-items: center; gap: 0.25rem; cursor: pointer; padding: 0.15rem 0.5rem; border-radius: 6px; background: #f1f5f9; }
.room-select-wrap:hover { background: #e2e8f0; }
.bar-room { font-size: 0.7rem; color: #475569; font-weight: 500; }
.room-arrow { font-size: 0.55rem; color: #94a3b8; }
.room-dropdown { position: absolute; top: calc(100% + 6px); left: 0; background: white; border: 1px solid #e2e8f0; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.12); z-index: 200; min-width: 180px; overflow: hidden; }
.room-option { display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.85rem; cursor: pointer; font-size: 0.82rem; transition: all 0.15s; }
.room-option:hover { background: #f8fafc; }
.room-option.active { background: #fef2f2; color: #ef4444; font-weight: 600; }
.room-cap { font-size: 0.65rem; color: #94a3b8; }
.room-empty { padding: 0.6rem 0.85rem; font-size: 0.75rem; color: #94a3b8; text-align: center; }

.bar-center { flex: 1; }
.search-box { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 0.75rem; font-size: 0.85rem; z-index: 1; }
.search-input { width: 100%; padding: 0.5rem 1rem 0.5rem 2.25rem; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 0.85rem; background: #f8fafc; transition: all 0.2s; }
.search-input:focus { outline: none; border-color: #ef4444; background: white; box-shadow: 0 0 0 3px rgba(239,68,68,0.06); }
.search-clear { position: absolute; right: 0.5rem; background: #e2e8f0; border: none; width: 22px; height: 22px; border-radius: 50%; cursor: pointer; font-size: 0.65rem; }
.bar-right { display: flex; align-items: center; gap: 0.5rem; font-size: 0.75rem; color: #64748b; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #ef4444; }
.status-dot.online { background: #10b981; }
.btn-launch { padding: 0.4rem 0.85rem; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 8px; font-weight: 600; font-size: 0.75rem; cursor: pointer; white-space: nowrap; transition: all 0.2s; display: flex; align-items: center; gap: 0.35rem; }
.btn-launch:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,130,246,0.3); }
.btn-icon { background: none; border: none; font-size: 1.1rem; cursor: pointer; padding: 0.25rem; text-decoration: none; }

.main-layout { flex: 1; display: flex; overflow: hidden; }
.queue-panel { width: 280px; min-width: 280px; background: white; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid #f1f5f9; }
.panel-header h3 { font-size: 0.85rem; font-weight: 700; }
.queue-badge { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 0.1rem 0.55rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 700; }
.now-playing-card { margin: 0.5rem 0.75rem; padding: 0.6rem 0.75rem; background: linear-gradient(135deg, #fef2f2, #eff6ff); border-radius: 10px; border: 1px solid #fecaca; display: flex; align-items: center; gap: 0.6rem; }
.np-equalizer { display: flex; align-items: flex-end; gap: 2px; height: 20px; }
.eq-bar { width: 3px; background: #ef4444; border-radius: 1px; animation: eq 1s ease-in-out infinite; }
.eq-bar:nth-child(1) { height: 8px; animation-delay: 0s; } .eq-bar:nth-child(2) { height: 16px; animation-delay: 0.2s; } .eq-bar:nth-child(3) { height: 10px; animation-delay: 0.4s; } .eq-bar:nth-child(4) { height: 18px; animation-delay: 0.6s; } .eq-bar:nth-child(5) { height: 12px; animation-delay: 0.8s; }
@keyframes eq { 0%,100%{transform:scaleY(.4)} 50%{transform:scaleY(1)} }
.np-label { font-size: 0.55rem; text-transform: uppercase; letter-spacing: 1px; color: #ef4444; font-weight: 700; }
.np-title { font-weight: 600; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px; }
.np-artist { font-size: 0.7rem; color: #94a3b8; }
.queue-list { flex: 1; overflow-y: auto; padding: 0 0.75rem; }
.queue-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; border-radius: 8px; margin-bottom: 0.2rem; transition: all 0.2s; }
.queue-item:hover { background: #f8fafc; }
.queue-item.is-next { background: linear-gradient(135deg, #fef2f2, #fff7ed); border: 1px solid #fed7aa; }
.queue-rank { width: 24px; height: 24px; background: #f1f5f9; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.7rem; color: #64748b; flex-shrink: 0; }
.rank-next { background: linear-gradient(135deg, #ef4444, #f97316); color: white; }
.queue-detail { flex: 1; min-width: 0; }
.queue-song { font-weight: 600; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.queue-artist { font-size: 0.68rem; color: #94a3b8; }
.queue-actions { display: flex; gap: 0.2rem; }
.btn-play-now { width: 24px; height: 24px; background: #10b981; border: none; border-radius: 5px; color: white; cursor: pointer; font-size: 0.65rem; }
.btn-remove { width: 24px; height: 24px; background: transparent; border: none; color: #ef4444; cursor: pointer; font-size: 0.75rem; }
.btn-remove:hover { background: #fef2f2; border-radius: 5px; }
.queue-empty { text-align: center; padding: 2rem 1rem; color: #94a3b8; }
.empty-art { font-size: 2.5rem; margin-bottom: 0.5rem; }
.empty-hint { font-size: 0.7rem; margin-top: 0.25rem; } .empty-hint strong { color: #ef4444; }
.queue-footer { display: flex; gap: 0.35rem; padding: 0.5rem 0.75rem; border-top: 1px solid #f1f5f9; }
.stat-pill { flex: 1; text-align: center; background: #f8fafc; border-radius: 8px; padding: 0.3rem; font-size: 0.6rem; color: #94a3b8; }
.stat-pill strong { display: block; font-size: 0.8rem; color: #1e293b; }
.browser-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #f8fafc; }
.filter-strip { display: flex; gap: 0.3rem; padding: 0.5rem 1rem; background: white; border-bottom: 1px solid #f1f5f9; overflow-x: auto; scrollbar-width: none; }
.filter-chip { display: flex; align-items: center; gap: 0.25rem; padding: 0.35rem 0.7rem; background: #f1f5f9; border: 2px solid transparent; border-radius: 2rem; cursor: pointer; font-size: 0.72rem; font-weight: 500; color: #475569; white-space: nowrap; transition: all 0.2s; }
.filter-chip.active { background: white; border-color: #ef4444; color: #ef4444; font-weight: 600; }
.song-grid { flex: 1; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.35rem; padding: 0.5rem 1rem; align-content: start; }
.song-card { display: flex; align-items: center; gap: 0.5rem; background: white; padding: 0.5rem 0.6rem; border-radius: 10px; cursor: pointer; transition: all 0.2s; border: 1px solid #f1f5f9; }
.song-card:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.05); border-color: #fecaca; transform: translateY(-1px); }
.song-card.is-in-queue { border-color: #bbf7d0; background: #f0fdf4; }
.card-thumb { width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; position: relative; }
.thumb-icon { font-size: 0.85rem; color: white; }
.thumb-badge { position: absolute; bottom: -3px; right: -3px; width: 14px; height: 14px; background: #10b981; color: white; border-radius: 50%; font-size: 0.5rem; display: flex; align-items: center; justify-content: center; }
.card-info { flex: 1; min-width: 0; }
.card-title { font-weight: 600; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-artist { font-size: 0.7rem; color: #94a3b8; }
.card-meta { display: flex; gap: 0.3rem; margin-top: 0.1rem; }
.meta-tag { font-size: 0.58rem; padding: 0.05rem 0.3rem; background: #eff6ff; color: #3b82f6; border-radius: 3px; }
.meta-plays { font-size: 0.58rem; color: #cbd5e1; }
.card-add { width: 30px; height: 30px; border-radius: 50%; border: 2px solid #ef4444; background: white; color: #ef4444; font-size: 1rem; font-weight: 700; cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.card-add:hover { background: #ef4444; color: white; transform: scale(1.1); }
.browser-empty { grid-column: 1/-1; text-align: center; padding: 3rem; color: #94a3b8; }
.control-panel { width: 240px; min-width: 240px; background: white; border-left: 1px solid #e2e8f0; padding: 0.6rem; display: flex; flex-direction: column; gap: 0.5rem; overflow-y: auto; }
.ctrl-section { background: #f8fafc; border-radius: 10px; padding: 0.65rem; border: 1px solid #f1f5f9; }
.ctrl-title { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 0.5rem; }
.playback-btns { display: flex; flex-direction: column; gap: 0.3rem; }
.pb-btn { width: 100%; padding: 0.5rem; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.8rem; transition: all 0.2s; }
.pb-btn.primary { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
.pb-btn:not(.primary) { background: #f1f5f9; color: #475569; }
.pb-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.now-brief { text-align: center; margin-top: 0.35rem; font-size: 0.7rem; color: #94a3b8; }
.brief-title { font-weight: 600; color: #1e293b; }
.key-display { display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 0.4rem; }
.key-btn { width: 36px; height: 36px; border: 2px solid #e2e8f0; border-radius: 10px; background: white; cursor: pointer; font-size: 1.1rem; font-weight: 700; color: #475569; }
.key-btn:hover:not(:disabled) { border-color: #ef4444; color: #ef4444; } .key-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.key-value { text-align: center; cursor: pointer; padding: 0.2rem 0.5rem; border-radius: 8px; }
.key-num { font-size: 1.3rem; font-weight: 800; display: block; } .key-label { font-size: 0.6rem; color: #94a3b8; }
.key-presets { display: flex; gap: 0.2rem; justify-content: center; }
.preset-btn { padding: 0.2rem 0.45rem; background: #f1f5f9; border: 2px solid transparent; border-radius: 4px; cursor: pointer; font-size: 0.65rem; font-weight: 600; color: #64748b; }
.preset-btn.active { background: white; border-color: #ef4444; color: #ef4444; }
.vocal-btns { display: flex; gap: 0.25rem; margin-bottom: 0.35rem; }
.vocal-btn { flex: 1; padding: 0.35rem; background: #f1f5f9; border: 2px solid transparent; border-radius: 6px; cursor: pointer; font-size: 0.65rem; font-weight: 500; color: #64748b; }
.vocal-btn.active { background: white; border-color: #ef4444; color: #ef4444; font-weight: 600; }
.ai-toggle { width: 100%; padding: 0.35rem; border: 1px solid #fecaca; border-radius: 6px; background: #fef2f2; color: #dc2626; cursor: pointer; font-size: 0.68rem; font-weight: 600; }
.ai-toggle.active { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; border-color: transparent; }
.volume-row { display: flex; align-items: center; gap: 0.4rem; }
.vol-slider { flex: 1; accent-color: #ef4444; height: 4px; } .vol-value { text-align: center; font-weight: 700; font-size: 0.8rem; margin-top: 0.2rem; }
.ai-btn { width: 100%; padding: 0.4rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.7rem; font-weight: 600; margin-bottom: 0.25rem; }
.ai-btn.party { background: #fef3c7; color: #92400e; } .ai-btn.romantic { background: #fce7f3; color: #9d174d; } .ai-btn.nostalgia { background: #f3e8ff; color: #6b21a8; }
.mood-indicator { text-align: center; margin-top: 0.35rem; font-size: 0.7rem; color: #64748b; }
.operator-toast { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%) translateY(20px); background: #1e293b; color: white; padding: 0.5rem 1.25rem; border-radius: 2rem; font-size: 0.8rem; font-weight: 500; z-index: 200; opacity: 0; transition: all 0.3s ease; pointer-events: none; white-space: nowrap; }
.operator-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.confirm-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 150; display: flex; align-items: center; justify-content: center; }
.confirm-card { background: white; border-radius: 16px; padding: 1.5rem; text-align: center; max-width: 300px; width: 90%; }
.confirm-icon { font-size: 2rem; display: block; margin-bottom: 0.5rem; }
.confirm-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.btn-cancel { flex: 1; padding: 0.5rem; background: #f1f5f9; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
.btn-danger { flex: 1; padding: 0.5rem; background: #ef4444; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
</style>
