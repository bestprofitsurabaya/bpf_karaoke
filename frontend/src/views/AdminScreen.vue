<template>
  <div class="admin-screen">
    <aside class="admin-sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">⚙️</span>
        <span class="brand-text">Admin Panel</span>
      </div>
      <nav class="sidebar-nav">
        <button @click="activeTab = 'dashboard'" :class="{ active: activeTab === 'dashboard' }">📊 Dashboard</button>
        <button @click="activeTab = 'songs'" :class="{ active: activeTab === 'songs' }">🎵 Manajemen Lagu</button>
        <button @click="activeTab = 'room'" :class="{ active: activeTab === 'room' }">🏢 Konfigurasi Ruangan</button>
        <button @click="activeTab = 'scan'" :class="{ active: activeTab === 'scan' }">📂 Scan Media</button>
      </nav>
      <div class="sidebar-footer">
        <router-link to="/" class="back-link">← Kembali ke Home</router-link>
      </div>
    </aside>

    <main class="admin-main">
      <div v-if="activeTab === 'dashboard'" class="dashboard">
        <h2>Dashboard Utama</h2>
        <div class="stats-grid">
          <div class="stat-card red">
            <span class="stat-icon">🎵</span>
            <div class="stat-value">{{ store.stats.total_songs || 0 }}</div>
            <div class="stat-label">Total Judul Lagu</div>
          </div>
          <div class="stat-card blue">
            <span class="stat-icon">🏢</span>
            <div class="stat-value" style="font-size: 1.1rem; padding: 0.7rem 0;">{{ store.roomId }}</div>
            <div class="stat-label">Ruangan Aktif</div>
          </div>
          <div class="stat-card green">
            <span class="stat-icon">📋</span>
            <div class="stat-value">{{ store.stats.queue_today || 0 }}</div>
            <div class="stat-label">Antrian Hari Ini</div>
          </div>
        </div>
        <button @click="store.fetchStats()" class="refresh-btn">🔄 Perbarui Statistik</button>
      </div>

      <div v-if="activeTab === 'songs'" class="songs-manage">
        <h2>Manajemen Konten Lagu</h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Judul</th>
                <th>Artis</th>
                <th>Genre</th>
                <th>Aksi Pembaruan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="song in store.songs" :key="song.id">
                <td>{{ song.id }}</td>
                <td>
                  <input v-model="song.title" class="table-input" />
                </td>
                <td>
                  <input v-model="song.artist" class="table-input" />
                </td>
                <td>
                  <input v-model="song.genre" class="table-input" />
                </td>
                <td>
                  <button @click="saveSong(song)" class="action-sm success">Simpan</button>
                  <button @click="deleteSong(song.id)" class="action-sm danger">Hapus</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="activeTab === 'room'" class="room-manage">
        <h2>Konfigurasi Ruangan Dinamis</h2>
        <div class="scan-card">
          <h3>Set Nama Ruangan Kerja</h3>
          <p>Ubah nama ruangan untuk sinkronisasi QR-Code dan HP pelanggan</p>
          <input v-model="localRoomName" class="input-field" style="margin: 1rem 0; max-width: 400px;" placeholder="Contoh: KARAOKE BPF SBY" />
          <button @click="updateRoomName" class="scan-btn">💾 Terapkan Ruangan</button>
        </div>
      </div>

      <div v-if="activeTab === 'scan'" class="scan-media">
        <h2>Sinkronisasi Folder Media</h2>
        <div class="scan-card">
          <span class="scan-icon">📂</span>
          <h3>Scan Berkas Lokal Otomatis</h3>
          <p>Lokasi Pustaka: <code>/media/lagu/</code></p>
          <button @click="scanMedia" class="scan-btn" :disabled="isScanning">
            {{ isScanning ? '⏳ Memindai Berkas...' : '🔍 Jalankan Pindai Konten' }}
          </button>
          <div v-if="scanResult" class="scan-result">
            <span>✅ Berhasil menambahkan {{ scanResult.new_songs }} berkas baru ke Pustaka.</span>
          </div>
        </div>
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
const localRoomName = ref(store.roomId)

const scanMedia = async () => {
  isScanning.value = true
  scanResult.value = null
  try {
    const response = await axios.post('/api/admin/songs/scan')
    scanResult.value = response.data
    store.fetchSongs()
    store.fetchStats()
  } catch (err) {
    alert('Gagal memindai: ' + err.message)
  }
  isScanning.value = false
}

const saveSong = async (song) => {
  try {
    await axios.put(`/api/songs/${song.id}`, {
      title: song.title,
      artist: song.artist,
      genre: song.genre
    })
    alert('Data lagu #' + song.id + ' berhasil disimpan!')
  } catch (err) {
    alert('Gagal menyimpan perubahan data')
  }
}

const deleteSong = async (id) => {
  if (!confirm('Apakah Anda yakin ingin menonaktifkan lagu ini dari daftar?')) return
  try {
    await axios.delete(`/api/songs/${id}`)
    store.fetchSongs()
  } catch (err) {
    alert('Gagal menghapus berkas data')
  }
}

const updateRoomName = () => {
  if (!localRoomName.value.trim()) return
  store.setRoomId(localRoomName.value.trim())
  alert('Nama ruangan diubah menjadi: ' + store.roomId)
}

onMounted(() => {
  store.fetchSongs()
  store.fetchStats()
})
</script>

<style scoped>
.admin-screen { display: flex; height: 100vh; background: #f8fafc; color: #1f2937; }
.admin-sidebar { width: 260px; background: white; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; padding: 1.5rem; }
.sidebar-brand { display: flex; align-items: center; gap: 0.5rem; font-size: 1.1rem; font-weight: 700; margin-bottom: 2rem; }
.sidebar-nav { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.sidebar-nav button { text-align: left; padding: 0.75rem 1rem; background: transparent; border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: #6b7280; transition: all 0.2s; }
.sidebar-nav button:hover { background: #f3f4f6; }
.sidebar-nav button.active { background: linear-gradient(135deg, #fef2f2, #eff6ff); color: #ef4444; font-weight: 600; }
.back-link { color: #6b7280; text-decoration: none; font-size: 0.85rem; }
.admin-main { flex: 1; overflow-y: auto; padding: 2rem; }
.admin-main h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { padding: 1.5rem; border-radius: 16px; color: white; }
.stat-card.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.stat-card.blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.stat-card.green { background: linear-gradient(135deg, #10b981, #059669); }
.stat-value { font-size: 2rem; font-weight: 800; margin: 0.5rem 0; }
.stat-label { font-size: 0.85rem; opacity: 0.9; }
.refresh-btn { padding: 0.75rem 1.5rem; background: white; border: 2px solid #e5e7eb; border-radius: 10px; cursor: pointer; }
.table-container { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: #f9fafb; padding: 0.75rem 1rem; text-align: left; font-size: 0.8rem; text-transform: uppercase; color: #6b7280; }
.data-table td { padding: 0.75rem 1rem; font-size: 0.9rem; border-bottom: 1px solid #f3f4f6; }
.table-input { width: 100%; padding: 0.35rem; border: 1px solid #d1d5db; border-radius: 4px; }
.action-sm { padding: 0.25rem 0.6rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.75rem; margin-right: 0.25rem; color: white; }
.action-sm.success { background: #10b981; }
.action-sm.danger { background: #ef4444; }
.scan-card { background: white; border-radius: 16px; padding: 2rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.scan-icon { font-size: 3rem; }
.scan-btn { display: block; margin: 1.5rem auto 0; padding: 0.75rem 2rem; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; }
.scan-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.scan-result { margin-top: 1rem; padding: 0.75rem; background: #ecfdf5; color: #059669; border-radius: 8px; }
.input-field { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 6px; }
</style>
