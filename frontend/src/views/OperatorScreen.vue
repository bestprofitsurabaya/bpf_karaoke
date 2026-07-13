<template>
  <div class="operator-layout">
    <!-- LEFT SIDEBAR - QUEUE -->
    <aside class="sidebar-queue">
      <!-- Header -->
      <div class="sidebar-header">
        <div class="header-title">
          <span class="header-icon">🎵</span>
          <h2>Antrian</h2>
        </div>
        <span class="queue-badge">{{ store.waitingQueue.length }}</span>
      </div>

      <!-- Now Playing Mini -->
      <div class="now-playing-mini" v-if="store.currentSong && store.isPlaying">
        <div class="np-wave">
          <span class="wave-bar"></span><span class="wave-bar"></span>
          <span class="wave-bar"></span><span class="wave-bar"></span>
          <span class="wave-bar"></span>
        </div>
        <div class="np-info">
          <span class="np-label">Sedang Diputar</span>
          <div class="np-title">{{ store.currentSong.song_title || '♪' }}</div>
        </div>
      </div>

      <!-- Queue List -->
      <div class="queue-list">
        <div
          v-for="(item, index) in store.waitingQueue"
          :key="item.id"
          class="queue-item"
          :class="{ 'is-next': index === 0 }"
        >
          <div class="queue-rank" :class="{ 'rank-next': index === 0 }">
            {{ index + 1 }}
          </div>
          <div class="queue-detail">
            <div class="queue-song">{{ item.song?.title || 'Unknown' }}</div>
            <div class="queue-artist">{{ item.song?.artist || '-' }}</div>
          </div>
          <div class="queue-actions">
            <button
              v-if="index === 0"
              class="btn-play-now"
              @click="playNow(item)"
              title="Putar Sekarang"
            >▶</button>
            <button class="btn-remove" @click="store.removeFromQueue(item.id)" title="Hapus">✕</button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="store.waitingQueue.length === 0" class="queue-empty">
          <span class="empty-icon">🎶</span>
          <p>Antrian kosong</p>
          <p class="empty-hint">Klik lagu untuk menambahkan</p>
        </div>
      </div>

      <!-- Quick Stats Footer -->
      <div class="sidebar-footer">
        <div class="stat-mini">
          <span>🎵</span>
          <strong>{{ store.stats.total_songs || 0 }}</strong>
          <span>Lagu</span>
        </div>
        <div class="stat-mini">
          <span :class="store.isConnected ? 'online' : 'offline'">●</span>
          <strong>{{ store.isConnected ? 'ON' : 'OFF' }}</strong>
          <span>Server</span>
        </div>
      </div>
    </aside>

    <!-- MAIN CONTENT - SONG BROWSER -->
    <main class="main-content">
      <!-- Top Bar -->
      <div class="top-bar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input
            v-model="store.searchQuery"
            type="text"
            placeholder="Cari lagu atau artis..."
            class="search-input"
            @input="debouncedSearch"
          />
          <button v-if="store.searchQuery" class="search-clear" @click="clearSearch">✕</button>
        </div>
        <div class="top-buttons">
          <button class="btn-top" @click="showFilters = !showFilters">
            🎸 {{ showFilters ? 'Sembunyi' : 'Filter' }}
          </button>
          <button class="btn-top" @click="store.fetchSongs()">🔄</button>
        </div>
      </div>

      <!-- Genre Filter Chips -->
      <div class="filter-bar" v-if="showFilters">
        <button
          @click="setFilter(null)"
          class="filter-chip"
          :class="{ active: !store.selectedGenre }"
        >Semua</button>
        <button
          v-for="g in store.genres"
          :key="g.genre"
          @click="setFilter(g.genre)"
          class="filter-chip"
          :class="{ active: store.selectedGenre === g.genre }"
        >
          {{ g.genre }} <span class="chip-count">{{ g.count }}</span>
        </button>
      </div>

      <!-- Quick Categories -->
      <div class="quick-cats">
        <button @click="setFilter('Pop Indonesia')" class="cat-btn">🇮🇩 Pop</button>
        <button @click="setFilter('Dangdut')" class="cat-btn">🎶 Dangdut</button>
        <button @click="setFilter('Barat')" class="cat-btn">🌍 Barat</button>
        <button @click="setFilter('K-Pop')" class="cat-btn">🇰🇷 K-Pop</button>
        <button @click="setFilter('Mandarin')" class="cat-btn">🇨🇳 Mandarin</button>
        <button @click="setFilter(null)" class="cat-btn cat-all">🔥 Semua</button>
      </div>

      <!-- Song Grid -->
      <div class="song-grid">
        <div
          v-for="song in store.filteredSongs"
          :key="song.id"
          class="song-card"
          @click="addToQueue(song)"
        >
          <div class="song-thumb" :style="{ background: thumbColor(song.genre) }">
            <span>🎵</span>
          </div>
          <div class="song-info">
            <div class="song-title">{{ song.title }}</div>
            <div class="song-artist">{{ song.artist || 'Unknown' }}</div>
            <div class="song-meta">
              <span v-if="song.genre" class="meta-genre">{{ song.genre }}</span>
              <span class="meta-plays">▶ {{ song.play_count }}x</span>
            </div>
          </div>
          <button class="btn-add" @click.stop="addToQueue(song)">+</button>
        </div>

        <div v-if="store.filteredSongs.length === 0" class="empty-state">
          <span>📭</span>
          <h3>Tidak ditemukan</h3>
          <p>Coba kata kunci lain</p>
        </div>
      </div>
    </main>

    <!-- RIGHT PANEL - PLAYER CONTROLS -->
    <aside class="panel-control">
      <!-- Audio Controls -->
      <div class="control-section">
        <h3 class="section-title">🎚️ Audio</h3>
        <div class="control-row">
          <span>🔊 Volume</span>
          <input
            type="range"
            min="0"
            max="100"
            :value="store.currentVolume"
            @input="store.setVolume(Number($event.target.value))"
            class="slider"
          />
          <span class="value">{{ store.currentVolume }}%</span>
        </div>
        <div class="control-row">
          <span>🎤 Vokal</span>
          <div class="btn-group">
            <button
              v-for="mode in ['stereo', 'left', 'right']"
              :key="mode"
              @click="store.toggleVocal(mode)"
              class="btn-mode"
              :class="{ active: store.vocalMode === mode }"
            >{{ mode === 'stereo' ? 'Stereo' : mode === 'left' ? 'Kiri' : 'Kanan' }}</button>
          </div>
        </div>
      </div>

      <!-- Playback Controls -->
      <div class="control-section" v-if="store.currentSong">
        <h3 class="section-title">▶️ Pemutaran</h3>
        <div class="playback-buttons">
          <button
            @click="store.isPlaying ? store.pauseSong() : store.resumeSong()"
            class="btn-playback primary"
          >
            {{ store.isPlaying ? '⏸ Pause' : '▶ Play' }}
          </button>
          <button @click="skipCurrent" class="btn-playback">⏭ Skip</button>
        </div>
        <div class="now-info" v-if="store.currentSong">
          <span class="now-playing-label">Sedang:</span>
          <span class="now-playing-title">{{ store.currentSong.song_title || '-' }}</span>
        </div>
      </div>

      <!-- AI Quick Panel -->
      <div class="control-section ai-section">
        <h3 class="section-title">🤖 AI Cepat</h3>
        <button @click="generatePartyPlaylist" class="btn-ai">
          🎉 Party Mix
        </button>
        <button @click="generateRomanticPlaylist" class="btn-ai">
          💕 Romantic
        </button>
        <div class="ai-mood" v-if="aiMood">
          <span>{{ aiMood.mood_emoji || '🎵' }}</span>
          <span>Mood: {{ aiMood.current_mood || 'neutral' }}</span>
        </div>
      </div>
    </aside>

    <!-- Toast -->
    <div class="toast" v-if="showToast">✅ Ditambahkan!</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import axios from 'axios'

const store = useKaraokeStore()
const showFilters = ref(false)
const showToast = ref(false)
const aiMood = ref(null)

let debounceTimer

const debouncedSearch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => store.fetchSongs(), 300)
}

const clearSearch = () => {
  store.searchQuery = ''
  store.fetchSongs()
}

const setFilter = (genre) => {
  store.selectedGenre = store.selectedGenre === genre ? null : genre
  store.fetchSongs()
}

const addToQueue = async (song) => {
  const ok = await store.addToQueue(song.id)
  if (ok) {
    showToast.value = true
    setTimeout(() => { showToast.value = false }, 1500)
  }
}

const playNow = (item) => {
  store.playSong(item.song_id, item.id)
}

const skipCurrent = () => {
  store.skipSong(store.currentSong?.queue_id)
}

const thumbColor = (genre) => {
  const map = {
    'Pop Indonesia': 'linear-gradient(135deg, #ef4444, #f87171)',
    'Dangdut': 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    'K-Pop': 'linear-gradient(135deg, #ec4899, #f472b6)',
    'Barat': 'linear-gradient(135deg, #3b82f6, #60a5fa)',
  }
  return map[genre] || 'linear-gradient(135deg, #ef4444, #3b82f6)'
}

const generatePartyPlaylist = async () => {
  try {
    const res = await axios.post('/api/ai/playlist/generate', { type: 'mood', value: 'party', count: 10 })
    if (res.data.songs) {
      res.data.songs.forEach(s => store.addToQueue(s.id))
    }
  } catch (e) { console.error(e) }
}

const generateRomanticPlaylist = async () => {
  try {
    const res = await axios.post('/api/ai/playlist/generate', { type: 'mood', value: 'romantic', count: 10 })
    if (res.data.songs) {
      res.data.songs.forEach(s => store.addToQueue(s.id))
    }
  } catch (e) { console.error(e) }
}

const fetchMood = async () => {
  try {
    const res = await axios.get('/api/ai/mood/default')
    aiMood.value = res.data
  } catch (e) { console.error(e) }
}

onMounted(() => {
  store.setScreenType('operator')
  store.fetchSongs()
  store.fetchGenres()
  store.fetchQueue()
  store.fetchStats()
  fetchMood()
})
</script>

<style scoped>
/* ============================================ */
/* OPERATOR LAYOUT - 3 Column */
/* ============================================ */

.operator-layout {
  display: flex;
  height: 100vh;
  background: #f8fafc;
  color: #1e293b;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

/* ============================================ */
/* LEFT SIDEBAR - QUEUE */
/* ============================================ */

.sidebar-queue {
  width: 300px;
  min-width: 300px;
  background: white;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 15px rgba(0,0,0,0.03);
  z-index: 10;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid #f1f5f9;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-icon { font-size: 1.2rem; }

.header-title h2 {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}

.queue-badge {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  padding: 0.2rem 0.7rem;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-weight: 700;
}

/* Now Playing Mini */
.now-playing-mini {
  margin: 0.75rem 1rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, #fef2f2, #eff6ff);
  border-radius: 10px;
  border: 1px solid #fecaca;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.np-wave {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 24px;
}

.wave-bar {
  width: 3px;
  background: #ef4444;
  border-radius: 2px;
  animation: wave 1s ease-in-out infinite;
}

.wave-bar:nth-child(1) { height: 10px; animation-delay: 0s; }
.wave-bar:nth-child(2) { height: 20px; animation-delay: 0.2s; }
.wave-bar:nth-child(3) { height: 14px; animation-delay: 0.4s; }
.wave-bar:nth-child(4) { height: 22px; animation-delay: 0.6s; }
.wave-bar:nth-child(5) { height: 16px; animation-delay: 0.8s; }

@keyframes wave {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}

.np-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #ef4444;
  font-weight: 600;
}

.np-title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

/* Queue List */
.queue-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 0.75rem;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.5rem;
  border-radius: 8px;
  margin-bottom: 0.35rem;
  transition: all 0.2s;
}

.queue-item:hover { background: #f8fafc; }

.queue-item.is-next {
  background: linear-gradient(135deg, #fef2f2, #fff7ed);
  border: 1px solid #fed7aa;
}

.queue-rank {
  width: 28px;
  height: 28px;
  background: #f1f5f9;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.8rem;
  color: #64748b;
  flex-shrink: 0;
}

.rank-next {
  background: linear-gradient(135deg, #ef4444, #f97316);
  color: white;
}

.queue-detail {
  flex: 1;
  min-width: 0;
}

.queue-song {
  font-weight: 600;
  font-size: 0.82rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-artist {
  font-size: 0.72rem;
  color: #94a3b8;
}

.queue-actions {
  display: flex;
  gap: 0.25rem;
}

.btn-play-now {
  width: 26px;
  height: 26px;
  background: #10b981;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  font-size: 0.7rem;
}

.btn-remove {
  width: 26px;
  height: 26px;
  background: transparent;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-remove:hover { background: #fef2f2; border-radius: 6px; }

.queue-empty {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.empty-icon { font-size: 2rem; display: block; margin-bottom: 0.5rem; }
.empty-hint { font-size: 0.75rem; }

/* Sidebar Footer */
.sidebar-footer {
  display: flex;
  border-top: 1px solid #f1f5f9;
  padding: 0.6rem 1rem;
  gap: 0.5rem;
}

.stat-mini {
  flex: 1;
  text-align: center;
  font-size: 0.7rem;
  color: #94a3b8;
}

.stat-mini strong {
  display: block;
  font-size: 0.85rem;
  color: #1e293b;
}

.online { color: #10b981; }
.offline { color: #ef4444; }

/* ============================================ */
/* MAIN CONTENT */
/* ============================================ */

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8fafc;
}

.top-bar {
  display: flex;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  background: white;
  border-bottom: 1px solid #e2e8f0;
}

.search-box {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 0.875rem;
  font-size: 0.9rem;
  z-index: 1;
}

.search-input {
  width: 100%;
  padding: 0.65rem 1rem 0.65rem 2.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9rem;
  background: #f8fafc;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #ef4444;
  background: white;
  box-shadow: 0 0 0 3px rgba(239,68,68,0.08);
}

.search-clear {
  position: absolute;
  right: 0.75rem;
  background: #e2e8f0;
  border: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  cursor: pointer;
  color: #64748b;
  font-size: 0.7rem;
}

.top-buttons {
  display: flex;
  gap: 0.4rem;
}

.btn-top {
  padding: 0.5rem 0.875rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  color: #475569;
  transition: all 0.2s;
}

.btn-top:hover { background: #e2e8f0; }

/* Filter Bar */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.75rem 1.25rem;
  background: white;
  border-bottom: 1px solid #f1f5f9;
}

.filter-chip {
  padding: 0.35rem 0.75rem;
  background: #f1f5f9;
  border: 2px solid transparent;
  border-radius: 2rem;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 500;
  color: #475569;
  transition: all 0.2s;
}

.filter-chip:hover { background: #e2e8f0; }

.filter-chip.active {
  background: white;
  border-color: #ef4444;
  color: #ef4444;
  font-weight: 600;
}

.chip-count {
  background: #e2e8f0;
  padding: 0.1rem 0.35rem;
  border-radius: 1rem;
  font-size: 0.65rem;
  margin-left: 0.25rem;
}

/* Quick Categories */
.quick-cats {
  display: flex;
  gap: 0.4rem;
  padding: 0.6rem 1.25rem;
  background: white;
  border-bottom: 1px solid #f1f5f9;
}

.cat-btn {
  padding: 0.3rem 0.7rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 2rem;
  cursor: pointer;
  font-size: 0.75rem;
  color: #dc2626;
  transition: all 0.2s;
}

.cat-btn:hover { background: #fee2e2; }

.cat-all {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #2563eb;
}

/* Song Grid */
.song-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  align-content: start;
}

.song-card {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  background: white;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #f1f5f9;
}

.song-card:hover {
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  border-color: #fecaca;
  transform: translateY(-1px);
}

.song-thumb {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1rem;
  color: white;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-title {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-artist {
  font-size: 0.75rem;
  color: #94a3b8;
}

.song-meta {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.15rem;
}

.meta-genre {
  font-size: 0.6rem;
  padding: 0.1rem 0.35rem;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 3px;
  font-weight: 500;
}

.meta-plays {
  font-size: 0.6rem;
  color: #cbd5e1;
}

.btn-add {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-add:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(239,68,68,0.3);
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem;
  color: #94a3b8;
}

.empty-state span { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
.empty-state h3 { color: #64748b; margin-bottom: 0.25rem; }

/* ============================================ */
/* RIGHT PANEL - CONTROLS */
/* ============================================ */

.panel-control {
  width: 260px;
  min-width: 260px;
  background: white;
  border-left: 1px solid #e2e8f0;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
}

.control-section {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid #f1f5f9;
}

.section-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
  margin-bottom: 0.75rem;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.65rem;
  font-size: 0.78rem;
  font-weight: 500;
}

.slider {
  flex: 1;
  accent-color: #ef4444;
  height: 4px;
}

.value {
  font-weight: 700;
  font-size: 0.75rem;
  min-width: 35px;
  text-align: right;
}

.btn-group {
  display: flex;
  gap: 0.25rem;
}

.btn-mode {
  padding: 0.3rem 0.5rem;
  background: #f1f5f9;
  border: 2px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.7rem;
  font-weight: 500;
  color: #64748b;
  transition: all 0.2s;
}

.btn-mode.active {
  background: white;
  border-color: #ef4444;
  color: #ef4444;
  font-weight: 600;
}

.playback-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.btn-playback {
  width: 100%;
  padding: 0.6rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-playback.primary {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.btn-playback:not(.primary) {
  background: #f1f5f9;
  color: #475569;
}

.now-info {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #94a3b8;
  text-align: center;
}

.now-playing-title {
  font-weight: 600;
  color: #1e293b;
}

.ai-section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.btn-ai {
  width: 100%;
  padding: 0.5rem;
  background: linear-gradient(135deg, #eff6ff, #fef2f2);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 500;
  color: #3b82f6;
  transition: all 0.2s;
}

.btn-ai:hover { background: linear-gradient(135deg, #dbeafe, #fee2e2); }

.ai-mood {
  text-align: center;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.35rem;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: #10b981;
  color: white;
  padding: 0.6rem 1.5rem;
  border-radius: 2rem;
  font-weight: 600;
  font-size: 0.85rem;
  z-index: 100;
  box-shadow: 0 10px 25px rgba(16,185,129,0.3);
  animation: toastIn 0.3s ease-out;
}

@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(20px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
