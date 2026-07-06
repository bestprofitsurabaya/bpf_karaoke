<template>
  <div class="admin-screen">
    <h1>Admin Panel</h1>
    <div class="stats-grid">
      <div class="stat-card">
        <h3>Total Lagu</h3>
        <div class="stat-value">{{ store.stats.total_songs || 0 }}</div>
      </div>
      <div class="stat-card">
        <h3>Total Play</h3>
        <div class="stat-value">{{ store.stats.total_plays || 0 }}</div>
      </div>
      <div class="stat-card">
        <h3>Queue Hari Ini</h3>
        <div class="stat-value">{{ store.stats.queue_today || 0 }}</div>
      </div>
      <div class="stat-card">
        <h3>Koneksi Aktif</h3>
        <div class="stat-value">{{ store.stats.active_connections || 0 }}</div>
      </div>
    </div>
    <button @click="scanMedia" class="scan-btn">Scan Media Folder</button>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import axios from 'axios'

const store = useKaraokeStore()

const scanMedia = async () => {
  try {
    await axios.post('/api/admin/songs/scan')
    alert('Scan completed!')
    store.fetchSongs()
    store.fetchStats()
  } catch (err) {
    alert('Scan failed: ' + err.message)
  }
}

onMounted(() => {
  store.fetchStats()
})
</script>

<style scoped>
.admin-screen {
  padding: 2rem;
  color: white;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin: 2rem 0;
}

.stat-card {
  background: rgba(255, 255, 255, 0.1);
  padding: 1.5rem;
  border-radius: 1rem;
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  margin-top: 0.5rem;
}

.scan-btn {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 0.5rem;
  font-size: 1rem;
  cursor: pointer;
}
</style>
