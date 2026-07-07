<template>
  <div class="admin-screen">
    <!-- Sidebar -->
    <aside class="admin-sidebar">
      <div class="sidebar-brand">
        <img src="/icons/icon-512x512.png" alt="BPF" class="brand-logo" />
        <span class="brand-text">Admin Panel</span>
      </div>
      <nav class="sidebar-nav">
        <button @click="activeTab = 'dashboard'" :class="{ active: activeTab === 'dashboard' }">
          📊 Dashboard
        </button>
        <button @click="activeTab = 'rooms'" :class="{ active: activeTab === 'rooms' }">
          🏠 Room Management
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
      <!-- ============ DASHBOARD ============ -->
      <div v-if="activeTab === 'dashboard'" class="tab-content">
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
            <span class="stat-icon">🏠</span>
            <div class="stat-value">{{ rooms.length }}</div>
            <div class="stat-label">Room Aktif</div>
          </div>
          <div class="stat-card purple">
            <span class="stat-icon">🟢</span>
            <div class="stat-value">{{ store.stats.active_connections || 0 }}</div>
            <div class="stat-label">Koneksi Aktif</div>
          </div>
        </div>
        <button @click="refreshAll" class="refresh-btn">🔄 Refresh All</button>
      </div>

      <!-- ============ ROOM MANAGEMENT ============ -->
      <div v-if="activeTab === 'rooms'" class="tab-content">
        <div class="tab-header">
          <h2>🏠 Room Management</h2>
          <button @click="showAddRoom = true" class="add-btn-primary">+ Tambah Room</button>
        </div>

        <!-- Add Room Form -->
        <div v-if="showAddRoom" class="form-card">
          <h3>Tambah Room Baru</h3>
          <input v-model="newRoom.name" placeholder="Nama Room (contoh: Room VIP)" class="input-field" />
          <input v-model="newRoom.description" placeholder="Deskripsi (opsional)" class="input-field" />
          <div class="form-actions">
            <button @click="createRoom" class="btn-save">💾 Simpan</button>
            <button @click="showAddRoom = false; resetForm()" class="btn-cancel">Batal</button>
          </div>
        </div>

        <!-- Room List -->
        <div class="room-grid">
          <div v-for="room in rooms" :key="room.id" class="room-card" :class="{ inactive: !room.is_active }">
            <div class="room-card-header">
              <span class="room-icon">🏠</span>
              <div class="room-status" :class="{ active: room.is_active }"></div>
            </div>
            <h3 class="room-name">{{ room.name }}</h3>
            <p class="room-desc">{{ room.description || 'Tidak ada deskripsi' }}</p>
            <p class="room-date">Dibuat: {{ formatDate(room.created_at) }}</p>
            <div class="room-actions">
              <button @click="editRoom(room)" class="btn-edit">✏️ Edit</button>
              <button @click="deleteRoom(room.id)" class="btn-delete" v-if="room.is_active">🗑️ Hapus</button>
            </div>
          </div>
        </div>

        <!-- Edit Room Modal -->
        <div v-if="editingRoom" class="modal-overlay" @click.self="editingRoom = null">
          <div class="modal-card">
            <h3>Edit Room</h3>
            <input v-model="editingRoom.name" placeholder="Nama Room" class="input-field" />
            <input v-model="editingRoom.description" placeholder="Deskripsi" class="input-field" />
            <div class="form-actions">
              <button @click="updateRoom" class="btn-save">💾 Update</button>
              <button @click="editingRoom = null" class="btn-cancel">Batal</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ============ SONGS ============ -->
      <div v-if="activeTab === 'songs'" class="tab-content">
        <h2>Manajemen Lagu</h2>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr><th>ID</th><th>Judul</th><th>Artis</th><th>Genre</th><th>Play</th><th>Aksi</th></tr>
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

      <!-- ============ SCAN ============ -->
      <div v-if="activeTab === 'scan'" class="tab-content">
        <h2>Scan Folder Media</h2>
        <div class="scan-card">
          <span class="scan-icon">📂</span>
          <h3>Scan Lagu Baru</h3>
          <p>Folder: <code>/media/lagu/</code></p>
          <button @click="scanMedia" class="scan-btn" :disabled="isScanning">
            {{ isScanning ? '⏳ Scanning...' : '🔍 Mulai Scan' }}
          </button>
          <div v-if="scanResult" class="scan-result">✅ {{ scanResult.new_songs }} lagu baru!</div>
        </div>
      </div>

      <!-- ============ USERS ============ -->
      <div v-if="activeTab === 'users'" class="tab-content">
        <h2>Manajemen Pengguna</h2>
        <div class="user-cards">
          <div class="user-card"><div class="user-avatar red">A</div><div class="user-info"><strong>admin</strong><span>Administrator</span></div><span class="role-badge admin">Admin</span></div>
          <div class="user-card"><div class="user-avatar blue">O</div><div class="user-info"><strong>operator</strong><span>Operator</span></div><span class="role-badge operator">Operator</span></div>
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
const rooms = ref([])
const showAddRoom = ref(false)
const editingRoom = ref(null)
const isScanning = ref(false)
const scanResult = ref(null)

const newRoom = ref({ name: '', description: '' })

// Fetch rooms
const fetchRooms = async () => {
  try {
    const response = await axios.get('/api/rooms')
    rooms.value = response.data
  } catch (err) {
    console.error('Failed to fetch rooms:', err)
  }
}

// Create room
const createRoom = async () => {
  if (!newRoom.value.name.trim()) return
  try {
    await axios.post('/api/rooms', newRoom.value)
    showAddRoom.value = false
    resetForm()
    fetchRooms()
  } catch (err) {
    alert('Gagal membuat room: ' + (err.response?.data?.detail || err.message))
  }
}

// Edit room
const editRoom = (room) => {
  editingRoom.value = { ...room }
}

// Update room
const updateRoom = async () => {
  if (!editingRoom.value) return
  try {
    await axios.put(`/api/rooms/${editingRoom.value.id}`, {
      name: editingRoom.value.name,
      description: editingRoom.value.description
    })
    editingRoom.value = null
    fetchRooms()
  } catch (err) {
    alert('Gagal update room: ' + (err.response?.data?.detail || err.message))
  }
}

// Delete room
const deleteRoom = async (roomId) => {
  if (!confirm('Yakin hapus room ini?')) return
  try {
    await axios.delete(`/api/rooms/${roomId}`)
    fetchRooms()
  } catch (err) {
    alert('Gagal hapus room')
  }
}

const resetForm = () => {
  newRoom.value = { name: '', description: '' }
}

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

const refreshAll = () => {
  store.fetchStats()
  store.fetchSongs()
  fetchRooms()
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' })
}

onMounted(() => {
  store.fetchSongs()
  store.fetchStats()
  fetchRooms()
})
</script>

<style scoped>
.admin-screen { display: flex; height: 100vh; background: #f8fafc; color: #1f2937; }

/* Sidebar */
.admin-sidebar {
  width: 240px; background: white; border-right: 1px solid #e5e7eb;
  display: flex; flex-direction: column; padding: 1.5rem;
}
.sidebar-brand { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 2rem; }
.brand-logo { width: 32px; height: 32px; border-radius: 6px; object-fit: contain; }
.brand-text { font-size: 1.1rem; font-weight: 700; }
.sidebar-nav { display: flex; flex-direction: column; gap: 0.25rem; flex: 1; }
.sidebar-nav button {
  text-align: left; padding: 0.75rem 1rem; background: transparent;
  border: none; border-radius: 8px; cursor: pointer; font-size: 0.9rem;
  color: #6b7280; transition: all 0.2s;
}
.sidebar-nav button:hover { background: #f3f4f6; }
.sidebar-nav button.active { background: linear-gradient(135deg, #fef2f2, #eff6ff); color: #ef4444; font-weight: 600; }
.back-link { color: #6b7280; text-decoration: none; font-size: 0.85rem; }

/* Main */
.admin-main { flex: 1; overflow-y: auto; padding: 2rem; }
.tab-content h2 { font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; }
.tab-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.tab-header h2 { margin-bottom: 0; }
.add-btn-primary {
  padding: 0.6rem 1.25rem; background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600;
}

/* Form */
.form-card {
  background: white; padding: 1.5rem; border-radius: 16px; margin-bottom: 1.5rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.form-card h3 { margin-bottom: 1rem; }
.input-field {
  width: 100%; padding: 0.75rem; border: 2px solid #e5e7eb; border-radius: 10px;
  font-size: 0.9rem; margin-bottom: 0.75rem; transition: all 0.3s;
}
.input-field:focus { outline: none; border-color: #ef4444; }
.form-actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
.btn-save {
  padding: 0.6rem 1.5rem; background: #10b981; color: white; border: none;
  border-radius: 8px; cursor: pointer; font-weight: 600;
}
.btn-cancel {
  padding: 0.6rem 1.5rem; background: #f3f4f6; border: none; border-radius: 8px;
  cursor: pointer; color: #6b7280; font-weight: 500;
}

/* Room Grid */
.room-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
.room-card {
  background: white; padding: 1.5rem; border-radius: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: all 0.3s;
}
.room-card:hover { box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
.room-card.inactive { opacity: 0.5; }
.room-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.room-icon { font-size: 2rem; }
.room-status { width: 10px; height: 10px; border-radius: 50%; background: #d1d5db; }
.room-status.active { background: #10b981; }
.room-name { font-size: 1.1rem; font-weight: 700; margin-bottom: 0.25rem; }
.room-desc { font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem; }
.room-date { font-size: 0.75rem; color: #9ca3af; margin-bottom: 1rem; }
.room-actions { display: flex; gap: 0.5rem; }
.btn-edit, .btn-delete {
  padding: 0.4rem 0.75rem; border: 1px solid #e5e7eb; border-radius: 6px;
  cursor: pointer; font-size: 0.8rem; background: white;
}
.btn-edit:hover { background: #f3f4f6; }
.btn-delete { color: #ef4444; border-color: #fecaca; }
.btn-delete:hover { background: #fef2f2; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-card {
  background: white; padding: 2rem; border-radius: 16px; width: 400px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.2);
}

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { padding: 1.5rem; border-radius: 16px; color: white; }
.stat-card.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.stat-card.blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.stat-card.green { background: linear-gradient(135deg, #10b981, #059669); }
.stat-card.purple { background: linear-gradient(135deg, #8b5cf6, #6d28d9); }
.stat-icon { font-size: 2rem; }
.stat-value { font-size: 2rem; font-weight: 800; margin: 0.5rem 0; }
.stat-label { font-size: 0.85rem; opacity: 0.9; }
.refresh-btn { padding: 0.75rem 1.5rem; background: white; border: 2px solid #e5e7eb; border-radius: 10px; cursor: pointer; font-weight: 500; }

/* Table */
.table-container { background: white; border-radius: 12px; overflow: hidden; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: #f9fafb; padding: 0.75rem 1rem; text-align: left; font-size: 0.8rem; text-transform: uppercase; color: #6b7280; }
.data-table td { padding: 0.75rem 1rem; font-size: 0.9rem; border-bottom: 1px solid #f3f4f6; }
.genre-badge { padding: 0.15rem 0.5rem; background: #eff6ff; color: #3b82f6; border-radius: 4px; font-size: 0.75rem; }
.action-sm { padding: 0.25rem 0.5rem; border: 1px solid #e5e7eb; border-radius: 4px; background: white; cursor: pointer; font-size: 0.75rem; margin-right: 0.25rem; }
.action-sm.danger { color: #ef4444; border-color: #fecaca; }

/* Scan */
.scan-card { background: white; border-radius: 16px; padding: 2rem; text-align: center; }
.scan-icon { font-size: 3rem; }
.scan-card h3 { margin: 1rem 0 0.5rem; }
.scan-card code { background: #f3f4f6; padding: 0.2rem 0.5rem; border-radius: 4px; }
.scan-btn { display: block; margin: 1.5rem auto 0; padding: 0.75rem 2rem; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; }
.scan-result { margin-top: 1rem; padding: 0.75rem; background: #ecfdf5; color: #059669; border-radius: 8px; }

/* Users */
.user-cards { display: flex; flex-direction: column; gap: 0.75rem; }
.user-card { display: flex; align-items: center; gap: 1rem; background: white; padding: 1rem; border-radius: 12px; }
.user-avatar { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; }
.user-avatar.red { background: #ef4444; }
.user-avatar.blue { background: #3b82f6; }
.user-info { flex: 1; }
.user-info strong { display: block; }
.user-info span { font-size: 0.8rem; color: #6b7280; }
.role-badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.role-badge.admin { background: #fef2f2; color: #ef4444; }
.role-badge.operator { background: #eff6ff; color: #3b82f6; }
</style>
