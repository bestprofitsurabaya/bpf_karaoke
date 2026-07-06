<template>
  <div class="operator-layout">
    <!-- Sidebar: Daftar Antrian -->
    <aside class="queue-sidebar">
      <div class="queue-header">
        <h2>🎵 Antrian</h2>
        <span class="queue-count">{{ store.waitingQueue.length }}</span>
      </div>
      <div class="queue-list">
        <div v-for="(item, index) in store.waitingQueue" :key="item.id"
             class="queue-item" :class="{ 'is-next': index === 0 }">
          <div class="queue-number">{{ index + 1 }}</div>
          <div class="queue-info">
            <div class="queue-title">{{ item.song?.title }}</div>
            <div class="queue-artist">{{ item.song?.artist }}</div>
          </div>
          <button class="queue-remove" @click="store.removeFromQueue(item.id)">✕</button>
        </div>
        <div v-if="store.waitingQueue.length === 0" class="queue-empty">
          Antrian kosong
        </div>
      </div>
      <div class="now-playing" v-if="store.currentSong">
        <div class="np-label">Sedang Diputar</div>
        <div class="np-title">{{ store.currentSong.song_title || 'Loading...' }}</div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Search & Filter -->
      <div class="search-bar">
        <input v-model="store.searchQuery" type="text"
               placeholder="🔍 Cari lagu atau artis..."
               class="search-input"
               @input="debouncedSearch">
        <select v-model="store.selectedGenre" @change="store.fetchSongs()" class="filter-select">
          <option value="">Semua Genre</option>
          <option v-for="g in store.genres" :key="g.genre" :value="g.genre">
            {{ g.genre }} ({{ g.count }})
          </option>
        </select>
      </div>

      <!-- Quick Categories -->
      <div class="categories">
        <button @click="quickFilter('')" class="cat-btn" :class="{ active: !store.selectedGenre }">
          🔥 Semua
        </button>
        <button @click="quickFilter('Pop Indonesia')" class="cat-btn">
          🇮🇩 Pop Indo
        </button>
        <button @click="quickFilter('Dangdut')" class="cat-btn">
          🎶 Dangdut
        </button>
        <button @click="quickFilter('Barat')" class="cat-btn">
          🌍 Barat
        </button>
        <button @click="quickFilter('K-Pop')" class="cat-btn">
          🇰🇷 K-Pop
        </button>
      </div>

      <!-- Songs Grid -->
      <div class="songs-grid">
        <div v-for="song in store.filteredSongs" :key="song.id"
             class="song-card" @click="addSong(song)">
          <div class="song-number">{{ song.id }}</div>
          <div class="song-info">
            <div class="song-title">{{ song.title }}</div>
            <div class="song-artist">{{ song.artist || 'Unknown Artist' }}</div>
          </div>
          <div class="song-meta">
            <span class="song-genre">{{ song.genre || '-' }}</span>
            <span class="song-plays">▶ {{ song.play_count }}</span>
          </div>
          <button class="song-add" @click.stop="addSong(song)">+</button>
        </div>
      </div>

      <!-- Now Playing Bar -->
      <div class="now-playing-bar" v-if="store.currentSong">
        <div class="np-info">
          <span class="np-icon">🎤</span>
          <div>
            <div class="np-title-small">{{ store.currentSong.song_title || 'Playing...' }}</div>
          </div>
        </div>
        <div class="np-controls">
          <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()" class="ctrl-btn">
            {{ store.isPlaying ? '⏸' : '▶' }}
          </button>
          <button @click="store.skipSong(store.currentSong.queue_id)" class="ctrl-btn">⏭</button>
        </div>
        <div class="volume-control">
          <span>🔊</span>
          <input type="range" min="0" max="100" :value="store.currentVolume"
                 @input="store.setVolume($event.target.value)" class="volume-slider">
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import { debounce } from '@/utils/helpers'

const store = useKaraokeStore()

let debounceTimer
const debouncedSearch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    store.fetchSongs()
  }, 300)
}

const quickFilter = (genre) => {
  store.selectedGenre = genre || null
  store.fetchSongs()
}

const addSong = async (song) => {
  const success = await store.addToQueue(song.id)
  if (success && store.waitingQueue.length === 1) {
    // Auto play if this is the first song
    store.playSong(song.id, store.queue.find(q => q.song_id === song.id && q.status === 'waiting')?.id)
  }
}

onMounted(() => {
  store.fetchSongs()
  store.fetchGenres()
  store.fetchQueue()
})
</script>

<style scoped>
.operator-layout {
  display: flex;
  height: 100vh;
}

.queue-sidebar {
  width: 320px;
  background: rgba(0, 0, 0, 0.3);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  padding: 1rem;
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.queue-header h2 {
  font-size: 1.2rem;
}

.queue-count {
  background: #667eea;
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.queue-list {
  flex: 1;
  overflow-y: auto;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  transition: all 0.2s;
}

.queue-item.is-next {
  border: 1px solid #667eea;
  background: rgba(102, 126, 234, 0.1);
}

.queue-number {
  width: 30px;
  height: 30px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.85rem;
}

.queue-info {
  flex: 1;
  min-width: 0;
}

.queue-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-artist {
  font-size: 0.8rem;
  opacity: 0.6;
}

.queue-remove {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 1rem;
}

.queue-empty {
  text-align: center;
  padding: 2rem;
  opacity: 0.5;
}

.now-playing {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
  border-radius: 0.5rem;
  margin-top: 1rem;
}

.np-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.8;
}

.np-title {
  font-weight: 600;
  margin-top: 0.25rem;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1rem;
  overflow: hidden;
}

.search-bar {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.5rem;
  color: white;
  font-size: 1rem;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.filter-select {
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.5rem;
  color: white;
}

.categories {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.cat-btn {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 2rem;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.85rem;
}

.cat-btn:hover, .cat-btn.active {
  background: #667eea;
  border-color: #667eea;
}

.songs-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 0.5rem;
  align-content: start;
  padding-bottom: 80px;
}

.song-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.song-card:hover {
  background: rgba(255, 255, 255, 0.1);
}

.song-number {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-artist {
  font-size: 0.8rem;
  opacity: 0.6;
}

.song-meta {
  display: flex;
  gap: 0.5rem;
  font-size: 0.75rem;
  opacity: 0.5;
}

.song-add {
  width: 35px;
  height: 35px;
  background: #667eea;
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.now-playing-bar {
  position: fixed;
  bottom: 0;
  left: 320px;
  right: 0;
  height: 70px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  gap: 1.5rem;
}

.np-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.np-icon {
  font-size: 1.5rem;
}

.np-title-small {
  font-weight: 600;
}

.np-controls {
  display: flex;
  gap: 0.5rem;
}

.ctrl-btn {
  width: 45px;
  height: 45px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.volume-slider {
  width: 100px;
  accent-color: #667eea;
}
</style>
