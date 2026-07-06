<template>
  <div class="remote-screen">
    <!-- Header -->
    <div class="remote-header">
      <h1>🎤 Karaoke Remote</h1>
      <p>Room: {{ store.roomId }}</p>
    </div>

    <!-- Search -->
    <div class="search-container">
      <input v-model="store.searchQuery" type="text"
             placeholder="Cari lagu atau artis..."
             @input="debouncedSearch">
    </div>

    <!-- Now Playing -->
    <div class="now-playing-mini" v-if="store.currentSong">
      <div class="np-status">🎵 Sedang Diputar</div>
      <div class="np-title">{{ store.currentSong.song_title || 'Playing...' }}</div>
      <div class="np-controls">
        <button @click="store.isPlaying ? store.pauseSong() : store.resumeSong()">
          {{ store.isPlaying ? '⏸ Pause' : '▶ Play' }}
        </button>
        <button @click="store.skipSong(store.currentSong?.queue_id)">⏭ Skip</button>
      </div>
    </div>

    <!-- Songs List -->
    <div class="songs-list">
      <div v-for="song in store.filteredSongs" :key="song.id"
           class="song-item" @click="addToQueue(song.id)">
        <div class="song-main">
          <div class="song-title">{{ song.title }}</div>
          <div class="song-artist">{{ song.artist || 'Unknown' }}</div>
        </div>
        <button class="add-btn" @click.stop="addToQueue(song.id)">+</button>
      </div>
    </div>

    <!-- My Queue -->
    <div class="my-queue" v-if="store.waitingQueue.length > 0">
      <h3>Antrian Saya</h3>
      <div v-for="(item, index) in store.waitingQueue" :key="item.id" class="queue-item">
        <span>{{ index + 1 }}. {{ item.song?.title }}</span>
        <button @click="store.removeFromQueue(item.id)" class="remove-btn">✕</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'

const store = useKaraokeStore()

let debounceTimer
const debouncedSearch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    store.fetchSongs()
  }, 300)
}

const addToQueue = async (songId) => {
  await store.addToQueue(songId)
}

onMounted(() => {
  store.fetchSongs()
  store.fetchQueue()
})
</script>

<style scoped>
.remote-screen {
  min-height: 100vh;
  background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
  color: white;
  padding: 1rem;
  max-width: 500px;
  margin: 0 auto;
}

.remote-header {
  text-align: center;
  padding: 1rem 0;
}

.remote-header h1 {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
}

.search-container input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
  color: white;
  font-size: 1rem;
  margin-bottom: 1rem;
}

.now-playing-mini {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
  border-radius: 0.75rem;
  margin-bottom: 1rem;
}

.np-status {
  font-size: 0.75rem;
  opacity: 0.8;
  text-transform: uppercase;
}

.np-title {
  font-weight: 600;
  font-size: 1.1rem;
  margin: 0.25rem 0 0.75rem;
}

.np-controls {
  display: flex;
  gap: 0.5rem;
}

.np-controls button {
  flex: 1;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 0.5rem;
  color: white;
  font-size: 0.9rem;
  cursor: pointer;
}

.songs-list {
  max-height: 50vh;
  overflow-y: auto;
}

.song-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
}

.song-main {
  flex: 1;
}

.song-title {
  font-weight: 500;
}

.song-artist {
  font-size: 0.8rem;
  opacity: 0.6;
}

.add-btn {
  width: 35px;
  height: 35px;
  background: #667eea;
  border: none;
  border-radius: 50%;
  color: white;
  font-size: 1.2rem;
  cursor: pointer;
}

.my-queue {
  margin-top: 1rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0.75rem;
  padding: 1rem;
}

.my-queue h3 {
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
  opacity: 0.7;
}

.queue-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.remove-btn {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
}
</style>
