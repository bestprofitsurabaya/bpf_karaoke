<template>
  <div class="admin-screen">
    <!-- Sidebar -->
    <aside class="admin-sidebar">
      <div class="sidebar-brand">
        <img src="/icons/icon-512x512.png" alt="BPF" class="sidebar-logo" />
        <span>Admin Panel</span>
      </div>
      <nav class="sidebar-nav">
        <button @click="activeTab = 'dashboard'" :class="{ active: activeTab === 'dashboard' }">📊 Dashboard</button>
        <button @click="activeTab = 'songs'" :class="{ active: activeTab === 'songs' }">🎵 Lagu</button>
        <button @click="activeTab = 'rooms'" :class="{ active: activeTab === 'rooms' }">🚪 Room</button>
        <button @click="activeTab = 'scan'" :class="{ active: activeTab === 'scan' }">📂 Scan</button>
      </nav>
      <router-link to="/" class="back-link">← Kembali</router-link>
    </aside>

    <!-- Main -->
    <main class="admin-main">
      <!-- DASHBOARD -->
      <div v-if="activeTab === 'dashboard'">
        <h2>Dashboard</h2>
        <div class="stats-grid">
          <div class="stat-card red"><span>🎵</span><div class="stat-val">{{ store.stats.total_songs || 0 }}</div><div class="stat-lbl">Total Lagu</div></div>
          <div class="stat-card blue"><span>▶️</span><div class="stat-val">{{ store.stats.total_plays || 0 }}</div><div class="stat-lbl">Total Play</div></div>
          <div class="stat-card green"><span>📋</span><div class="stat-val">{{ store.stats.queue_today || 0 }}</div><div class="stat-lbl">Queue Hari Ini</div></div>
          <div class="stat-card purple"><span>🟢</span><div class="stat-val">{{ store.stats.active_connections || 0 }}</div><div class="stat-lbl">Koneksi</div></div>
        </div>
        
        <!-- AI Genre Stats -->
        <div class="ai-stats-card">
          <h3>🤖 AI Genre Detector</h3>
          <button @click="runAutoGenre" class="btn-ai-detect" :disabled="aiDetecting">
            {{ aiDetecting ? '⏳ Mendeteksi...' : '🔍 Auto-Detect Genre' }}
          </button>
          <div v-if="aiResult" class="ai-result">
            <span class="ai-result-icon">✅</span>
            <span>{{ aiResult.auto_assigned }} lagu auto-assigned, {{ aiResult.set_to_unknown }} perlu review</span>
          </div>
        </div>
      </div>

      <!-- SONGS MANAGEMENT -->
      <div v-if="activeTab === 'songs'">
        <div class="section-header">
          <h2>Manajemen Lagu</h2>
          <div class="header-actions">
            <button @click="runAutoGenre" class="btn-action ai" :disabled="aiDetecting">
              🤖 {{ aiDetecting ? 'Detecting...' : 'Auto Genre' }}
            </button>
            <span class="song-count">{{ songs.length }} lagu</span>
          </div>
        </div>

        <!-- BULK ACTION BAR -->
        <div class="bulk-bar" v-if="selectedSongs.size > 0">
          <div class="bulk-info">
            <span class="bulk-count">{{ selectedSongs.size }} lagu dipilih</span>
            <button @click="clearSelection" class="bulk-clear">Batal</button>
          </div>
          <div class="bulk-actions">
            <div class="bulk-genre-select">
              <GenreDropdown v-model="bulkGenre" placeholder="Pilih genre massal..." />
            </div>
            <button @click="applyBulkGenre" class="btn-bulk-apply" :disabled="!bulkGenre">
              Terapkan Massal
            </button>
          </div>
        </div>

        <!-- Edit Modal -->
        <div class="modal-overlay" v-if="editModal" @click.self="editModal = null">
          <div class="modal-card">
            <h3>✏️ Edit Lagu #{{ editForm.id }}</h3>
            <div class="form-group">
              <label>Judul</label>
              <input v-model="editForm.title" class="form-input" />
            </div>
            <div class="form-group">
              <label>Artis</label>
              <input v-model="editForm.artist" class="form-input" />
            </div>
            <div class="form-group">
              <label>Genre</label>
              <GenreDropdown v-model="editForm.genre" placeholder="Pilih atau ketik genre..." />
            </div>
            <div class="modal-actions">
              <button class="btn-cancel" @click="editModal = null">Batal</button>
              <button class="btn-save" @click="saveEdit">💾 Simpan</button>
            </div>
          </div>
        </div>

        <!-- Songs Table -->
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th class="th-check">
                  <input type="checkbox" @change="toggleAll" :checked="allSelected" />
                </th>
                <th>ID</th>
                <th>Judul</th>
                <th>Artis</th>
                <th>Genre</th>
                <th>Play</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="song in songs" :key="song.id" :class="{ selected: selectedSongs.has(song.id) }">
                <td class="td-check">
                  <input 
                    type="checkbox" 
                    :checked="selectedSongs.has(song.id)"
                    @change="toggleSong(song.id)"
                  />
                </td>
                <td>{{ song.id }}</td>
                <td class="td-title">{{ song.title }}</td>
                <td>{{ song.artist || '-' }}</td>
                <td>
                  <span class="genre-badge" :class="{ unknown: song.genre === 'Unknown' || !song.genre }">
                    {{ song.genre || 'Unknown' }}
                  </span>
                </td>
                <td>{{ song.play_count }}x</td>
                <td class="td-actions">
                  <button class="btn-sm edit" @click="openEdit(song)">✏️</button>
                  <button class="btn-sm delete" @click="deleteSong(song.id)">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ROOMS MANAGEMENT -->
      <div v-if="activeTab === 'rooms'">
        <div class="section-header">
          <h2>Room Management</h2>
          <button class="btn-add" @click="openRoomForm">+ Tambah Room</button>
        </div>
        <div class="modal-overlay" v-if="roomForm" @click.self="roomForm = false">
          <div class="modal-card">
            <h3>{{ editingRoom ? '✏️ Edit Room' : '🚪 Tambah Room' }}</h3>
            <div class="form-group"><label>Nama Room</label><input v-model="roomData.name" class="form-input" /></div>
            <div class="form-group"><label>Deskripsi</label><input v-model="roomData.description" class="form-input" /></div>
            <div class="form-group"><label>Kapasitas</label><input v-model.number="roomData.capacity" type="number" class="form-input" min="1" max="50" /></div>
            <div class="modal-actions"><button class="btn-cancel" @click="roomForm = false">Batal</button><button class="btn-save" @click="saveRoom">💾 Simpan</button></div>
          </div>
        </div>
        <div class="rooms-grid">
          <div v-for="room in rooms" :key="room.id" class="room-card">
            <div class="room-icon">🚪</div>
            <div class="room-info"><h3>{{ room.name }}</h3><p>{{ room.description || '-' }}</p><span class="room-capacity">👥 {{ room.capacity }} orang</span></div>
            <div class="room-actions"><button class="btn-sm edit" @click="editRoom(room)">✏️</button><button class="btn-sm delete" @click="deleteRoom(room.id)">🗑️</button></div>
          </div>
        </div>
      </div>

      <!-- SCAN MEDIA -->
      <div v-if="activeTab === 'scan'">
        <h2>Scan Media Folder</h2>
        <div class="scan-card">
          <span class="scan-icon">📂</span>
          <h3>Scan Lagu Baru</h3>
          <p>Folder: <code>/media/lagu/</code></p>
          <p class="scan-note">🤖 AI akan otomatis mendeteksi genre saat scan</p>
          <button @click="scanMedia" class="scan-btn" :disabled="scanning">
            {{ scanning ? '⏳ Scanning...' : '🔍 Mulai Scan' }}
          </button>
          <div v-if="scanResult" class="scan-result">✅ {{ scanResult.new_songs }} lagu baru ditambahkan!</div>
        </div>
      </div>
    </main>

    <!-- Toast -->
    <div class="toast" v-if="toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import GenreDropdown from '@/components/GenreDropdown.vue'
import axios from 'axios'

const store = useKaraokeStore()
const activeTab = ref('dashboard')
const songs = ref([])
const rooms = ref([])
const toast = ref('')
const scanning = ref(false)
const scanResult = ref(null)
const aiDetecting = ref(false)
const aiResult = ref(null)

// Selection
const selectedSongs = ref(new Set())
const bulkGenre = ref('')

// Edit
const editModal = ref(null)
const editForm = ref({ id: null, title: '', artist: '', genre: '' })

// Room
const roomForm = ref(false)
const editingRoom = ref(null)
const roomData = ref({ name: '', description: '', capacity: 10 })

// Computed
const allSelected = computed(() => {
  return songs.value.length > 0 && selectedSongs.value.size === songs.value.length
})

// Toast
function showToast(msg) { toast.value = msg; setTimeout(() => toast.value = '', 2500) }

// ============================================
// SELECTION
// ============================================
function toggleSong(id) {
  const newSet = new Set(selectedSongs.value)
  if (newSet.has(id)) newSet.delete(id)
  else newSet.add(id)
  selectedSongs.value = newSet
}

function toggleAll() {
  if (allSelected.value) {
    selectedSongs.value = new Set()
  } else {
    selectedSongs.value = new Set(songs.value.map(s => s.id))
  }
}

function clearSelection() {
  selectedSongs.value = new Set()
  bulkGenre.value = ''
}

// ============================================
// BULK GENRE
// ============================================
async function applyBulkGenre() {
  if (!bulkGenre.value || selectedSongs.value.size === 0) return
  
  try {
    const ids = Array.from(selectedSongs.value)
    const res = await axios.post(`/api/admin/songs/bulk-genre?genre=${encodeURIComponent(bulkGenre.value)}`, ids)
    showToast(`✅ ${res.data.updated_count} lagu diupdate ke "${bulkGenre.value}"!`)
    bulkGenre.value = ''
    selectedSongs.value = new Set()
    fetchSongs()
  } catch(e) {
    showToast('❌ Gagal update massal: ' + (e.response?.data?.detail || e.message))
  }
}

// ============================================
// AUTO GENRE DETECTION
// ============================================
async function runAutoGenre() {
  aiDetecting.value = true
  aiResult.value = null
  try {
    const res = await axios.post('/api/admin/songs/auto-genre')
    aiResult.value = res.data
    showToast(`🤖 ${res.data.auto_assigned} lagu auto-assigned, ${res.data.set_to_unknown} perlu review`)
    fetchSongs()
    store.fetchStats()
  } catch(e) {
    showToast('❌ Auto-detect gagal')
  }
  aiDetecting.value = false
}

// ============================================
// SONGS CRUD
// ============================================
async function fetchSongs() {
  try {
    const res = await axios.get('/api/songs?limit=500')
    songs.value = res.data
  } catch(e) { showToast('❌ Gagal load lagu') }
}

function openEdit(song) {
  editForm.value = { id: song.id, title: song.title, artist: song.artist || '', genre: song.genre || '' }
  editModal.value = true
}

async function saveEdit() {
  try {
    await axios.put(`/api/songs/${editForm.value.id}`, {
      title: editForm.value.title,
      artist: editForm.value.artist || null,
      genre: editForm.value.genre || null
    })
    showToast('✅ Lagu diupdate!')
    editModal.value = null
    fetchSongs()
  } catch(e) { showToast('❌ Gagal update') }
}

async function deleteSong(id) {
  if (!confirm('Hapus lagu ini?')) return
  try {
    await axios.delete(`/api/songs/${id}`)
    showToast('✅ Lagu dihapus!')
    fetchSongs()
  } catch(e) { showToast('❌ Gagal hapus') }
}

// ============================================
// ROOMS
// ============================================
async function fetchRooms() {
  try { const res = await axios.get('/api/rooms'); rooms.value = res.data } catch(e) {}
}

function openRoomForm() { editingRoom.value = null; roomData.value = { name: '', description: '', capacity: 10 }; roomForm.value = true }
function editRoom(room) { editingRoom.value = room.id; roomData.value = { name: room.name, description: room.description || '', capacity: room.capacity }; roomForm.value = true }

async function saveRoom() {
  try {
    if (editingRoom.value) { await axios.put(`/api/rooms/${editingRoom.value}`, roomData.value); showToast('✅ Room diupdate!') }
    else { await axios.post('/api/rooms', roomData.value); showToast('✅ Room dibuat!') }
    roomForm.value = false; fetchRooms()
  } catch(e) { showToast('❌ Gagal') }
}

async function deleteRoom(id) {
  if (!confirm('Hapus room ini?')) return
  try { await axios.delete(`/api/rooms/${id}`); showToast('✅ Room dihapus!'); fetchRooms() } catch(e) {}
}

// ============================================
// SCAN
// ============================================
async function scanMedia() {
  scanning.value = true; scanResult.value = null
  try {
    const res = await axios.post('/api/admin/songs/scan')
    scanResult.value = res.data
    showToast(`✅ ${res.data.new_songs} lagu baru! (AI genre auto-detected)`)
    fetchSongs(); store.fetchStats()
  } catch(e) { showToast('❌ Scan gagal') }
  scanning.value = false
}

// Lifecycle
onMounted(() => {
  store.fetchStats()
  fetchSongs()
  fetchRooms()
})

watch(activeTab, (tab) => {
  if (tab === 'rooms') fetchRooms()
  if (tab === 'songs') fetchSongs()
})
</script>

<style scoped>
.admin-screen { display: flex; height: 100vh; background: #f8fafc; color: #1e293b; }
.admin-sidebar { width: 220px; background: white; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; padding: 1.25rem; }
.sidebar-brand { display: flex; align-items: center; gap: 0.5rem; font-weight: 700; font-size: 1rem; margin-bottom: 1.5rem; }
.sidebar-logo { width: 32px; height: 32px; border-radius: 6px; object-fit: contain; }
.sidebar-nav { display: flex; flex-direction: column; gap: 0.2rem; flex: 1; }
.sidebar-nav button { text-align: left; padding: 0.6rem 0.75rem; background: transparent; border: none; border-radius: 8px; cursor: pointer; font-size: 0.85rem; color: #64748b; transition: all .2s; }
.sidebar-nav button:hover { background: #f1f5f9; }
.sidebar-nav button.active { background: #fef2f2; color: #ef4444; font-weight: 600; }
.back-link { color: #94a3b8; text-decoration: none; font-size: 0.8rem; margin-top: 0.5rem; }

.admin-main { flex: 1; overflow-y: auto; padding: 1.5rem 2rem; }
.admin-main h2 { font-size: 1.3rem; font-weight: 700; margin-bottom: 1.25rem; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { padding: 1.25rem; border-radius: 12px; color: white; }
.stat-card.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.stat-card.blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.stat-card.green { background: linear-gradient(135deg, #10b981, #059669); }
.stat-card.purple { background: linear-gradient(135deg, #8b5cf6, #6d28d9); }
.stat-val { font-size: 1.8rem; font-weight: 800; margin: 0.25rem 0; }
.stat-lbl { font-size: 0.8rem; opacity: 0.9; }

.ai-stats-card { background: white; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; border: 1px solid #f1f5f9; }
.ai-stats-card h3 { font-size: 1rem; margin-bottom: 0.75rem; }
.btn-ai-detect { padding: 0.6rem 1.5rem; background: linear-gradient(135deg, #8b5cf6, #6d28d9); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.85rem; }
.btn-ai-detect:disabled { opacity: 0.6; cursor: not-allowed; }
.ai-result { margin-top: 0.75rem; padding: 0.5rem; background: #f0fdf4; border-radius: 8px; font-size: 0.85rem; color: #16a34a; display: flex; align-items: center; gap: 0.5rem; }

/* Section Header */
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.header-actions { display: flex; align-items: center; gap: 0.75rem; }
.song-count { font-size: 0.85rem; color: #94a3b8; }
.btn-action { padding: 0.45rem 1rem; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.8rem; }
.btn-action.ai { background: #f3e8ff; color: #7c3aed; }
.btn-add { padding: 0.5rem 1rem; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.8rem; }

/* BULK BAR */
.bulk-bar { background: linear-gradient(135deg, #eff6ff, #fef2f2); border: 2px solid #bfdbfe; border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 1rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; animation: slideDown 0.3s ease-out; }
@keyframes slideDown { from{opacity:0;transform:translateY(-10px)} to{opacity:1;transform:translateY(0)} }
.bulk-info { display: flex; align-items: center; gap: 0.75rem; }
.bulk-count { font-weight: 700; color: #1e40af; font-size: 0.9rem; }
.bulk-clear { background: none; border: none; color: #ef4444; cursor: pointer; font-weight: 500; font-size: 0.8rem; }
.bulk-actions { display: flex; align-items: center; gap: 0.75rem; }
.bulk-genre-select { width: 220px; }
.btn-bulk-apply { padding: 0.5rem 1.25rem; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.8rem; white-space: nowrap; }
.btn-bulk-apply:disabled { opacity: 0.5; cursor: not-allowed; }

/* Table */
.table-container { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: #f8fafc; padding: 0.6rem 0.75rem; text-align: left; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }
.data-table td { padding: 0.55rem 0.75rem; font-size: 0.82rem; border-bottom: 1px solid #f1f5f9; }
.th-check, .td-check { width: 40px; text-align: center; }
.td-title { font-weight: 600; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.td-actions { display: flex; gap: 0.3rem; }
tr.selected { background: #eff6ff; }
.genre-badge { padding: 0.15rem 0.5rem; background: #eff6ff; color: #3b82f6; border-radius: 4px; font-size: 0.7rem; font-weight: 500; }
.genre-badge.unknown { background: #fef3c7; color: #92400e; font-style: italic; }
.btn-sm { padding: 0.25rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.75rem; background: white; }
.btn-sm.edit:hover { background: #eff6ff; border-color: #3b82f6; }
.btn-sm.delete:hover { background: #fef2f2; border-color: #ef4444; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-card { background: white; border-radius: 16px; padding: 2rem; width: 420px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
.modal-card h3 { margin-bottom: 1.25rem; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.3rem; color: #475569; }
.form-input { width: 100%; padding: 0.6rem 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.9rem; }
.form-input:focus { outline: none; border-color: #ef4444; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1.5rem; }
.btn-cancel { flex: 1; padding: 0.6rem; background: #f1f5f9; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
.btn-save { flex: 1; padding: 0.6rem; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }

/* Rooms */
.rooms-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
.room-card { background: white; border-radius: 12px; padding: 1.25rem; display: flex; gap: 1rem; align-items: center; border: 1px solid #f1f5f9; }
.room-icon { font-size: 2rem; }
.room-info { flex: 1; }
.room-info h3 { font-size: 1rem; font-weight: 700; }
.room-info p { font-size: 0.8rem; color: #94a3b8; }
.room-capacity { font-size: 0.75rem; color: #64748b; }
.room-actions { display: flex; flex-direction: column; gap: 0.3rem; }

/* Scan */
.scan-card { background: white; border-radius: 16px; padding: 2rem; text-align: center; }
.scan-icon { font-size: 3rem; }
.scan-card h3 { margin: 1rem 0 0.5rem; }
.scan-card code { background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }
.scan-note { color: #7c3aed; font-size: 0.8rem; margin-top: 0.5rem; }
.scan-btn { margin-top: 1rem; padding: 0.7rem 2rem; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; }
.scan-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.scan-result { margin-top: 1rem; padding: 0.5rem; background: #f0fdf4; color: #16a34a; border-radius: 8px; font-weight: 500; }

.toast { position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%); background: #1e293b; color: white; padding: 0.6rem 1.5rem; border-radius: 2rem; font-size: 0.85rem; z-index: 200; box-shadow: 0 10px 25px rgba(0,0,0,0.2); animation: toastIn 0.3s ease-out; }
@keyframes toastIn { from{opacity:0;transform:translateX(-50%) translateY(20px)} to{opacity:1;transform:translateX(-50%) translateY(0)} }
</style>
