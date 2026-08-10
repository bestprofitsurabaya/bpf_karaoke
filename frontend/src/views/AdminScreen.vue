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
        <button @click="activeTab = 'sesi'" :class="{ active: activeTab === 'sesi' }">⏱️ Sesi Room</button>
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

        <!-- SINKRONISASI BANK KARAOKE (Windows XP) -->
        <div class="sync-card" :class="{ done: syncState?.done, error: syncState?.phase === 'error' }">
          <div class="sync-head">
            <h3>📥 Sinkronisasi Bank Karaoke <small>(Windows XP \\Karaoke)</small></h3>
            <span class="sync-badge" :class="{ done: syncState?.done, err: syncState?.phase === 'error', live: syncState?.available && !syncState?.done }">
              {{ syncState?.done ? '✅ SEMUA TERSALIN' : (syncState?.available ? '🔄 MENGIRIM...' : (syncState?.error ? '⚠️ ERROR' : '⏸ BELUM JALAN')) }}
            </span>
          </div>

          <div v-if="syncState?.available" class="sync-body">
            <div class="progress-track">
              <div class="progress-fill" :class="{ counting: !syncState.total_known }" :style="{ width: Math.min(100, syncState.percent || 0) + '%' }"></div>
            </div>
            <div class="sync-stats">
              <span>📄 {{ syncState.copied_files || 0 }} file tersalin</span>
              <span v-if="syncState.total_known">/ {{ syncState.total_files || 0 }} total ({{ syncState.percent || 0 }}%)</span>
              <span v-else class="sync-counting">· menghitung total bank...</span>
              <span>💾 {{ fmtGb(syncState.copied_bytes) }}</span>
              <span>🚫 {{ syncState.errors || 0 }} error</span>
            </div>
            <div v-if="syncState.current_file" class="sync-file" :title="syncState.current_file">📍 {{ syncState.current_file }}</div>
            <div v-if="syncState.done" class="sync-done-note">🎉 Semua lagu dari {{ (syncState.shares || []).join(' & ') }} sudah tersalin ke server. Proses transcode MPEG → MP4 masih berjalan di background.</div>
            <div v-if="syncState.disk?.warning" class="sync-disk-warn">⚠️ {{ syncState.disk.warning }} (bebas {{ syncState.disk.free_gb }} GB)</div>
            <div v-else-if="syncState.disk" class="sync-disk">💿 Disk server: bebas {{ syncState.disk.free_gb }} GB dari {{ syncState.disk.total_gb }} GB</div>
            <div v-if="syncState.last_error && !syncState.done" class="sync-err">Terakhir: {{ syncState.last_error }}</div>
          </div>
          <p v-else class="sync-empty">{{ syncState?.error || 'Menunggu sinkronisasi dimulai...' }}</p>
        </div>

        <!-- PIPELINE TRANSCODE (setelah sync) -->
        <div class="sync-card pipeline-card" :class="{ warn: pipelineWarn }">
          <div class="sync-head">
            <h3>🛠 Pipeline Transcode <small>(MPEG → MP4, hapus sumber)</small></h3>
            <div class="pipeline-actions">
              <button class="btn-pipe" @click="triggerScan" :disabled="pipeBusy" :title="'Picu scan media + antre transcode'">🔍 Scan</button>
              <button class="btn-pipe" @click="triggerSweep" :disabled="pipeBusy" :title="'Bersihkan .part basi dari task yang mati'">🧹 Sweep</button>
              <button class="btn-pipe refresh" @click="store.fetchPipeline()" :title="'Segarkan data pipeline'">🔄</button>
            </div>
          </div>

          <div v-if="store.pipeline" class="pipe-grid">
            <div class="pipe-cell" title="Task transcode menunggu worker">
              <span class="pc-icon">🔄</span><div class="pc-val">{{ store.pipeline.transcode?.queue ?? '–' }}</div><div class="pc-lbl">Antrian</div>
            </div>
            <div class="pipe-cell" title="File sudah ditandai & belum selesai">
              <span class="pc-icon">📌</span><div class="pc-val">{{ store.pipeline.transcode?.pending ?? '–' }}</div><div class="pc-lbl">Pending</div>
            </div>
            <div class="pipe-cell" title="MP4 hasil transcode siap diputar">
              <span class="pc-icon">🎞️</span><div class="pc-val">{{ fmtCount(store.pipeline.transcode?.mp4_ready) }}</div><div class="pc-lbl">MP4 siap</div>
            </div>
            <div class="pipe-cell" title="Sumber master (mpg/avi/dll) tersisa">
              <span class="pc-icon">💿</span><div class="pc-val">{{ fmtCount(store.pipeline.transcode?.sources) }}</div><div class="pc-lbl">Sumber</div>
            </div>
            <div class="pipe-cell" :class="{ bad: pipeStale }" title="File .part basi (>1 jam, task mati) — blokir lagu sampai disweep">
              <span class="pc-icon">🧩</span><div class="pc-val">{{ store.pipeline.transcode?.stale_parts ?? 0 }}</div><div class="pc-lbl">.part basi</div>
            </div>
            <div class="pipe-cell" :class="{ bad: pipeDiskLow }" title="Ruang disk bebas partisi media">
              <span class="pc-icon">💾</span><div class="pc-val">{{ fmtGB(store.pipeline.disk?.free) }}</div><div class="pc-lbl">Disk bebas</div>
            </div>
          </div>
          <p v-else class="sync-empty">Memuat status pipeline...</p>
          <div v-if="pipeBusyMsg" class="pipe-msg" :class="{ err: pipeMsgErr }">{{ pipeBusyMsg }}</div>
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

      <!-- ROOM SESSIONS (DURASI PENGGUNAAN) -->
      <div v-if="activeTab === 'sesi'">
        <div class="section-header">
          <h2>⏱️ Durasi Penggunaan Room</h2>
          <div class="header-actions">
            <span class="realtime-badge" :class="{ live: realtimeLive }" :title="lastSyncAt ? 'Terakhir sinkron: ' + formatClock(lastSyncAt) : 'Menunggu koneksi realtime'">
              <span class="rt-dot"></span>
              {{ realtimeLive ? 'Realtime' : 'Offline' }}
              <span v-if="lastSyncAt" class="rt-time">· {{ formatClock(lastSyncAt) }}</span>
            </span>
            <button class="btn-add" @click="refreshSessionStates">🔄 Refresh</button>
          </div>
        </div>

        <div class="rooms-grid">
          <div v-for="room in sessionRooms" :key="room.id" class="room-card" :class="{ 'room-busy': room.session_status === 'active' }">
            <div class="room-icon">🚪</div>
            <div class="room-info">
              <h3>{{ room.name }}</h3>
              <span class="session-badge" :class="{ active: room.session_status === 'active' }">
                <template v-if="room.session_status === 'active'">🔴 Terpakai · sisa {{ formatRemaining(room.session_remaining_seconds) }}</template>
                <template v-else>🟢 Kosong</template>
              </span>
            </div>
            <div class="room-actions">
              <button v-if="room.session_status !== 'active'" class="btn-session start" @click="openSessionModal('start', room)">▶ Mulai</button>
              <template v-else>
                <button class="btn-session extend" @click="openSessionModal('extend', room)">+ Perpanjang</button>
                <button class="btn-session end" @click="endSession(room)">■ Selesai</button>
              </template>
            </div>
          </div>
          <div v-if="sessionRooms.length === 0" class="browser-empty"><h3>Belum ada room</h3></div>
        </div>

        <!-- History -->
        <div class="history-card">
          <div class="history-header">
            <h3>🕐 Riwayat Sesi</h3>
            <select v-model="historyRoom" class="form-input history-select" @change="fetchSessionHistory">
              <option value="">Pilih room...</option>
              <option v-for="room in sessionRooms" :key="room.id" :value="room.name">{{ room.name }}</option>
            </select>
          </div>
          <table class="data-table" v-if="sessionHistory.length">
            <thead><tr><th>Mulai</th><th>Berakhir Target</th><th>Selesai</th><th>Durasi</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="h in sessionHistory" :key="h.id">
                <td>{{ formatDateTime(h.started_at) }}</td>
                <td>{{ formatDateTime(h.end_time) }}</td>
                <td>{{ formatDateTime(h.ended_at) }}</td>
                <td>{{ h.duration_minutes ?? '-' }} mnt</td>
                <td>{{ h.status }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="history-empty">Pilih room untuk melihat riwayat sesi</p>
        </div>
      </div>

      <!-- SESSION MODAL (Start / Extend) -->
      <div class="modal-overlay" v-if="sessionModal" @click.self="sessionModal = null">
        <div class="modal-card">
          <h3>{{ sessionModal.mode === 'start' ? '▶ Mulai Sesi ' : '⏱️ Perpanjang Sesi ' }}{{ sessionModal.room?.name }}</h3>

          <div class="form-group">
            <label>Cara menentukan waktu selesai</label>
            <div class="radio-row">
              <label class="radio-pill"><input type="radio" value="duration" v-model="sessionForm.type" /> Durasi (menit)</label>
              <label class="radio-pill"><input type="radio" value="endtime" v-model="sessionForm.type" /> Berakhir jam</label>
            </div>
          </div>

          <div class="form-group" v-if="sessionForm.type === 'duration'">
            <label>{{ sessionModal.mode === 'start' ? 'Durasi sewa' : 'Menit tambahan' }}</label>
            <div class="preset-row">
              <button v-for="p in (sessionModal.mode === 'start' ? [30,60,90,120,150,180] : [15,30,60,90])" :key="p"
                      class="preset-btn" :class="{ active: sessionForm.minutes === p }" @click="sessionForm.minutes = p">
                {{ p }} mnt
              </button>
              <input v-model.number="sessionForm.minutes" type="number" min="1" class="form-input preset-custom" placeholder="Custom" />
            </div>
          </div>

          <div class="form-group" v-else>
            <label>Berakhir pada jam</label>
            <input v-model="sessionForm.endTime" type="datetime-local" class="form-input" />
            <span class="field-hint">Contoh: pilih 22:00 → sesi berakhir pukul 22.00</span>
          </div>

          <div class="form-group" v-if="sessionModal.mode === 'start'">
            <label>Catatan (opsional)</label>
            <input v-model="sessionForm.note" class="form-input" placeholder="Contoh: Paket 1 jam, tamu A" />
          </div>

          <div class="modal-actions">
            <button class="btn-cancel" @click="sessionModal = null">Batal</button>
            <button class="btn-save" @click="submitSession">💾 Simpan</button>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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

// Sinkronisasi Bank Karaoke
const syncState = ref(null)
let syncPollTimer = null

// ========== PIPELINE TRANSCODE ==========
const pipeBusy = ref(false)
const pipeBusyMsg = ref('')
const pipeMsgErr = ref(false)
let pipelineTimer = null

const pipelineWarn = computed(() => {
  const p = store.pipeline
  if (!p) return false
  return (p.transcode?.stale_parts || 0) > 0 || pipeDiskLow.value
})
const pipeStale = computed(() => (store.pipeline?.transcode?.stale_parts || 0) > 0)
const pipeDiskLow = computed(() => {
  const f = store.pipeline?.disk?.free
  return typeof f === 'number' && f > 0 && f < 50e9
})
function fmtCount(n) { if (n == null || isNaN(n)) return '–'; return n >= 1000 ? (n / 1000).toFixed(1).replace('.', ',') + 'K' : String(n) }
function fmtGB(n) { if (n == null || isNaN(n)) return '–'; return (n / 1e9).toFixed(0) + ' GB' }

async function triggerScan() {
  pipeBusy.value = true; pipeBusyMsg.value = '⏳ Menjadwalkan scan media...'; pipeMsgErr.value = false
  try {
    const res = await axios.post('/api/admin/pipeline/scan')
    pipeBusyMsg.value = `✅ Scan dijadwalkan (task ${String(res.data.task_id).slice(0, 8)})`
    setTimeout(() => { if (!pipeMsgErr.value) pipeBusyMsg.value = '' }, 5000)
  } catch (e) {
    pipeBusyMsg.value = '❌ ' + (e.response?.data?.detail || 'Gagal menjadwalkan scan'); pipeMsgErr.value = true
  }
  pipeBusy.value = false
}

async function triggerSweep() {
  pipeBusy.value = true; pipeBusyMsg.value = '⏳ Menjalankan sweep .part basi...'; pipeMsgErr.value = false
  try {
    const res = await axios.post('/api/admin/pipeline/sweep')
    pipeBusyMsg.value = `✅ Sweep dijalankan (task ${String(res.data.task_id).slice(0, 8)})`
    setTimeout(() => { if (!pipeMsgErr.value) pipeBusyMsg.value = '' }, 5000)
  } catch (e) {
    pipeBusyMsg.value = '❌ ' + (e.response?.data?.detail || 'Gagal menjalankan sweep'); pipeMsgErr.value = true
  }
  pipeBusy.value = false
}

function fmtGb(b) {
  if (!b) return '0 GB'
  return (b / 1024 / 1024 / 1024).toFixed(1) + ' GB'
}

async function fetchSyncStatus() {
  try {
    const res = await axios.get('/api/admin/sync/status')
    syncState.value = res.data
  } catch (e) { /* admin belum login / belum jalan */ }
}

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
// ROOM SESSIONS (DURASI PENGGUNAAN)
// ============================================
const sessionRooms = ref([])
const sessionModal = ref(null)  // { mode: 'start'|'extend', room }
const sessionForm = ref({ type: 'duration', minutes: 60, endTime: '', note: '' })
const sessionHistory = ref([])
const historyRoom = ref('')

// Sinkronisasi realtime sesi room: indikator LIVE + auto-refresh saat event room_session
const realtimeLive = ref(false)
const lastSyncAt = ref(null)
let syncTimer = null

// Handler bernama (referensi tersimpan) agar off() hanya menghapus handler milik
// AdminScreen, BUKAN handler global store (room_session/connect/disconnect).
function handleRoomSessionSync() {
  realtimeLive.value = true
  lastSyncAt.value = new Date()
  // Debounce agar tidak spam refresh saat banyak event beruntun
  clearTimeout(syncTimer)
  syncTimer = setTimeout(() => refreshSessionStates(), 300)
}
function handleSocketConnect() { realtimeLive.value = true }
function handleSocketDisconnect() { realtimeLive.value = false }

function setupRealtimeSessionSync() {
  if (!store.socket) return
  store.socket.on('room_session', handleRoomSessionSync)
  store.socket.on('connect', handleSocketConnect)
  store.socket.on('disconnect', handleSocketDisconnect)
}

function formatClock(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function refreshSessionStates() {
  try {
    const res = await axios.get('/api/rooms/active')
    sessionRooms.value = res.data.rooms || []
    realtimeLive.value = store.isConnected
    // Join socket room tiap room agar admin menerima event room_session secara realtime
    if (store.socket?.connected) {
      for (const r of sessionRooms.value) store.socket.emit('join_room', { type: 'admin', room_id: r.name })
    }
  } catch(e) { showToast('❌ Gagal load status sesi') }
}

function openSessionModal(mode, room) {
  sessionModal.value = { mode, room }
  sessionForm.value = { type: 'duration', minutes: mode === 'start' ? 60 : 30, endTime: '', note: '' }
}

async function submitSession() {
  if (!sessionModal.value) return
  const { mode, room } = sessionModal.value
  let payload = {}

  if (sessionForm.value.type === 'duration') {
    const minutes = sessionForm.value.minutes
    if (!minutes || minutes <= 0) { showToast('❌ Isi durasi dengan benar'); return }
    if (mode === 'start') payload.duration_minutes = minutes
    else payload.minutes = minutes
  } else {
    if (!sessionForm.value.endTime) { showToast('❌ Pilih jam berakhir'); return }
    payload.end_time = new Date(sessionForm.value.endTime).toISOString()
  }
  if (mode === 'start') payload.note = sessionForm.value.note || null

  try {
    const url = `/api/admin/rooms/${encodeURIComponent(room.name)}/session/${mode}`
    await axios.post(url, payload)
    showToast(mode === 'start' ? '✅ Sesi dimulai!' : '✅ Sesi diperpanjang!')
    sessionModal.value = null
    refreshSessionStates()
    if (historyRoom.value === room.name) fetchSessionHistory()
  } catch(e) {
    showToast('❌ ' + (e.response?.data?.detail || 'Gagal'))
  }
}

async function endSession(room) {
  if (!confirm(`Akhiri sesi room "${room.name}"?`)) return
  try {
    await axios.post(`/api/admin/rooms/${encodeURIComponent(room.name)}/session/end`)
    showToast('✅ Sesi diakhiri')
    refreshSessionStates()
    if (historyRoom.value === room.name) fetchSessionHistory()
  } catch(e) { showToast('❌ Gagal akhiri sesi') }
}

async function fetchSessionHistory() {
  sessionHistory.value = []
  if (!historyRoom.value) return
  try {
    const res = await axios.get(`/api/admin/rooms/${encodeURIComponent(historyRoom.value)}/sessions`)
    sessionHistory.value = res.data
  } catch(e) { showToast('❌ Gagal load riwayat') }
}

function formatRemaining(secs) {
  secs = Math.max(0, Math.floor(secs || 0))
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  return h > 0 ? `${h}j ${m}m` : `${m} mnt`
}

// Backend menyimpan waktu UTC; string tanpa offset dianggap waktu lokal oleh
// new Date() (geser 7 jam di WIB). Perlakukan string tanpa offset sebagai UTC.
function parseUtcDate(iso) {
  if (!iso) return null
  const s = String(iso)
  const hasOffset = /Z$|[+-]\d{2}:\d{2}$/.test(s)
  const d = new Date(hasOffset ? s : s + 'Z')
  return isNaN(d.getTime()) ? null : d
}

function formatDateTime(iso) {
  const d = parseUtcDate(iso)
  if (!d) return '-'
  return d.toLocaleString('id-ID', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' })
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
  store.fetchPipeline()
  fetchSongs()
  fetchRooms()
  refreshSessionStates()
  setupRealtimeSessionSync()
  fetchSyncStatus()
  syncPollTimer = setInterval(fetchSyncStatus, 15000)
  pipelineTimer = setInterval(() => store.fetchPipeline(), 30000)
})

onUnmounted(() => {
  if (store.socket) {
    store.socket.off('room_session', handleRoomSessionSync)
    store.socket.off('connect', handleSocketConnect)
    store.socket.off('disconnect', handleSocketDisconnect)
  }
  clearTimeout(syncTimer)
  clearInterval(syncPollTimer)
  clearInterval(pipelineTimer)
})

watch(activeTab, (tab) => {
  if (tab === 'rooms') fetchRooms()
  if (tab === 'songs') fetchSongs()
  if (tab === 'sesi') { refreshSessionStates(); sessionHistory.value = []; historyRoom.value = '' }
})

watch(() => store.isConnected, (val) => { realtimeLive.value = val })
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

/* Room Sessions */
.realtime-badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.35rem 0.8rem;
  background: #f1f5f9; color: #94a3b8;
  border-radius: 2rem; font-size: 0.72rem; font-weight: 600;
  transition: all 0.3s;
}
.realtime-badge.live { background: #f0fdf4; color: #16a34a; }
.rt-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; }
.realtime-badge.live .rt-dot { background: #10b981; box-shadow: 0 0 6px rgba(16,185,129,0.7); animation: rtPulse 1.6s infinite; }
.rt-time { font-weight: 500; opacity: 0.8; }
@keyframes rtPulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
.room-busy { border: 2px solid #fecaca; background: #fffafa; }
.session-badge { font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 1rem; background: #f0fdf4; color: #16a34a; }
.session-badge.active { background: #fef2f2; color: #dc2626; }
.btn-session { padding: 0.4rem 0.8rem; border: none; border-radius: 8px; font-weight: 600; font-size: 0.72rem; cursor: pointer; color: white; }
.btn-session.start { background: #10b981; }
.btn-session.extend { background: #f59e0b; }
.btn-session.end { background: #ef4444; }
.radio-row { display: flex; gap: 0.5rem; }
.radio-pill { display: flex; align-items: center; gap: 0.35rem; padding: 0.4rem 0.7rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.8rem; cursor: pointer; }
.radio-pill:has(input:checked) { border-color: #ef4444; background: #fef2f2; color: #ef4444; }
.preset-row { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
.preset-btn { padding: 0.35rem 0.7rem; background: #f1f5f9; border: 2px solid transparent; border-radius: 8px; cursor: pointer; font-size: 0.75rem; font-weight: 600; }
.preset-btn.active { border-color: #ef4444; background: white; color: #ef4444; }
.preset-custom { width: 90px; }
.field-hint { font-size: 0.7rem; color: #94a3b8; margin-top: 0.25rem; display: block; }
.history-card { background: white; border-radius: 12px; padding: 1.25rem; margin-top: 1.5rem; border: 1px solid #f1f5f9; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; gap: 1rem; }
.history-header h3 { font-size: 1rem; }
.history-select { width: 200px; }
.history-empty { color: #94a3b8; font-size: 0.85rem; padding: 0.5rem 0; }

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

/* Sync Bank */
.sync-card { background: white; border-radius: 12px; padding: 1.25rem; border: 1px solid #f1f5f9; margin-bottom: 1rem; }
.sync-card.done { border-color: #bbf7d0; background: #fafffc; }
.sync-card.error { border-color: #fecaca; }
.sync-head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.sync-head h3 { font-size: 1rem; }
.sync-head small { color: #94a3b8; font-weight: 400; }
.sync-badge { padding: 0.3rem 0.8rem; border-radius: 2rem; font-size: 0.7rem; font-weight: 700; background: #f1f5f9; color: #94a3b8; white-space: nowrap; }
.sync-badge.live { background: #eff6ff; color: #2563eb; animation: rtPulse 1.6s infinite; }
.sync-badge.done { background: #f0fdf4; color: #16a34a; }
.sync-badge.err { background: #fef2f2; color: #dc2626; }
.sync-body { display: flex; flex-direction: column; gap: 0.5rem; }
.progress-track { height: 10px; background: #f1f5f9; border-radius: 5px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #2563eb); border-radius: 5px; transition: width 0.8s ease; }
.sync-card.done .progress-fill { background: linear-gradient(90deg, #10b981, #059669); }
.sync-stats { display: flex; gap: 1.25rem; flex-wrap: wrap; font-size: 0.8rem; color: #475569; }
.sync-counting { color: #94a3b8; font-style: italic; }
.progress-fill.counting { background: repeating-linear-gradient(45deg, #93c5fd, #93c5fd 10px, #60a5fa 10px, #60a5fa 20px); animation: rtPulse 1.6s infinite; }
.sync-file { font-size: 0.75rem; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.sync-done-note { font-size: 0.85rem; color: #16a34a; font-weight: 600; }
.sync-disk { font-size: 0.75rem; color: #94a3b8; }
.sync-disk-warn { font-size: 0.8rem; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; padding: 0.4rem 0.7rem; border-radius: 8px; font-weight: 600; }
.sync-err { font-size: 0.75rem; color: #dc2626; }
.sync-empty { font-size: 0.85rem; color: #94a3b8; }

/* Pipeline Transcode */
.pipeline-card.warn { border-color: #fde68a; background: #fffbeb; }
.pipeline-actions { display: flex; gap: 0.4rem; }
.btn-pipe { padding: 0.35rem 0.8rem; border: 1px solid #e2e8f0; border-radius: 8px; background: white; cursor: pointer; font-size: 0.75rem; font-weight: 600; color: #475569; transition: all .15s; }
.btn-pipe:hover:not(:disabled) { border-color: #ef4444; color: #ef4444; background: #fef2f2; }
.btn-pipe:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-pipe.refresh:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }
.pipe-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 0.6rem; margin-top: 0.25rem; }
.pipe-cell { text-align: center; padding: 0.6rem 0.4rem; background: #f8fafc; border: 1px solid #f1f5f9; border-radius: 10px; }
.pipe-cell.bad { border-color: #fca5a5; background: #fef2f2; }
.pc-icon { font-size: 1rem; }
.pc-val { font-size: 1.05rem; font-weight: 800; color: #1e293b; line-height: 1.2; }
.pipe-cell.bad .pc-val { color: #dc2626; }
.pc-lbl { font-size: 0.62rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.4px; margin-top: 0.1rem; }
.pipe-msg { margin-top: 0.6rem; padding: 0.4rem 0.7rem; background: #f0fdf4; color: #16a34a; border-radius: 8px; font-size: 0.78rem; font-weight: 500; }
.pipe-msg.err { background: #fef2f2; color: #dc2626; }

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
