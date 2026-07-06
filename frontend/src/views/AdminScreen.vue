<template>
  <div class="admin-screen">
    <!-- Sidebar -->
    <aside class="admin-sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">⚙️</span>
        <span class="brand-text">Admin Panel</span>
      </div>
      <nav class="sidebar-nav">
        <button @click="activeTab = 'dashboard'" :class="{ active: activeTab === 'dashboard' }">
          📊 Dashboard
        </button>
        <button @click="activeTab = 'songs'" :class="{ active: activeTab === 'songs' }">
          🎵 Lagu
        </button>
        <button @click="activeTab = 'scan'" :class="{ active: activeTab === 'scan' }">
          📂 Scan Media
        </button>
        <button @click="activeTab = 'users'" :class="{ active: activeTab === 'users' }">
          👥 Users
        </button>
      </nav>
      <div class="sidebar-footer">
        <router-link to="/" class="back-link">← Kembali ke Home</router-link>
      </div>
    </aside>

    <!-- Main -->
    <main class="admin-main">
      <!-- Dashboard -->
      <div v-if="activeTab === 'dashboard'" class="dashboard">
        <h2>Dashboard</h2>
        <div class="stats-grid">
          <div class="stat-card red">
            <span class="stat-icon">🎵</span>
            <div class="stat-value">{{ store.stats.total_songs || 0 }}</div>
            <div class="stat-label">Total Lagu</div>
          </div>
          <div class="stat-card blue">
            <span class="stat-icon">▶️</span>
            <div class="stat-value">{{ store.stats.total_plays || 0 }}</div>
            <div class="stat-label">Total Play</div>
          </div>
          <div class="stat-card green">
            <span class="stat-icon">📋</span>
            <div class="stat-value">{{ store.stats.queue_today || 0 }}</div>
            <div class="stat-label">Queue Hari Ini</div>
          </div>
          <div class="stat-card purple">
            <span class="stat-icon">🟢</span>
            <div class="stat-value">{{ store.stats.active_connections || 0 }}</div>
            <div class="stat-label">Koneksi Aktif</div>
          </div>
        </div>
        <button @click="store.fetchStats()" class="refresh-btn">🔄 Refresh Stats</button>
      </div>

      <!-- Songs Management -->
      <div v-if="activeTab === 'songs'" class="songs-manage">
        <h2>Manajemen Lagu</h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Judul</th>
                <th>Artis</th>
                <th>Genre</th>
                <th>Play Count</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="song in store.songs.slice(0, 20)" :key="song.id">
                <td>{{ song.id }}</td>
                <td>{{ song.title }}</td>
                <td>{{ song.artist || '-' }}</td>
                <td><span class="genre-badge">{{ song.genre || '-' }}</span></td>
                <td>{{ song.play_count }}x</td>
                <td>
                  <button class="action-sm">Edit</button>
                  <button class="action-sm danger">Hapus</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Scan Media -->
      <div v-if="activeTab === 'scan'" class="scan-media">
        <h2>Scan Folder Media</h2>
        <div class="scan-card">
          <span class="scan-icon">📂</span>
          <h3>Scan Lagu Baru</h3>
          <p>Folder media: <code>/media/lagu/</code></p>
          <button @click="scanMedia" class="scan-btn" :disabled="isScanning">
            {{ isScanning ? '⏳ Scanning...' : '🔍 Mulai Scan' }}
          </button>
          <div v-if="scanResult" class="scan-result">
            <span>✅ {{ scanResult.new_songs }} lagu baru ditemukan!</span>
          </div>
        </div>
      </div>

      <!-- Users -->
      <div v-if="activeTab === 'users'" class="users-manage">
        <h2>Manajemen Pengguna</h2>
        <div class="user-cards">
          <div class="user-card">
            <div class="user-avatar red">A</div>
            <div class="user-info">
              <strong>admin</strong>
              <span>Administrator</span>
            </div>
            <span class="role-badge admin">Admin</span>
          </div>
          <div class="user-card">
            <div class="user-avatar blue">O</div>
            <div class="user-info">
              <strong>operator</strong>
              <span>Operator Karaoke</span>
            </div>
            <span class="role-badge operator">Operator</span>
          </div>
        </div>
        <button class="add-user-btn">+ Tambah Pengguna</button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import axios from 'axios'

const store = useKaraokeStore()
const activeTab = ref('dashboard')
const isScanning = ref(false)
const scanResult = ref(null)

const scanMedia = async () => {
  isScanning.value = true
  scanResult.value = null
  try {
    const response = await axios.post('/api/admin/songs/scan')
    scanResult.value = response.data
    store.fetchSongs()
    store.fetchStats()
  } catch (err) {
    alert('Scan gagal: ' + err.message)
  }
  isScanning.value = false
}

onMounted(() => {
  store.fetchSongs()
  store.fetchStats()
})
</script>

<style scoped>
.admin-screen {
  display: flex;
  height: 100vh;
  background: #f8fafc;
  color: #1f2937;
}

/* Sidebar */
.admin-sidebar {
  width: 240px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 2rem;
  color: #1f2937;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.sidebar-nav button {
  text-align: left;
  padding: 0.75rem 1rem;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #6b7280;
  transition: all 0.2s;
}

.sidebar-nav button:hover {
  background: #f3f4f6;
}

.sidebar-nav button.active {
  background: linear-gradient(135deg, #fef2f2, #eff6ff);
  color: #ef4444;
  font-weight: 600;
}

.back-link {
  color: #6b7280;
  text-decoration: none;
  font-size: 0.85rem;
}

/* Main */
.admin-main {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.admin-main h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: #1f2937;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  padding: 1.5rem;
  border-radius: 16px;
  color: white;
}

.stat-card.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.stat-card.blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.stat-card.green { background: linear-gradient(135deg, #10b981, #059669); }
.stat-card.purple { background: linear-gradient(135deg, #8b5cf6, #6d28d9); }

.stat-icon {
  font-size: 2rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 800;
  margin: 0.5rem 0;
}

.stat-label {
  font-size: 0.85rem;
  opacity: 0.9;
}

.refresh-btn {
  padding: 0.75rem 1.5rem;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
}

/* Table */
.table-container {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  background: #f9fafb;
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
}

.data-table td {
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
  border-bottom: 1px solid #f3f4f6;
}

.genre-badge {
  padding: 0.15rem 0.5rem;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 4px;
  font-size: 0.75rem;
}

.action-sm {
  padding: 0.25rem 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.75rem;
  margin-right: 0.25rem;
}

.action-sm.danger {
  color: #ef4444;
  border-color: #fecaca;
}

/* Scan Card */
.scan-card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.scan-icon {
  font-size: 3rem;
}

.scan-card h3 {
  margin: 1rem 0 0.5rem;
}

.scan-card code {
  background: #f3f4f6;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
}

.scan-btn {
  display: block;
  margin: 1.5rem auto 0;
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
}

.scan-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.scan-result {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #ecfdf5;
  color: #059669;
  border-radius: 8px;
}

/* User Cards */
.user-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: white;
  padding: 1rem;
  border-radius: 12px;
}

.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: white;
}

.user-avatar.red { background: #ef4444; }
.user-avatar.blue { background: #3b82f6; }

.user-info {
  flex: 1;
}

.user-info strong {
  display: block;
}

.user-info span {
  font-size: 0.8rem;
  color: #6b7280;
}

.role-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}

.role-badge.admin {
  background: #fef2f2;
  color: #ef4444;
}

.role-badge.operator {
  background: #eff6ff;
  color: #3b82f6;
}

.add-user-btn {
  padding: 0.75rem 1.5rem;
  background: white;
  border: 2px dashed #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  color: #6b7280;
  font-weight: 500;
}
</style>
