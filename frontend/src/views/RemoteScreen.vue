<template>
  <div class="remote-screen">
    <!-- Header -->
    <div class="remote-header">
      <div class="header-top">
        <span class="header-emoji">🎤</span>
        <div>
          <h1>BPF Karaoke</h1>
          <p class="room-tag">Room: {{ store.roomId }}</p>
        </div>
      </div>
      <div class="connection-status" :class="{ connected: store.isConnected }">
        <span class="status-dot"></span>
        {{ store.isConnected ? 'Connected' : 'Connecting...' }}
      </div>
    </div>

    <!-- Search -->
    <div class="search-section">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input v-model="store.searchQuery" type="search"
               placeholder="Cari lagu favoritmu..."
               @input="debouncedSearch">
        <button v-if="store.searchQuery" class="clear-btn" @click="clearSearch">✕</button>
      </div>
    </div>

    <!-- Now Playing Card -->
    <div class="now-playing-card" v-if="store.currentSong">
      <div class="np-glow"></div>
      <div class="np-content">
        <span class="np-badge">🎵 NOW PLAYING</span>
        <div class="np-title">{{ store.currentSong.song_title || 'Unknown' }}</div>
        <div class="np-artist">{{ store.currentSong.song_artist || 'Unknown Artist' }}</div>
        <div class="np-actions">
          <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()" class="np-btn play-btn">
            {{ store.isPlaying ? '⏸ Pause' : '▶ Play' }}
          </button>
          <button @click="store.skipSong(store.currentSong?.queue_id)" class="np-btn skip-btn">
            ⏭ Skip
          </button>
        </div>
      </div>
    </div>

    <!-- Quick Categories -->
    <div class="quick-cats">
      <button @click="quickFilter('Pop Indonesia')" class="cat-chip">🇮🇩 Pop</button>
      <button @click="quickFilter('Dangdut')" class="cat-chip">🎶 Dangdut</button>
      <button @click="quickFilter('Barat')" class="cat-chip">🌍 Barat</button>
      <button @click="quickFilter('K-Pop')" class="cat-chip">🇰🇷 K-Pop</button>
    </div>

    <!-- Songs List -->
    <div class="songs-section">
      <h3 class="section-label">Daftar Lagu</h3>
      <div class="songs-list">
        <div v-for="song in store.filteredSongs" :key="song.id"
             class="song-item" @click="addToQueue(song)">
          <div class="song-thumb" :style="{ background: getThumbColor(song.genre) }">
            🎵
          </div>
          <div class="song-info">
            <div class="song-title">{{ song.title }}</div>
            <div class="song-artist">{{ song.artist || 'Unknown' }}</div>
            <div class="song-meta">
              <span v-if="song.genre" class="meta-tag">{{ song.genre }}</span>
              <span class="meta-plays">▶ {{ song.play_count }}x</span>
            </div>
          </div>
          <button class="add-btn" @click.stop="addToQueue(song)">
            <span>+</span>
          </button>
        </div>
      </div>
    </div>

    <!-- My Queue -->
    <div class="my-queue" v-if="store.waitingQueue.length > 0">
      <h3 class="section-label">
        Antrian Saya
        <span class="queue-count">{{ store.waitingQueue.length }}</span>
      </h3>
      <div class="queue-list">
        <div v-for="(item, index) in store.waitingQueue" :key="item.id" class="queue-item">
          <span class="queue-num">{{ index + 1 }}</span>
          <div class="queue-info">
            <div class="queue-title">{{ item.song?.title }}</div>
            <div class="queue-artist">{{ item.song?.artist }}</div>
          </div>
          <button @click="store.removeFromQueue(item.id)" class="remove-btn">✕</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div class="success-toast" v-if="showToast">
      ✅ Ditambahkan ke antrian!
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'

const store = useKaraokeStore()
const showToast = ref(false)

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

const quickFilter = (genre) => {
  store.selectedGenre = store.selectedGenre === genre ? null : genre
  store.fetchSongs()
}

const addToQueue = async (song) => {
  const success = await store.addToQueue(song.id)
  if (success) {
    showToast.value = true
    setTimeout(() => { showToast.value = false }, 2000)
  }
}

const getThumbColor = (genre) => {
  const colors = {
    'Pop Indonesia': 'linear-gradient(135deg, #ef4444, #f87171)',
    'Dangdut': 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    'K-Pop': 'linear-gradient(135deg, #ec4899, #f472b6)',
    'Barat': 'linear-gradient(135deg, #3b82f6, #60a5fa)'
  }
  return colors[genre] || 'linear-gradient(135deg, #ef4444, #3b82f6)'
}

onMounted(() => {
  store.fetchSongs()
  store.fetchQueue()
  store.connectSocket()
})
</script>

<style scoped>
.remote-screen {
  min-height: 100vh;
  background: linear-gradient(180deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
  padding: 1rem;
  max-width: 480px;
  margin: 0 auto;
  font-family: 'Inter', sans-serif;
}

/* Header */
.remote-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0 1rem;
}

.header-top {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-emoji {
  font-size: 2rem;
  background: white;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.remote-header h1 {
  font-size: 1.2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.room-tag {
  font-size: 0.75rem;
  color: #9ca3af;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: #9ca3af;
  background: white;
  padding: 0.4rem 0.75rem;
  border-radius: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.status-dot {
  width: 7px;
  height: 7px;
  background: #d1d5db;
  border-radius: 50%;
}

.connected .status-dot {
  background: #10b981;
  animation: pulse-glow 2s infinite;
}

/* Search */
.search-section {
  margin-bottom: 1rem;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 1rem;
  z-index: 1;
}

.search-box input {
  width: 100%;
  padding: 0.875rem 1rem 0.875rem 2.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 14px;
  font-size: 0.95rem;
  background: white;
  transition: all 0.3s;
}

.search-box input:focus {
  outline: none;
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.clear-btn {
  position: absolute;
  right: 0.75rem;
  background: #e5e7eb;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
}

/* Now Playing Card */
.now-playing-card {
  position: relative;
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  background-size: 200% 200%;
  animation: gradient-shift 4s ease infinite;
  border-radius: 16px;
  padding: 1.25rem;
  margin-bottom: 1rem;
  color: white;
  overflow: hidden;
}

.np-glow {
  position: absolute;
  top: -30%;
  right: -30%;
  width: 100px;
  height: 100px;
  background: rgba(255,255,255,0.2);
  border-radius: 50%;
  filter: blur(30px);
}

.np-content {
  position: relative;
}

.np-badge {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.9;
}

.np-title {
  font-size: 1.2rem;
  font-weight: 700;
  margin: 0.25rem 0;
}

.np-artist {
  font-size: 0.9rem;
  opacity: 0.8;
  margin-bottom: 0.75rem;
}

.np-actions {
  display: flex;
  gap: 0.5rem;
}

.np-btn {
  flex: 1;
  padding: 0.6rem;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
}

.play-btn {
  background: rgba(255,255,255,0.2);
  color: white;
}

.skip-btn {
  background: rgba(0,0,0,0.2);
  color: white;
}

/* Quick Categories */
.quick-cats {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.cat-chip {
  padding: 0.4rem 0.75rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #4b5563;
}

.cat-chip:active {
  background: #fef2f2;
  border-color: #ef4444;
  color: #ef4444;
}

/* Songs Section */
.section-label {
  font-size: 0.9rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.songs-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.song-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: white;
  padding: 0.75rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #f3f4f6;
}

.song-item:active {
  transform: scale(0.98);
  background: #f9fafb;
}

.song-thumb {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1.1rem;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-title {
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1f2937;
}

.song-artist {
  font-size: 0.8rem;
  color: #6b7280;
}

.song-meta {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.15rem;
}

.meta-tag {
  font-size: 0.6rem;
  padding: 0.1rem 0.35rem;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 4px;
}

.meta-plays {
  font-size: 0.6rem;
  color: #9ca3af;
}

.add-btn {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  flex-shrink: 0;
}

/* My Queue */
.my-queue {
  margin-top: 1.5rem;
  background: white;
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.queue-count {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid #f3f4f6;
}

.queue-item:last-child {
  border-bottom: none;
}

.queue-num {
  width: 26px;
  height: 26px;
  background: #f3f4f6;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: #6b7280;
}

.queue-info {
  flex: 1;
  min-width: 0;
}

.queue-title {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #1f2937;
}

.queue-artist {
  font-size: 0.75rem;
  color: #9ca3af;
}

.remove-btn {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.25rem;
}

/* Toast */
.success-toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: #10b981;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 30px;
  font-weight: 600;
  z-index: 100;
  animation: fadeInUp 0.3s ease-out;
}
</style>
