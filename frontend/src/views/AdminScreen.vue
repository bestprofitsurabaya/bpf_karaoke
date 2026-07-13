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
      </div>

      <!-- SONGS MANAGEMENT -->
      <div v-if="activeTab === 'songs'">
        <div class="section-header">
          <h2>Manajemen Lagu</h2>
          <div class="header-actions">
            <span class="song-count">{{ filteredSongs.length }} lagu</span>
            <button class="btn-add" @click="autoDetectGenres" :disabled="detectingGenres">
              🤖 {{ detectingGenres ? 'Mendeteksi...' : 'Auto-Detect Lokal' }}
            </button>
            <button class="btn-add online" @click="detectGenreOnline" :disabled="detectingOnline">
              🌐 {{ detectingOnline ? 'Mencari...' : 'Detect Online' }}
            </button>
          </div>
        </div>

        <!-- Genre Filter Bar -->
        <div class="genre-filter-bar">
          <input v-model="songSearch" type="text" placeholder="🔍 Filter lagu..." class="filter-input" />
          <select v-model="genreFilter" class="filter-select" @change="applyGenreFilter">
            <option value="">Semua Genre</option>
            <option v-for="g in allGenres" :key="g.name" :value="g.name">{{ g.name }} ({{ g.count }})</option>
          </select>
          <select v-model="batchGenre" class="filter-select">
            <option value="">Batch: Set Genre...</option>
            <option v-for="g in allGenres" :key="g.name" :value="g.name">{{ g.name }}</option>
          </select>
          <button class="btn-add" @click="applyBatchGenre" :disabled="!batchGenre || selectedSongs.size === 0">
            Apply ({{ selectedSongs.size }})
          </button>
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
              <div class="genre-input-group">
                <select v-model="editForm.genre" class="form-input">
                  <option value="">Pilih Genre...</option>
                  <option v-for="g in allGenres" :key="g.name" :value="g.name">{{ g.name }}</option>
                </select>
                <span class="or-divider">atau</span>
                <input v-model="newGenreInput" type="text" class="form-input" placeholder="Genre baru..." />
                <button class="btn-sm" @click="addNewGenre" title="Tambah genre baru">+</button>
              </div>
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
                <th width="30"><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
                <th>ID</th>
                <th>Judul</th>
                <th>Artis</th>
                <th>Genre</th>
                <th>Play</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="song in paginatedSongs" :key="song.id" :class="{ 'row-selected': selectedSongs.has(song.id) }">
                <td><input type="checkbox" :checked="selectedSongs.has(song.id)" @change="toggleSelect(song.id)" /></td>
                <td>{{ song.id }}</td>
                <td class="td-title">{{ song.title }}</td>
                <td>{{ song.artist || '-' }}</td>
                <td>
                  <span v-if="song.genre" class="genre-badge clickable" @click="quickEditGenre(song)">{{ song.genre }}</span>
                  <span v-else class="genre-badge empty" @click="quickEditGenre(song)">Set Genre</span>
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

        <!-- Pagination -->
        <div class="pagination" v-if="totalPages > 1">
          <button @click="songPage--" :disabled="songPage <= 1">← Prev</button>
          <span v-for="p in totalPages" :key="p" 
                @click="songPage = p" 
                :class="{ active: songPage === p }" 
                class="page-btn">{{ p }}</span>
          <button @click="songPage++" :disabled="songPage >= totalPages">Next →</button>
        </div>

        <!-- Quick Genre Edit Popover -->
        <div class="genre-popover" v-if="quickGenre.show" @click.self="quickGenre.show = false">
          <div class="popover-card">
            <h4>Set Genre untuk #{{ quickGenre.songId }}</h4>
            <div class="quick-genre-list">
              <button v-for="g in quickGenres" :key="g" @click="setQuickGenre(quickGenre.songId, g)" class="genre-option">
                {{ g }}
              </button>
            </div>
            <div class="quick-genre-input">
              <input v-model="quickGenre.newGenre" type="text" placeholder="Genre lain..." class="form-input" />
              <button @click="setQuickGenre(quickGenre.songId, quickGenre.newGenre)" class="btn-save">Set</button>
            </div>
          </div>
        </div>
      </div>
<!-- ROOMS MANAGEMENT -->
      <div v-if="activeTab === 'rooms'">
        <div class="section-header">
          <h2>Room Management</h2>
          <button class="btn-add" @click="openRoomForm">+ Tambah Room</button>
        </div>

        <!-- Room Form -->
        <div class="modal-overlay" v-if="roomForm" @click.self="roomForm = false">
          <div class="modal-card">
            <h3>{{ editingRoom ? '✏️ Edit Room' : '🚪 Tambah Room' }}</h3>
            <div class="form-group">
              <label>Nama Room</label>
              <input v-model="roomData.name" class="form-input" placeholder="Contoh: Room 1" />
            </div>
            <div class="form-group">
              <label>Deskripsi</label>
              <input v-model="roomData.description" class="form-input" placeholder="Deskripsi room..." />
            </div>
            <div class="form-group">
              <label>Kapasitas</label>
              <input v-model.number="roomData.capacity" type="number" class="form-input" min="1" max="50" />
            </div>
            <div class="modal-actions">
              <button class="btn-cancel" @click="roomForm = false">Batal</button>
              <button class="btn-save" @click="saveRoom">💾 Simpan</button>
            </div>
          </div>
        </div>

        <!-- Rooms Grid -->
        <div class="rooms-grid">
          <div v-for="room in rooms" :key="room.id" class="room-card">
            <div class="room-icon">🚪</div>
            <div class="room-info">
              <h3>{{ room.name }}</h3>
              <p>{{ room.description || '-' }}</p>
              <span class="room-capacity">👥 {{ room.capacity }} orang</span>
            </div>
            <div class="room-actions">
              <button class="btn-sm edit" @click="editRoom(room)">✏️</button>
              <button class="btn-sm delete" @click="deleteRoom(room.id)">🗑️</button>
            </div>
          </div>
          <div v-if="rooms.length === 0" class="empty-state">
            <span>🚪</span><p>Belum ada room</p>
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
          <button @click="scanMedia" class="scan-btn" :disabled="scanning">
            {{ scanning ? '⏳ Scanning...' : '🔍 Mulai Scan' }}
          </button>
          <div v-if="scanResult" class="scan-result">✅ {{ scanResult.new_songs }} lagu baru!</div>
        </div>
      </div>
    </main>

    <!-- Toast -->
    <div class="toast" v-if="toast">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import axios from 'axios'

const store = useKaraokeStore()
const activeTab = ref('dashboard')
const songs = ref([])
const rooms = ref([])
const toast = ref('')

// Song management enhancements
const songSearch = ref('')
const genreFilter = ref('')
const batchGenre = ref('')
const selectedSongs = ref(new Set())
const allGenres = ref([])
const songPage = ref(1)
const perPage = 25
const detectingGenres = ref(false)

const detectingOnline = ref(false)
const onlineResults = ref(null)

const newGenreInput = ref('')
const quickGenre = ref({ show: false, songId: null, newGenre: '' })
const quickGenres = ['Pop Indonesia', 'Dangdut', 'Rock', 'K-Pop', 'Barat', 'Mandarin', 'Anak', 'Religi', 'Daerah', 'Ballad', 'Akustik', 'Jazz', 'EDM', 'Hip Hop']

const scanning = ref(false)
const scanResult = ref(null)

// Edit Song
const editModal = ref(null)
const editForm = ref({ id: null, title: '', artist: '', genre: '' })

// Room
const roomForm = ref(false)
const editingRoom = ref(null)
const roomData = ref({ name: '', description: '', capacity: 10 })

const showToast = (msg) => { toast.value = msg; setTimeout(() => toast.value = '', 2000) }

// ============================================
// SONGS
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
  } catch(e) { showToast('❌ Gagal update: ' + (e.response?.data?.detail || e.message)) }
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
  try {
    const res = await axios.get('/api/rooms')
    rooms.value = res.data
  } catch(e) { showToast('❌ Gagal load room') }
}

function openRoomForm() {
  editingRoom.value = null
  roomData.value = { name: '', description: '', capacity: 10 }
  roomForm.value = true
}

function editRoom(room) {
  editingRoom.value = room.id
  roomData.value = { name: room.name, description: room.description || '', capacity: room.capacity }
  roomForm.value = true
}

async function saveRoom() {
  try {
    if (editingRoom.value) {
      await axios.put(`/api/rooms/${editingRoom.value}`, roomData.value)
      showToast('✅ Room diupdate!')
    } else {
      await axios.post('/api/rooms', roomData.value)
      showToast('✅ Room dibuat!')
    }
    roomForm.value = false
    fetchRooms()
  } catch(e) {
    showToast('❌ Gagal: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteRoom(id) {
  if (!confirm('Hapus room ini?')) return
  try {
    await axios.delete(`/api/rooms/${id}`)
    showToast('✅ Room dihapus!')
    fetchRooms()
  } catch(e) { showToast('❌ Gagal hapus') }
}

// ============================================
// SCAN
// ============================================
async function scanMedia() {
  scanning.value = true; scanResult.value = null
  try {
    const res = await axios.post('/api/admin/songs/scan')
    scanResult.value = res.data
    showToast(`✅ ${res.data.new_songs} lagu baru!`)
    fetchSongs(); store.fetchStats()
  } catch(e) { showToast('❌ Scan gagal') }
  scanning.value = false
}


async function fetchGenres() {
  try {
    const res = await axios.get('/api/genres/list')
    allGenres.value = res.data.genres || []
  } catch(e) { console.error('Fetch genres error:', e) }
}

function toggleSelect(id) {
  const s = new Set(selectedSongs.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedSongs.value = s
}

function toggleAll() {
  if (allSelected.value) {
    selectedSongs.value = new Set()
  } else {
    selectedSongs.value = new Set(paginatedSongs.value.map(s => s.id))
  }
}

function applyGenreFilter() {
  songPage.value = 1
}

async function applyBatchGenre() {
  if (!batchGenre.value || selectedSongs.value.size === 0) return
  try {
    await axios.post('/api/songs/batch-genre', {
      song_ids: [...selectedSongs.value],
      genre: batchGenre.value
    })
    showToast(`✅ Genre diupdate untuk ${selectedSongs.value.size} lagu!`)
    selectedSongs.value = new Set()
    batchGenre.value = ''
    fetchSongs()
    fetchGenres()
    store.fetchStats()
  } catch(e) { showToast('❌ Gagal update genre') }
}

async function autoDetectGenres() {
  detectingGenres.value = true
  try {
    const res = await axios.post('/api/genres/detect')
    showToast(`✅ ${res.data.updated} lagu terdeteksi genre!`)
    fetchSongs()
    fetchGenres()
    store.fetchStats()
  } catch(e) { showToast('❌ Auto-detect gagal') }
  detectingGenres.value = false


async function detectGenreOnline() {
  detectingOnline.value = true
  onlineResults.value = null
  try {
    const res = await axios.post('/api/genres/detect-online-batch?limit=50')
    onlineResults.value = res.data
    showToast(`✅ ${res.data.detected} lagu terdeteksi via online!`)
    fetchSongs()
    fetchGenres()
    store.fetchStats()
  } catch(e) {
    showToast('❌ Online detection gagal: ' + (e.response?.data?.detail || e.message))
  }
  detectingOnline.value = false
}

}

function quickEditGenre(song) {
  quickGenre.value = { show: true, songId: song.id, newGenre: '' }
}

async function setQuickGenre(songId, genre) {
  if (!genre) return
  try {
    await axios.put(`/api/songs/${songId}`, {
      title: songs.value.find(s => s.id === songId)?.title || '',
      genre: genre
    })
    showToast(`✅ Genre diupdate!`)
    quickGenre.value.show = false
    fetchSongs()
    fetchGenres()
    store.fetchStats()
  } catch(e) { showToast('❌ Gagal update') }
}

function addNewGenre() {
  if (newGenreInput.value && !allGenres.value.find(g => g.name === newGenreInput.value)) {
    editForm.value.genre = newGenreInput.value
    newGenreInput.value = ''
  }
}

onMounted(() => {
  store.fetchStats()
  fetchSongs()
  fetchRooms()
  fetchGenres()
})

// Fetch rooms when tab switches

const filteredSongs = computed(() => {
  let result = songs.value
  if (songSearch.value) {
    const q = songSearch.value.toLowerCase()
    result = result.filter(s => s.title.toLowerCase().includes(q) || (s.artist && s.artist.toLowerCase().includes(q)))
  }
  if (genreFilter.value) {
    result = result.filter(s => s.genre === genreFilter.value)
  }
  return result
})

const totalPages = computed(() => Math.ceil(filteredSongs.value.length / perPage))

const paginatedSongs = computed(() => {
  const start = (songPage.value - 1) * perPage
  return filteredSongs.value.slice(start, start + perPage)
})

const allSelected = computed(() => {
  return paginatedSongs.value.length > 0 && paginatedSongs.value.every(s => selectedSongs.value.has(s.id))
})

watch(activeTab, (tab) => {
  if (tab === 'rooms') fetchRooms()
  if (tab === 'songs') { fetchSongs(); fetchGenres() }
})

</script>

<script>
import { watch } from 'vue'
export default { setup() { return { watch } } }
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

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.stat-card { padding: 1.25rem; border-radius: 12px; color: white; }
.stat-card.red { background: linear-gradient(135deg, #ef4444, #dc2626); }
.stat-card.blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.stat-card.green { background: linear-gradient(135deg, #10b981, #059669); }
.stat-card.purple { background: linear-gradient(135deg, #8b5cf6, #6d28d9); }
.stat-card span { font-size: 1.5rem; }
.stat-val { font-size: 1.8rem; font-weight: 800; margin: 0.25rem 0; }
.stat-lbl { font-size: 0.8rem; opacity: 0.9; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.song-count { font-size: 0.85rem; color: #94a3b8; }
.btn-add { padding: 0.5rem 1rem; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.8rem; }

/* Table */
.table-container { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th { background: #f8fafc; padding: 0.6rem 0.75rem; text-align: left; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; }
.data-table td { padding: 0.55rem 0.75rem; font-size: 0.82rem; border-bottom: 1px solid #f1f5f9; }
.td-title { font-weight: 600; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.td-actions { display: flex; gap: 0.3rem; }
.genre-badge { padding: 0.1rem 0.4rem; background: #eff6ff; color: #3b82f6; border-radius: 4px; font-size: 0.7rem; }
.btn-sm { padding: 0.25rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 4px; cursor: pointer; font-size: 0.75rem; background: white; }
.btn-sm.edit:hover { background: #eff6ff; border-color: #3b82f6; }
.btn-sm.delete:hover { background: #fef2f2; border-color: #ef4444; }

/* Rooms Grid */
.rooms-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
.room-card { background: white; border-radius: 12px; padding: 1.25rem; display: flex; gap: 1rem; align-items: center; border: 1px solid #f1f5f9; }
.room-icon { font-size: 2rem; }
.room-info { flex: 1; }
.room-info h3 { font-size: 1rem; font-weight: 700; }
.room-info p { font-size: 0.8rem; color: #94a3b8; }
.room-capacity { font-size: 0.75rem; color: #64748b; }
.room-actions { display: flex; flex-direction: column; gap: 0.3rem; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-card { background: white; border-radius: 16px; padding: 2rem; width: 400px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
.modal-card h3 { margin-bottom: 1.25rem; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.3rem; color: #475569; }
.form-input { width: 100%; padding: 0.6rem 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.9rem; }
.form-input:focus { outline: none; border-color: #ef4444; }
.modal-actions { display: flex; gap: 0.5rem; margin-top: 1.5rem; }
.btn-cancel { flex: 1; padding: 0.6rem; background: #f1f5f9; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
.btn-save { flex: 1; padding: 0.6rem; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }

/* Scan */
.scan-card { background: white; border-radius: 16px; padding: 2rem; text-align: center; }
.scan-icon { font-size: 3rem; }
.scan-card h3 { margin: 1rem 0 0.5rem; }
.scan-card code { background: #f1f5f9; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }
.scan-btn { margin-top: 1rem; padding: 0.7rem 2rem; background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; }
.scan-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.scan-result { margin-top: 1rem; padding: 0.5rem; background: #f0fdf4; color: #16a34a; border-radius: 8px; font-weight: 500; }

.empty-state { grid-column: 1/-1; text-align: center; padding: 2rem; color: #94a3b8; }
.empty-state span { font-size: 2rem; display: block; }

.toast { position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%); background: #1e293b; color: white; padding: 0.6rem 1.5rem; border-radius: 2rem; font-size: 0.85rem; z-index: 200; box-shadow: 0 10px 25px rgba(0,0,0,0.2); animation: toastIn 0.3s ease-out; }
@keyframes toastIn { from{opacity:0;transform:translateX(-50%) translateY(20px)} to{opacity:1;transform:translateX(-50%) translateY(0)} }

/* Genre Management */
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.genre-filter-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 0;
  align-items: center;
  flex-wrap: wrap;
}

.filter-input {
  padding: 0.45rem 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.8rem;
  flex: 1;
  min-width: 150px;
}

.filter-select {
  padding: 0.45rem 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.8rem;
  background: white;
}

.row-selected {
  background: #eff6ff !important;
}

.genre-badge.clickable {
  cursor: pointer;
  transition: all 0.2s;
}

.genre-badge.clickable:hover {
  background: #dbeafe;
  transform: scale(1.05);
}

.genre-badge.empty {
  background: #fef3c7;
  color: #92400e;
  cursor: pointer;
  font-style: italic;
  font-size: 0.65rem;
}

.genre-input-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.or-divider {
  font-size: 0.75rem;
  color: #94a3b8;
  flex-shrink: 0;
}

/* Pagination */
.pagination {
  display: flex;
  gap: 0.35rem;
  align-items: center;
  justify-content: center;
  padding: 1rem 0;
}

.page-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.2s;
}

.page-btn:hover { background: #f1f5f9; }

.page-btn.active {
  background: #ef4444;
  color: white;
  border-color: #ef4444;
}

.pagination button {
  padding: 0.4rem 0.8rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 0.8rem;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Genre Popover */
.genre-popover {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.popover-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  max-width: 350px;
  width: 90%;
}

.popover-card h4 {
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.quick-genre-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1rem;
}

.genre-option {
  padding: 0.35rem 0.75rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 2rem;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.2s;
}

.genre-option:hover {
  background: #fef2f2;
  border-color: #fecaca;
  color: #ef4444;
}

.quick-genre-input {
  display: flex;
  gap: 0.5rem;
}

.quick-genre-input .form-input {
  flex: 1;
}


.btn-add.online {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

</style>
