<template>
  <div class="operator-layout">
    <!-- Sidebar Queue -->
    <aside class="queue-sidebar">
      <div class="sidebar-header">
        <div class="header-brand">
          <span class="brand-dot"></span>
          <h2>Antrian Lagu</h2>
        </div>
        <span class="queue-count">{{ store.waitingQueue.length }}</span>
      </div>

      <!-- Current Playing -->
      <div class="now-playing-card" v-if="store.currentSong">
        <div class="np-glow"></div>
        <div class="np-content">
          <span class="np-label">🎤 Sedang Diputar</span>
          <div class="np-title">{{ store.currentSong.song_title || 'Loading...' }}</div>
          <div class="np-controls-mini">
            <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()" class="ctrl-mini">
              {{ store.isPlaying ? '⏸' : '▶' }}
            </button>
            <button @click="store.skipSong(store.currentSong?.queue_id)" class="ctrl-mini">⏭</button>
          </div>
        </div>
      </div>

      <!-- Queue List -->
      <div class="queue-list">
        <div v-for="(item, index) in store.waitingQueue" :key="item.id"
             class="queue-item" :class="{ 'is-next': index === 0 }"
             :style="{ animationDelay: `${index * 0.05}s` }">
          <div class="queue-rank" :class="{ 'rank-next': index === 0 }">
            {{ index + 1 }}
          </div>
          <div class="queue-info">
            <div class="queue-title">{{ item.song?.title || 'Unknown' }}</div>
            <div class="queue-artist">{{ item.song?.artist || 'Unknown Artist' }}</div>
          </div>
          <div class="queue-actions">
            <button v-if="index === 0" class="action-play" @click="playNow(item)" title="Play Now">▶</button>
            <button class="action-remove" @click="store.removeFromQueue(item.id)" title="Remove">✕</button>
          </div>
        </div>
        <div v-if="store.waitingQueue.length === 0" class="queue-empty">
          <span class="empty-icon">🎵</span>
          <p>Antrian kosong</p>
          <p class="empty-hint">Klik lagu untuk menambahkan</p>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="quick-stats">
        <div class="stat-item">
          <span class="stat-icon">📊</span>
          <span class="stat-value">{{ store.stats.total_songs || 0 }}</span>
          <span class="stat-label">Lagu</span>
        </div>
        <div class="stat-item">
          <span class="stat-icon">🟢</span>
          <span class="stat-value">{{ store.isConnected ? 'ON' : 'OFF' }}</span>
          <span class="stat-label">Server</span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Top Bar -->
      <div class="top-bar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input v-model="store.searchQuery" type="text"
                 placeholder="Cari judul lagu atau nama artis..."
                 class="search-input"
                 @input="debouncedSearch">
          <button v-if="store.searchQuery" class="search-clear" @click="clearSearch">✕</button>
        </div>
        <div class="top-actions">
          <button class="action-btn" @click="showGenreFilter = !showGenreFilter">🎸 Genre</button>
          <button class="action-btn" @click="store.fetchSongs()">🔄 Refresh</button>
        </div>
      </div>

      <!-- Genre Filter Chips -->
      <div class="genre-chips" v-if="showGenreFilter">
        <button @click="filterByGenre(null)" class="chip" :class="{ active: !store.selectedGenre }">🎵 Semua</button>
        <button v-for="g in store.genres" :key="g.genre"
                @click="filterByGenre(g.genre)"
                class="chip" :class="{ active: store.selectedGenre === g.genre }">
          {{ getGenreIcon(g.genre) }} {{ g.genre }}
          <span class="chip-count">{{ g.count }}</span>
        </button>
      </div>

      <!-- Quick Categories -->
      <div class="quick-cats">
        <span class="cat-label">Kategori Cepat:</span>
        <button @click="quickFilter('Pop Indonesia')" class="cat-pill">🇮🇩 Pop Indo</button>
        <button @click="quickFilter('Dangdut')" class="cat-pill">🎶 Dangdut</button>
        <button @click="quickFilter('Barat')" class="cat-pill">🌍 Barat</button>
        <button @click="quickFilter('K-Pop')" class="cat-pill">🇰🇷 K-Pop</button>
        <button @click="quickFilter('Mandarin')" class="cat-pill">🇨🇳 Mandarin</button>
      </div>

      <!-- Songs Grid -->
      <div class="songs-grid">
        <div v-for="(song, index) in store.filteredSongs" :key="song.id"
             class="song-card"
             :style="{ animationDelay: `${index * 0.02}s` }"
             @click="addToQueue(song)">
          <div class="song-thumb" :style="{ background: getThumbGradient(song.genre) }">
            <span class="thumb-icon">🎵</span>
            <span class="song-id">#{{ song.id }}</span>
          </div>
          <div class="song-details">
            <div class="song-title">{{ song.title }}</div>
            <div class="song-artist">{{ song.artist || 'Unknown Artist' }}</div>
            <div class="song-meta">
              <span class="meta-genre" v-if="song.genre">{{ song.genre }}</span>
              <span class="meta-plays">▶ {{ song.play_count }}x</span>
              <span class="meta-lang" v-if="song.language">{{ song.language }}</span>
            </div>
          </div>
          <button class="add-btn" @click.stop="addToQueue(song)" title="Tambah ke Antrian">
            <span>+</span>
          </button>
        </div>

        <!-- Empty State -->
        <div v-if="store.filteredSongs.length === 0" class="empty-state">
          <span class="empty-icon">🔍</span>
          <h3>Tidak ada lagu ditemukan</h3>
          <p>Coba kata kunci lain atau scan folder media di Admin Panel</p>
        </div>
      </div>
    </main>

    <!-- AI Panel -->
    <aside class="ai-sidebar">
      <AIRecommendations @add-to-queue="(songId) => addToQueueById(songId)" />
      <VoiceScoring class="mt-3" />
    </aside>

    <!-- Success Toast -->
    <div class="add-toast" v-if="showAddToast">
      <span>✅ Ditambahkan ke antrian!</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import AIRecommendations from '@/components/ai/AIRecommendations.vue'
import VoiceScoring from '@/components/ai/VoiceScoring.vue'

const store = useKaraokeStore()
const showGenreFilter = ref(false)
const showAddToast = ref(false)

let debounceTimer
const debouncedSearch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    store.fetchSongs()
  }, 300)
}

const clearSearch = () => {
  store.searchQuery = ''
  store.fetchSongs()
}

const filterByGenre = (genre) => {
  store.selectedGenre = genre
  store.fetchSongs()
}

const quickFilter = (genre) => {
  store.selectedGenre = store.selectedGenre === genre ? null : genre
  store.fetchSongs()
}

const addToQueue = async (song) => {
  const success = await store.addToQueue(song.id)
  if (success) {
    showAddToast.value = true
    setTimeout(() => { showAddToast.value = false }, 2000)
  }
}

const addToQueueById = async (songId) => {
  await addToQueue({ id: songId })
}

const playNow = (item) => {
  store.playSong(item.song_id, item.id)
}

const getGenreIcon = (genre) => {
  const icons = {
    'Pop Indonesia': '🇮🇩', 'Dangdut': '🎶', 'Rock': '🎸',
    'K-Pop': '🇰🇷', 'Mandarin': '🇨🇳', 'Barat': '🌍',
    'Anak': '👶', 'Daerah': '🏠', 'Religi': '🕌'
  }
  return icons[genre] || '🎵'
}

const getThumbGradient = (genre) => {
  const gradients = {
    'Pop Indonesia': 'linear-gradient(135deg, #ef4444, #f87171)',
    'Dangdut': 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    'K-Pop': 'linear-gradient(135deg, #ec4899, #f472b6)',
    'Barat': 'linear-gradient(135deg, #3b82f6, #60a5fa)',
  }
  return gradients[genre] || 'linear-gradient(135deg, #ef4444, #3b82f6)'
}

onMounted(() => {
  store.fetchSongs()
  store.fetchGenres()
  store.fetchQueue()
  store.fetchStats()
})
</script>

<style scoped>
.operator-layout {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
}

/* Sidebar */
.queue-sidebar {
  width: 300px;
  background: white;
  border-right: 1px solid #f3f4f6;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 20px rgba(0,0,0,0.05);
  z-index: 10;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid #f3f4f6;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.brand-dot {
  width: 10px;
  height: 10px;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  border-radius: 50%;
}

.header-brand h2 {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1f2937;
}

.queue-count {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 700;
}

/* Now Playing Card */
.now-playing-card {
  margin: 1rem;
  position: relative;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  background-size: 200% 200%;
  animation: gradient-shift 4s ease infinite;
  border-radius: 12px;
  padding: 1rem;
  color: white;
  overflow: hidden;
}

.np-glow {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: rgba(255,255,255,0.1);
  border-radius: 50%;
  filter: blur(20px);
}

.np-content { position: relative; }

.np-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.9;
}

.np-title {
  font-weight: 700;
  font-size: 1rem;
  margin: 0.25rem 0 0.75rem;
  line-height: 1.3;
}

.np-controls-mini {
  display: flex;
  gap: 0.5rem;
}

.ctrl-mini {
  width: 36px;
  height: 36px;
  background: rgba(255,255,255,0.2);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.ctrl-mini:hover { background: rgba(255,255,255,0.3); }

/* Queue List */
.queue-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 1rem;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 10px;
  margin-bottom: 0.5rem;
  transition: all 0.3s;
  animation: fadeInUp 0.3s ease-out backwards;
}

.queue-item:hover { background: #f3f4f6; }

.queue-item.is-next {
  background: linear-gradient(135deg, #fef2f2, #eff6ff);
  border: 1px solid #fecaca;
}

.queue-rank {
  width: 32px;
  height: 32px;
  background: #e5e7eb;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  color: #6b7280;
}

.rank-next {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.queue-info { flex: 1; min-width: 0; }

.queue-title {
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1f2937;
}

.queue-artist { font-size: 0.8rem; color: #9ca3af; }

.queue-actions { display: flex; gap: 0.25rem; }

.action-play {
  width: 28px;
  height: 28px;
  background: #10b981;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
  font-size: 0.7rem;
}

.action-remove {
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #ef4444;
  cursor: pointer;
}

.action-remove:hover { background: #fef2f2; }

.queue-empty {
  text-align: center;
  padding: 2rem;
  color: #9ca3af;
}

.empty-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 0.5rem;
}

.empty-hint { font-size: 0.8rem; margin-top: 0.25rem; }

/* Quick Stats */
.quick-stats {
  display: flex;
  border-top: 1px solid #f3f4f6;
  padding: 0.75rem 1rem;
  gap: 0.5rem;
}

.stat-item {
  flex: 1;
  text-align: center;
  background: #f9fafb;
  border-radius: 8px;
  padding: 0.5rem;
}

.stat-icon { font-size: 1rem; display: block; }

.stat-value { font-weight: 700; color: #1f2937; font-size: 0.9rem; }

.stat-label { font-size: 0.7rem; color: #9ca3af; }

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.top-bar {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  background: white;
  border-bottom: 1px solid #f3f4f6;
}

.search-box {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 1rem;
  font-size: 1rem;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  font-size: 0.95rem;
  transition: all 0.3s;
  background: #f9fafb;
}

.search-input:focus {
  outline: none;
  border-color: #ef4444;
  background: white;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.search-clear {
  position: absolute;
  right: 0.75rem;
  background: #e5e7eb;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  color: #6b7280;
}

.top-actions { display: flex; gap: 0.5rem; }

.action-btn {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.85rem;
  color: #4b5563;
  transition: all 0.2s;
}

.action-btn:hover { background: #e5e7eb; }

/* Genre Chips */
.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: white;
  border-bottom: 1px solid #f3f4f6;
}

.chip {
  padding: 0.4rem 0.875rem;
  background: #f3f4f6;
  border: 2px solid transparent;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  color: #4b5563;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.chip:hover { background: #e5e7eb; }

.chip.active {
  background: white;
  border-color: #ef4444;
  color: #ef4444;
  font-weight: 600;
}

.chip-count {
  background: #e5e7eb;
  padding: 0.1rem 0.4rem;
  border-radius: 10px;
  font-size: 0.7rem;
}

/* Quick Categories */
.quick-cats {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: white;
  border-bottom: 1px solid #f3f4f6;
  flex-wrap: wrap;
}

.cat-label {
  font-size: 0.8rem;
  color: #9ca3af;
  font-weight: 600;
  margin-right: 0.25rem;
}

.cat-pill {
  padding: 0.35rem 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #ef4444;
  transition: all 0.2s;
}

.cat-pill:hover {
  background: #fee2e2;
  border-color: #f87171;
}

/* Songs Grid */
.songs-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  align-content: start;
}

.song-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: white;
  padding: 0.75rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #f3f4f6;
  animation: fadeInUp 0.4s ease-out backwards;
}

.song-card:hover {
  box-shadow: 0 4px 15px rgba(0,0,0,0.08);
  border-color: #fecaca;
  transform: translateY(-1px);
}

.song-thumb {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex-shrink: 0;
}

.thumb-icon { font-size: 1.2rem; }

.song-id {
  position: absolute;
  bottom: -4px;
  right: -4px;
  background: rgba(0,0,0,0.5);
  color: white;
  font-size: 0.6rem;
  padding: 0.1rem 0.3rem;
  border-radius: 4px;
}

.song-details { flex: 1; min-width: 0; }

.song-title {
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1f2937;
}

.song-artist { font-size: 0.8rem; color: #6b7280; }

.song-meta {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
  flex-wrap: wrap;
}

.meta-genre {
  font-size: 0.65rem;
  padding: 0.1rem 0.4rem;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 4px;
  font-weight: 500;
}

.meta-plays { font-size: 0.65rem; color: #9ca3af; }

.meta-lang { font-size: 0.65rem; color: #6b7280; }

.add-btn {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.add-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

/* Empty State */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 3rem;
  color: #9ca3af;
}

.empty-state .empty-icon { font-size: 3rem; margin-bottom: 1rem; }

.empty-state h3 { color: #4b5563; margin-bottom: 0.5rem; }

/* AI Sidebar */
.ai-sidebar {
  width: 320px;
  background: #f8fafc;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  border-left: 1px solid #e5e7eb;
}

.mt-3 { margin-top: 0.75rem; }

/* Toast */
.add-toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: #10b981;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 30px;
  font-weight: 600;
  z-index: 1000;
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes gradient-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
</style>
