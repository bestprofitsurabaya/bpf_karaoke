<template>
  <div class="operator-app" :class="{ dark: isDark }">
    <!-- CONNECTION BANNER -->
    <transition name="fade">
      <div class="conn-banner" v-if="!store.isConnected" role="alert">
        ⚠️ Koneksi terputus — mencoba menghubungkan ulang...
      </div>
    </transition>

    <!-- TOP BAR -->
    <header class="top-bar">
      <div class="bar-left">
        <img src="/icons/icon-512x512.png" alt="BPF" class="bar-logo" />
        <div class="bar-info">
          <span class="bar-title">BPF Karaoke</span>
          <div class="room-select-wrap" @click.stop="showRoomList = !showRoomList" role="button" tabindex="0" @keydown.enter.prevent="showRoomList = !showRoomList" aria-label="Pilih room">
            <span class="bar-room">{{ store.roomId }}</span>
            <span class="room-arrow">▾</span>
            <div class="room-dropdown" v-if="showRoomList" @click.stop>
              <div v-for="room in rooms" :key="room.id" class="room-option" :class="{ active: room.name === store.roomId }" @click="selectRoom(room)">
                <span>🚪 {{ room.name }}</span>
                <span class="room-meta">
                  <span class="room-busy" :class="{ active: room.session_status === 'active' || room.queue_count > 0 }"></span>
                  <span class="room-cap">👥 {{ room.capacity }}</span>
                  <span class="room-cap">🎵 {{ room.queue_count || 0 }}</span>
                </span>
              </div>
              <div v-if="rooms.length === 0" class="room-empty">Tidak ada room aktif</div>
            </div>
          </div>
        </div>
      </div>
      <div class="bar-center">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input ref="searchInputRef" v-model="store.searchQuery" type="text" placeholder="Cari judul lagu atau penyanyi... ( / )" class="search-input" @input="debouncedSearch" />
          <button v-if="store.searchQuery" class="search-clear" @click="clearSearch" aria-label="Bersihkan pencarian">✕</button>
        </div>
      </div>
      <div class="bar-right">
        <button class="btn-icon" @click="toggleDark" :title="isDark ? 'Mode terang' : 'Mode gelap'" :aria-label="isDark ? 'Aktifkan mode terang' : 'Aktifkan mode gelap'">{{ isDark ? '☀️' : '🌙' }}</button>
        <button class="btn-launch" @click="launchPlayer">📺 Player</button>
        <div class="conn-status">
          <span class="status-dot" :class="{ online: store.isConnected }"></span>
          <span class="conn-text">{{ store.isConnected ? 'Online' : 'Offline' }}</span>
        </div>
        <span class="shortcut-hint"><kbd>/</kbd> cari · <kbd>Space</kbd> play</span>
        <button class="btn-icon" @click="refreshAll" title="Refresh semua data" aria-label="Refresh semua data">🔄</button>
        <router-link to="/" class="btn-icon" title="Beranda" aria-label="Ke beranda">🏠</router-link>
      </div>
    </header>

    <!-- MAIN LAYOUT -->
    <div class="main-layout">
      <!-- LEFT: QUEUE PANEL -->
      <aside class="queue-panel" aria-label="Panel antrian">
        <div class="panel-header">
          <h3>📋 Antrian</h3>
          <div class="header-actions">
            <button v-if="store.waitingQueue.length > 0" class="btn-clear-queue" @click="confirmClearQueue" aria-label="Kosongkan antrian">🗑️</button>
            <span class="queue-badge">{{ store.waitingQueue.length }}</span>
          </div>
        </div>

        <!-- Room Session Timer -->
        <div class="room-session-bar" :class="{ active: store.roomSession?.active, urgent: sessionUrgent }">
          <span class="rs-icon">⏱️</span>
          <div v-if="store.roomSession?.active" class="rs-detail">
            <span class="rs-label">{{ sessionUrgent ? 'SEGERA HABIS!' : 'ROOM TERPAKAI' }}</span>
            <span class="rs-time">Sisa {{ formatRemaining(sessionRemaining) }} · Berakhir {{ formatEndTime(store.roomSession.session?.end_time) }}</span>
            <div class="rs-progress"><div class="rs-fill" :style="{ width: sessionProgress + '%' }"></div></div>
          </div>
          <span v-else class="rs-idle">ROOM KOSONG</span>
        </div>

        <!-- Now Playing -->
        <div class="now-playing-card" v-if="store.currentSong && store.isPlaying">
          <div class="np-art" :style="{ background: thumbGradient() }" aria-hidden="true">🎤</div>
          <div class="np-detail">
            <span class="np-label">SEDANG DIPUTAR</span>
            <div class="np-title">{{ store.currentSong.song_title || '♪' }}</div>
            <div class="np-artist">{{ store.currentSong.song_artist || '' }}</div>
            <div class="ending-soon" v-if="endingSoon" :class="{ pulse: endingSoon }" role="alert">
              ⚠️ Lagu berakhir dalam {{ endingCountdown }} detik!
            </div>
            <div class="np-progress" v-if="playbackProgress.duration > 0">
              <div class="progress-track"><div class="progress-fill" :style="{ width: playbackProgress.percentage + '%' }"></div></div>
              <div class="progress-time"><span>{{ formatTime(playbackProgress.current_time) }}</span><span>{{ formatTime(playbackProgress.duration) }}</span></div>
            </div>
          </div>
          <div class="np-controls">
            <button class="np-btn" @click="togglePlay" :aria-label="store.isPlaying ? 'Pause' : 'Play'">{{ store.isPlaying ? '⏸' : '▶' }}</button>
            <button class="np-btn" @click="skipCurrent" aria-label="Skip">⏭</button>
          </div>
        </div>

        <!-- Queue List -->
        <div class="queue-list">
          <div v-for="(item, index) in store.waitingQueue" :key="item.id"
               class="queue-item" :class="{ 'is-next': index === 0, 'is-dragging': dragIndex === index, 'drop-target': hoverIndex === index && dragIndex !== null }"
               draggable="true"
               @dragstart="onDragStart(index, $event)" @dragover.prevent="hoverIndex = index" @dragend="onDragEnd" @drop="onDrop(index)">
            <div class="drag-handle" title="Seret untuk urut ulang" aria-hidden="true">⋮⋮</div>
            <div class="queue-rank" :class="{ 'rank-next': index === 0 }">{{ index + 1 }}</div>
            <div class="queue-detail">
              <div class="queue-song">#{{ item.song?.id }} {{ item.song?.title || 'Unknown' }}
                <span v-if="item.song?.file_format === 'youtube'" class="yt-tag" title="Lagu YouTube online">▶ YT</span>
              </div>
              <div class="queue-artist">
                {{ item.song?.artist || '-' }}
                <span v-if="item.requester_name" class="guest-badge" :title="`Diminta oleh ${item.requester_name}`">👤 {{ item.requester_name }}</span>
              </div>
            </div>
            <div class="queue-actions">
              <div class="queue-move" aria-label="Pindahkan posisi">
                <button class="move-btn" :disabled="index === 0" @click="moveQueueItem(index, -1)" aria-label="Naikkan posisi">▲</button>
                <button class="move-btn" :disabled="index === store.waitingQueue.length - 1" @click="moveQueueItem(index, 1)" aria-label="Turunkan posisi">▼</button>
              </div>
              <button v-if="index === 0" class="btn-play-now" @click="playNow(item)" aria-label="Putar sekarang">▶</button>
              <button v-else class="btn-queue-next" @click="playQueueNext(item)" title="Putar berikutnya (geser ke posisi 2)" aria-label="Putar berikutnya">⏩</button>
              <button class="btn-remove" @click="confirmRemove(item)" aria-label="Hapus dari antrian">✕</button>
            </div>
          </div>
          <div v-if="store.waitingQueue.length === 0" class="queue-empty">
            <div class="empty-art">🎶</div>
            <p>Antrian kosong</p>
            <p class="empty-sub">Klik <b>+</b> pada lagu untuk menambah</p>
          </div>
        </div>

        <!-- Batch Add Bar -->
        <div class="batch-bar" v-if="selectedSongs.size > 0">
          <span class="batch-count">{{ selectedSongs.size }} lagu dipilih</span>
          <button class="btn-batch-select-all" @click="selectAll">☑ Semua di halaman ini</button>
          <button class="btn-batch-add" @click="batchAddToQueue">+ Tambah ke Antrian</button>
          <button class="btn-batch-clear" @click="selectedSongs.clear()">Batal</button>
        </div>

        <!-- Pipeline Sync → Transcode → Hapus Sumber -->
        <div class="pipeline-bar" :class="pipelineTone" :title="pipelineTitle">
          <div class="pipe-head">
            <span class="pipe-title">🛠 Pipeline</span>
            <span class="pipe-live" :class="{ on: !!store.pipeline }">●</span>
          </div>
          <div class="pipe-cells">
            <div class="pipe-cell" :title="store.pipeline?.sync?.last_error || 'Fase sinkronisasi dari XP'">
              <span class="pc-icon">{{ syncIcon }}</span>
              <span class="pc-val">{{ store.pipeline?.sync?.phase || '–' }}</span>
              <span class="pc-label">Sync</span>
            </div>
            <div class="pipe-cell" title="Antrian transcode di Celery">
              <span class="pc-icon">🔄</span>
              <span class="pc-val">{{ fmtCount(store.pipeline?.transcode?.queue) }}</span>
              <span class="pc-label">Antrian</span>
            </div>
            <div class="pipe-cell" title="MP4 hasil transcode yang siap diputar">
              <span class="pc-icon">🎞️</span>
              <span class="pc-val">{{ fmtCount(store.pipeline?.transcode?.mp4_ready) }}</span>
              <span class="pc-label">MP4 siap</span>
            </div>
            <div class="pipe-cell" title="Sumber master (mpg/avi/dll) yang belum di-transcode">
              <span class="pc-icon">💿</span>
              <span class="pc-val">{{ fmtCount(store.pipeline?.transcode?.sources) }}</span>
              <span class="pc-label">Sumber</span>
            </div>
            <div class="pipe-cell" :class="{ warn: diskLow }" title="Ruang disk bebas partisi media">
              <span class="pc-icon">💾</span>
              <span class="pc-val">{{ fmtGB(store.pipeline?.disk?.free) }}</span>
              <span class="pc-label">Disk bebas</span>
            </div>
            <div class="pipe-cell" :class="{ warn: store.pipeline && !store.pipeline.youtube?.configured }" title="API key YouTube terpasang?">
              <span class="pc-icon">▶️</span>
              <span class="pc-val">{{ store.pipeline?.youtube?.configured ? 'ON' : 'OFF' }}</span>
              <span class="pc-label">YouTube</span>
            </div>
          </div>
        </div>

        <div class="queue-footer">
          <div class="stat-pill"><span>🎵</span><strong>{{ store.stats.total_songs || 0 }}</strong><em>Lagu</em></div>
          <div class="stat-pill"><span>▶️</span><strong>{{ store.stats.total_plays || 0 }}</strong><em>Putar</em></div>
          <div class="stat-pill"><span>📋</span><strong>{{ store.stats.queue_today || 0 }}</strong><em>Hari ini</em></div>
        </div>
      </aside>

      <!-- CENTER: SONG BROWSER -->
      <main class="browser-panel" aria-label="Pencarian lagu">
        <div class="browser-tabs" role="tablist">
          <button @click="setTab('all')" class="tab-btn" :class="{ active: activeTab === 'all' }" role="tab" :aria-selected="activeTab === 'all'">🎵 Semua Lagu</button>
          <button @click="setTab('favorites')" class="tab-btn" :class="{ active: activeTab === 'favorites' }" role="tab" :aria-selected="activeTab === 'favorites'">⭐ Favorites ({{ favoriteSongs.length }})</button>
          <button @click="setTab('history')" class="tab-btn" :class="{ active: activeTab === 'history' }" role="tab" :aria-selected="activeTab === 'history'">🕐 History</button>
        </div>

        <!-- Filter + Sort Strip (hanya tab Semua Lagu) -->
        <div class="filter-strip" v-if="activeTab === 'all'">
          <button class="filter-chip" :class="{ active: store.selectedGenre === null }" @click="setFilter(null)">
            <span class="chip-emoji">🔥</span><span class="chip-label">Semua</span>
          </button>
          <button v-for="g in genreChips" :key="g.genre" class="filter-chip" :class="{ active: store.selectedGenre === g.genre }" @click="setFilter(g.genre)">
            <span class="chip-emoji">{{ genreEmoji(g.genre) }}</span><span class="chip-label">{{ g.genre }}</span><span class="chip-count">{{ g.count }}</span>
          </button>
          <button class="filter-chip yt-chip" :class="{ active: store.youtubeMode }" @click="toggleYoutubeMode" :title="store.youtubeMode ? 'Kembali ke lagu lokal' : 'Cari lagu yang tidak ada di database via YouTube'" aria-pressed="store.youtubeMode">
            <span class="chip-emoji">▶️</span><span class="chip-label">YouTube</span>
            <span class="yt-online" v-if="store.youtubeMode">●</span>
          </button>
          <div class="sort-wrap">
            <label class="sort-label" for="sort-select">Urut:</label>
            <select id="sort-select" :value="sortKey" @change="onSortChange" class="sort-select" aria-label="Urutkan lagu">
              <option value="title">Judul A-Z</option>
              <option value="artist">Artis A-Z</option>
              <option value="plays">Paling sering diputar</option>
              <option value="newest">Terbaru</option>
            </select>
            <button class="btn-add-all" @click="confirmAddAll" title="Tambahkan semua lagu hasil filter ke antrian">➕ Semua hasil</button>
          </div>
        </div>

        <!-- ALL SONGS (lokal) -->
        <div class="song-grid" v-if="activeTab === 'all' && !(store.youtubeMode && store.searchQuery)">
          <template v-if="store.fetchingSongs && store.songs.length === 0">
            <div v-for="i in 6" :key="'sk' + i" class="skeleton-card">
              <div class="sk-thumb"></div>
              <div class="sk-lines"><div class="sk-line w-75"></div><div class="sk-line w-50"></div></div>
            </div>
          </template>
          <SongCard v-for="song in store.songs" :key="song.id"
                    :song="song"
                    :selected="selectedSongs.has(song.id)"
                    :in-queue="isInQueue(song.id)"
                    :favorited="favoriteIds.has(song.id)"
                    @toggle-select="toggleSelect"
                    @toggle-favorite="toggleFavorite"
                    @add="addToQueue"
                    @play-next="playNext" />
          <div v-if="!store.fetchingSongs && store.songs.length === 0" class="browser-empty">
            <span class="empty-emoji">🔍</span><h3>Tidak ditemukan</h3>
            <p>Coba kata kunci lain atau ubah filter genre</p>
          </div>
        </div>
        <div class="load-more-row" v-if="activeTab === 'all' && !(store.youtubeMode && store.searchQuery) && store.hasMoreSongs && store.songs.length > 0">
          <button class="btn-load-more" @click="loadMore">Muat lebih banyak ({{ store.songs.length }} dimuat)</button>
        </div>

        <!-- YOUTUBE RESULTS (lagu tidak tersedia offline) -->
        <div class="yt-panel" v-if="activeTab === 'all' && store.youtubeMode && store.searchQuery">
          <div v-if="store.youtubeSearching" class="yt-loading">
            <div class="spinner-ring"></div><p>Mencari di YouTube...</p>
          </div>
          <div v-else-if="store.youtubeError" class="yt-error">
            <span class="empty-emoji">⚠️</span><h3>YouTube tidak tersedia</h3><p>{{ store.youtubeError }}</p>
          </div>
          <div v-else-if="store.youtubeResults.length === 0" class="browser-empty">
            <span class="empty-emoji">▶️</span><h3>Tidak ditemukan di YouTube</h3><p>Coba kata kunci lain</p>
          </div>
          <template v-else>
            <div class="yt-header-row">
              <span class="yt-note">🎬 Hasil dari YouTube (diputar online via embed)</span>
            </div>
            <div v-for="r in store.youtubeResults" :key="r.youtube_id" class="yt-item">
              <img :src="r.thumbnail" :alt="r.title" class="yt-thumb" loading="lazy" />
              <div class="yt-detail">
                <div class="yt-title">{{ r.title }}</div>
                <div class="yt-artist">{{ r.artist }}<span v-if="r.duration" class="yt-dur">· {{ formatDuration(r.duration) }}</span></div>
              </div>
              <button class="card-add" @click="addYouTube(r)" :title="`Tambah ${r.title}`" aria-label="Tambah ke antrian">+</button>
            </div>
          </template>
        </div>

        <!-- FAVORITES -->
        <div class="song-grid" v-if="activeTab === 'favorites'">
          <SongCard v-for="fav in favoriteSongs" :key="fav.song_id"
                    :song="fav.song"
                    :selected="selectedSongs.has(fav.song_id)"
                    :in-queue="isInQueue(fav.song_id)"
                    :favorited="true"
                    @toggle-select="toggleSelect"
                    @toggle-favorite="toggleFavorite"
                    @add="addToQueue"
                    @play-next="playNext" />
          <div v-if="favoriteSongs.length === 0" class="browser-empty">
            <span class="empty-emoji">⭐</span><h3>Belum ada favorit</h3>
            <p>Klik ☆ pada lagu untuk menandai favorit</p>
          </div>
        </div>

        <!-- HISTORY (grouped) -->
        <div class="history-list" v-if="activeTab === 'history'">
          <div v-for="group in historyGroups" :key="group.label" class="history-group">
            <div class="history-date">{{ group.label }}</div>
            <div v-for="h in group.items" :key="h.id" class="history-item">
              <div class="history-time">{{ formatDate(h.played_at) }}</div>
              <div class="history-info">
                <div class="history-title">#{{ h.song_id }} {{ h.title || 'Unknown' }}</div>
                <div class="history-artist">{{ h.artist || '-' }}</div>
              </div>
              <button class="card-add" @click="addToQueueById(h.song_id)" v-if="h.song_id" aria-label="Tambah ke antrian">+</button>
            </div>
          </div>
          <div v-if="history.length === 0" class="browser-empty">
            <span class="empty-emoji">🕐</span><h3>Belum ada history</h3>
            <p>Riwayat lagu yang diputar akan tampil di sini</p>
          </div>
        </div>
      </main>

      <!-- RIGHT: CONTROL PANEL -->
      <ControlPanel
        :is-playing="store.isPlaying"
        :has-song="!!store.currentSong"
        :key-shift="store.keyShift"
        :vocal-mode="store.vocalMode"
        :volume="store.currentVolume"
        :vocal-removing="vocalRemoving"
        @toggle-play="togglePlay"
        @skip="skipCurrent"
        @change-key="changeKey"
        @toggle-vocal="store.toggleVocal"
        @vocal-remove="triggerVocalRemove"
        @set-volume="store.setVolume"
        @toggle-mute="toggleMute" />
    </div>

    <!-- TOASTS -->
    <div class="toast-stack" aria-live="polite">
      <transition-group name="toast">
        <div v-for="t in toasts" :key="t.id" class="operator-toast" :class="`toast-${t.type}`">
          <span class="toast-icon">{{ t.icon }}</span>
          <span>{{ t.message }}</span>
        </div>
      </transition-group>
    </div>

    <!-- CONFIRM -->
    <div class="confirm-overlay" v-if="confirm.show" @click.self="confirm.show = false">
      <div class="confirm-card">
        <span class="confirm-icon">⚠️</span>
        <p>{{ confirm.message }}</p>
        <div class="confirm-actions">
          <button @click="confirm.show = false" class="btn-cancel">Batal</button>
          <button @click="confirm.onConfirm" class="btn-danger">{{ confirm.btnText || 'Hapus' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useKaraokeStore } from '@/stores/karaoke'
import { formatRemaining, formatEndTime, thumbGradient, formatDuration } from '@/utils/helpers'
import SongCard from '@/components/operator/SongCard.vue'
import ControlPanel from '@/components/operator/ControlPanel.vue'
import axios from 'axios'

const store = useKaraokeStore()
const PAGE = 60

// ========== UI STATE ==========
const toasts = ref([])
let toastId = 0
const confirm = ref({ show: false, message: '', onConfirm: () => {}, btnText: '' })
const showRoomList = ref(false)
const rooms = ref([])
const dragIndex = ref(null)
const hoverIndex = ref(null)
const activeTab = ref('all')
const favorites = ref([])
const favoriteIds = ref(new Set())
const history = ref([])
const selectedSongs = ref(new Set())
const endingSoon = ref(false)
const endingCountdown = ref(15)
const sortKey = ref('title')
const searchInputRef = ref(null)
const vocalRemoving = ref(false)
let vocalPollTimer = null
const lastVolume = ref(store.currentVolume)
const isDark = ref(localStorage.getItem('karaoke_dark') === '1')

const playbackProgress = reactive({ current_time: 0, duration: 0, percentage: 0, song_id: null })

// ========== PIPELINE (sync → transcode → hapus sumber) ==========
let pipelineTimer = null
const pipelineTone = computed(() => {
  const p = store.pipeline
  if (!p) return 'off'
  if ((p.transcode?.stale_parts || 0) > 0) return 'warn'
  if (diskLow.value) return 'warn'
  if (p.sync?.phase === 'error') return 'warn'
  return 'ok'
})
const diskLow = computed(() => {
  const free = store.pipeline?.disk?.free
  return typeof free === 'number' && free > 0 && free < 50e9
})
const syncIcon = computed(() => {
  const p = store.pipeline?.sync
  if (!p || !p.available) return '⏸'
  if (p.phase === 'done') return '✅'
  if (p.phase === 'error') return '⚠️'
  if (p.phase === 'syncing') return '🔄'
  return '⏸'
})
const pipelineTitle = computed(() => {
  const p = store.pipeline
  if (!p) return 'Pipeline belum dimuat'
  const parts = []
  if ((p.transcode?.stale_parts || 0) > 0) parts.push(`⚠️ ${p.transcode.stale_parts} .part basi!`)
  if (diskLow.value) parts.push('⚠️ Disk hampir penuh!')
  if (p.sync?.phase === 'error') parts.push(`Sync error: ${p.sync.last_error || '-'}`)
  if ((p.sync?.hang_dirs || []).length > 0) parts.push(`Folder hang: ${p.sync.hang_dirs.join(', ')}`)
  if ((p.sync?.errors || 0) > 0) parts.push(`${p.sync.errors} error sync`)
  if (p.transcode?.queue != null) parts.push(`${p.transcode.queue} antrian transcode · ${p.transcode.pending ?? '-'} pending`)
  return parts.join(' | ') || 'Pipeline sehat'
})
function fmtCount(n) { if (n == null || isNaN(n)) return '–'; return n >= 1000 ? (n / 1000).toFixed(1).replace('.', ',') + 'K' : String(n) }
function fmtGB(n) { if (n == null || isNaN(n)) return '–'; return (n / 1e9).toFixed(0) + ' GB' }

// ========== ROOM SESSION ==========
const sessionNow = ref(Date.now())
let sessionTimer = null

const sessionRemaining = computed(() => {
  const s = store.roomSession?.session
  if (!store.roomSession?.active || !s?.end_time) return 0
  const end = new Date(s.end_time).getTime()
  return Math.max(0, Math.floor((end - sessionNow.value) / 1000))
})
const sessionUrgent = computed(() => sessionRemaining.value > 0 && sessionRemaining.value <= 300)
const sessionProgress = computed(() => {
  const s = store.roomSession?.session
  if (!store.roomSession?.active || !s) return 0
  const start = new Date(s.started_at).getTime()
  const end = new Date(s.end_time).getTime()
  const total = end - start
  if (total <= 0) return 0
  return Math.max(0, Math.min(100, ((sessionNow.value - start) / total) * 100))
})

// ========== GENRES & SORT ==========
const genreEmojiMap = {
  'Pop Indonesia': '🇮🇩', 'Dangdut': '🎶', 'Barat': '🌍', 'K-Pop': '🇰🇷',
  'Mandarin': '🇨🇳', 'Rock': '🎸', 'Jazz': '🎷', 'Religi': '🕌', 'Unknown': '❓'
}
function genreEmoji(g) { return genreEmojiMap[g] || '🎵' }

const genreChips = computed(() => (store.genres || []).slice(0, 10))

const favoriteSongs = computed(() => favorites.value.filter(f => f.song))

const historyGroups = computed(() => {
  const groups = []
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1)
  for (const h of history.value) {
    const d = new Date(h.played_at)
    const day = new Date(d); day.setHours(0, 0, 0, 0)
    let label
    if (day.getTime() === today.getTime()) label = 'Hari Ini'
    else if (day.getTime() === yesterday.getTime()) label = 'Kemarin'
    else label = d.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'short' })
    const last = groups[groups.length - 1]
    if (last && last.label === label) last.items.push(h)
    else groups.push({ label, items: [h] })
  }
  return groups
})

// ========== TOAST ==========
function showToast(message, type = 'info', duration = 2600) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' }
  const id = ++toastId
  toasts.value.push({ id, message, type, icon: icons[type] || 'ℹ️' })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, duration)
}

// ========== SEARCH & FILTER ==========
let searchTimer
function fetchSongs() { store.fetchSongs({ limit: PAGE, sort: sortKey.value }) }
function clearSearch() {
  store.searchQuery = ''
  if (store.youtubeMode) store.clearYoutube()
  else fetchSongs()
}
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (store.youtubeMode) store.youtubeSearch(store.searchQuery)
    else fetchSongs()
  }, 350)
}
function toggleYoutubeMode() {
  store.youtubeMode = !store.youtubeMode
  if (store.youtubeMode) {
    store.clearYoutube()
    if (store.searchQuery) store.youtubeSearch(store.searchQuery)
    else showToast('💡 Ketik judul/artis, lalu Enter untuk cari di YouTube', 'info')
  } else {
    fetchSongs()
  }
}
async function addYouTube(r) {
  const inQ = store.waitingQueue.some(q => q.song?.file_path === `yt:${r.youtube_id}`)
  if (inQ) { showToast(`"${r.title}" sudah di antrian`, 'warning'); return }
  const res = await store.addYouTubeToQueue(r)
  if (res) showToast(`✅ "${res.title}" ditambahkan!`, 'success')
  else showToast('❌ Gagal menambah lagu YouTube', 'error')
}
function setFilter(genre) {
  store.selectedGenre = store.selectedGenre === genre ? null : genre
  fetchSongs()
}
function onSortChange(e) {
  sortKey.value = e.target.value
  fetchSongs()
}
function isInQueue(songId) { return store.waitingQueue.some(q => q.song_id === songId) }
function setTab(tab) { activeTab.value = tab }

// ========== QUEUE ==========
async function addToQueue(song) {
  if (isInQueue(song.id)) { showToast(`"${song.title}" sudah di antrian`, 'warning'); return }
  const ok = await store.addToQueue(song.id)
  if (ok) showToast(`✅ "${song.title}" ditambahkan!`, 'success')
  else showToast('❌ Gagal menambah lagu', 'error')
}
async function addToQueueById(songId) {
  const ok = await store.addToQueue(songId)
  if (ok) showToast('✅ Ditambahkan!', 'success')
}
async function playNext(song) {
  if (isInQueue(song.id)) { showToast(`"${song.title}" sudah di antrian`, 'warning'); return }
  const ok = await store.playNext(song.id)
  if (ok) showToast(`⏩ "${song.title}" akan diputar berikutnya`, 'success')
  else showToast('❌ Gagal menambahkan lagu', 'error')
}
function playNow(item) { store.playSong(item.song_id, item.id) }
function playQueueNext(item) {
  // Geser item yang SUDAH di antrian ke posisi 0 (waitingQueue[0] = lagu
  // yang akan diputar SETELAH lagu sekarang selesai) — Play Next untuk lagu
  // yang sudah ditambahkan. Item lain otomatis bergeser mundur.
  const order = store.waitingQueue.map(q => q.id)
  const idx = order.indexOf(item.id)
  if (idx === -1) return
  order.splice(idx, 1)
  order.unshift(item.id)
  if (store.socket?.connected) {
    store.socket.emit('reorder_queue', {
      room_id: store.roomId,
      queue_ids: order,
      revision: store.queueRevision
    })
    showToast(`⏩ "${item.song?.title || ''}" diputar berikutnya`, 'success')
  } else {
    showToast('⚠️ Koneksi realtime terputus', 'warning')
  }
}
function skipCurrent() { store.skipSong(store.currentSong?.queue_id) }
function togglePlay() { store.isPlaying ? store.pauseSong() : store.resumeSong() }
function changeKey(delta) { store.changeKey(Math.max(-12, Math.min(12, store.keyShift + delta))) }
function toggleMute() {
  if (store.currentVolume > 0) { lastVolume.value = store.currentVolume; store.setVolume(0) }
  else store.setVolume(lastVolume.value || 80)
}
function confirmRemove(item) {
  confirm.value = { show: true, message: `Hapus "${item.song?.title || 'lagu ini'}" dari antrian?`, btnText: 'Hapus', onConfirm: () => { store.removeFromQueue(item.id); confirm.value.show = false; showToast('🗑️ Dihapus dari antrian', 'info') } }
}
function confirmClearQueue() {
  confirm.value = { show: true, message: `Hapus SEMUA antrian (${store.waitingQueue.length} lagu)?`, btnText: 'Kosongkan', onConfirm: () => { store.socket?.emit('clear_queue', { room_id: store.roomId }); confirm.value.show = false; showToast('🗑️ Antrian dikosongkan', 'info') } }
}

// ========== REORDER (drag & drop + tombol naik/turun) ==========
function emitReorder(list) {
  store.socket?.emit('reorder_queue', {
    room_id: store.roomId,
    queue_ids: list.map(q => q.id),
    revision: store.queueRevision
  }, (res) => {
    if (res && res.ok === false && res.reason === 'stale') {
      // Antrian berubah sejak operator menarik urutan -> muat ulang
      showToast('⚠️ Antrian berubah, urutan dimuat ulang', 'warning')
      store.fetchQueue()
    } else if (res && res.ok) {
      showToast('↕️ Urutan disimpan', 'success')
    }
  })
}
function moveQueueItem(index, dir) {
  const newIndex = index + dir
  if (newIndex < 0 || newIndex >= store.waitingQueue.length) return
  const arr = [...store.waitingQueue]
  const [item] = arr.splice(index, 1)
  arr.splice(newIndex, 0, item)
  emitReorder(arr)
}
function onDragStart(index, event) {
  dragIndex.value = index
  hoverIndex.value = index
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}
function onDragEnd() { dragIndex.value = null; hoverIndex.value = null }
function onDrop(targetIndex) {
  if (dragIndex.value === null || dragIndex.value === targetIndex) { onDragEnd(); return }
  const arr = [...store.waitingQueue]
  const [item] = arr.splice(dragIndex.value, 1)
  arr.splice(targetIndex, 0, item)
  onDragEnd()
  emitReorder(arr)
}

// ========== BATCH SELECT ==========
function toggleSelect(song) {
  const s = new Set(selectedSongs.value)
  s.has(song.id) ? s.delete(song.id) : s.add(song.id)
  selectedSongs.value = s
}
function selectAll() {
  selectedSongs.value = new Set(store.songs.map(s => s.id))
}
async function batchAddToQueue() {
  const ids = Array.from(selectedSongs.value)
  if (ids.length === 0) return
  try {
    const res = await axios.post(`/api/queue/batch?room_id=${store.roomId}`, ids)
    showToast(`✅ ${res.data.added || ids.length} lagu ditambahkan!`, 'success')
    selectedSongs.value = new Set()
    store.fetchQueue()
  } catch (e) { showToast('❌ Gagal menambah batch', 'error') }
}

// ========== FAVORITES ==========
async function toggleFavorite(song) {
  try {
    const res = await axios.post(`/api/favorites/${song.id}`)
    if (res.data.status === 'added') { favoriteIds.value.add(song.id); showToast('⭐ Ditambahkan ke favorit', 'success') }
    else { favoriteIds.value.delete(song.id); showToast('☆ Dihapus dari favorit', 'info') }
    fetchFavorites()
  } catch (e) { showToast('❌ Gagal update favorit', 'error') }
}
async function fetchFavorites() {
  try {
    const res = await axios.get('/api/favorites')
    favorites.value = res.data
    favoriteIds.value = new Set(res.data.map(f => f.song_id))
  } catch (e) { /* silent */ }
}
async function fetchHistory() {
  try {
    const res = await axios.get(`/api/history/${store.roomId}`)
    history.value = res.data
  } catch (e) { /* silent */ }
}

// ========== KEYBOARD (global agar tetap aktif) ==========
function onWindowKeydown(e) {
  const tag = e.target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.code === 'Space') { e.preventDefault(); togglePlay() }
  else if (e.code === 'Escape') { e.preventDefault(); if (store.isPlaying) store.pauseSong() }
  else if (e.code === 'ArrowRight') { e.preventDefault(); skipCurrent() }
  else if (e.key === '/') { e.preventDefault(); searchInputRef.value?.focus() }
}

// ========== PROGRESS & ENDING SOON ==========
function setupProgressListener() {
  if (!store.socket) return
  store.socket.on('playback_progress', (data) => {
    // Abaikan progress dari lagu lain (stale)
    if (data.song_id && store.currentSong?.song_id && data.song_id !== store.currentSong.song_id) return
    Object.assign(playbackProgress, data)
    const remaining = (data.duration || 0) - (data.current_time || 0)
    if (remaining > 0 && remaining <= 15) {
      endingSoon.value = true
      endingCountdown.value = Math.ceil(remaining)
    } else {
      endingSoon.value = false
    }
  })
}

// Reset progress saat berganti lagu / berhenti
watch(() => store.currentSong?.song_id, (newId) => {
  if (!newId) {
    Object.assign(playbackProgress, { current_time: 0, duration: 0, percentage: 0, song_id: null })
    endingSoon.value = false
    return
  }
  Object.assign(playbackProgress, { current_time: 0, duration: 0, percentage: 0, song_id: newId })
  endingSoon.value = false
})

// Saat sesi habis (menit sisa 0) -> refetch agar server menutup sesi expired
watch(sessionRemaining, (val, old) => {
  if (val === 0 && old > 0) store.fetchRoomSession()
})

// ========== DARK MODE ==========
function toggleDark() {
  isDark.value = !isDark.value
  localStorage.setItem('karaoke_dark', isDark.value ? '1' : '0')
  store.isDarkMode = isDark.value
}

// ========== HELPERS ==========
function formatTime(s) { if (!s || isNaN(s)) return '0:00'; const m = Math.floor(s / 60); return `${m}:${Math.floor(s % 60).toString().padStart(2, '0')}` }
function formatDate(d) { if (!d) return ''; const t = new Date(d); return t.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) }
function launchPlayer() { window.open(`${window.location.origin}/player?screen=2&room=${encodeURIComponent(store.roomId)}`, '_blank', 'width=1280,height=720') }

// ========== ROOMS ==========
async function fetchRooms() {
  try {
    const res = await axios.get('/api/rooms/active')
    rooms.value = res.data.rooms || res.data
    ensureValidRoom()
  } catch (e) { /* silent */ }
}
function ensureValidRoom() {
  const valid = rooms.value.some(r => r.name === store.roomId)
  if (!valid && rooms.value.length > 0) selectRoom(rooms.value[0])
}
function selectRoom(room) {
  store.setRoomId(room.name)
  showRoomList.value = false
  store.fetchRoomSession()
  fetchHistory()
  showToast('📍 ' + room.name, 'info')
}
function refreshAll() {
  fetchSongs()
  store.fetchGenres(); store.fetchQueue(); store.fetchStats(); store.fetchPipeline()
  store.fetchRoomSession(); fetchRooms(); fetchFavorites(); fetchHistory()
  showToast('🔄 Data diperbarui', 'info')
}
function loadMore() {
  store.fetchSongs({ limit: PAGE, offset: store.songs.length, append: true, sort: sortKey.value })
}
function confirmAddAll() {
  const label = store.searchQuery ? `"${store.searchQuery}"` : (store.selectedGenre || 'semua lagu')
  confirm.value = {
    show: true,
    message: `Tambahkan SEMUA lagu hasil filter ${label} ke antrian?`,
    btnText: 'Tambah',
    onConfirm: async () => {
      confirm.value.show = false
      const res = await store.addAllFiltered()
      if (res) {
        const dup = res.skipped_duplicates ? ` (${res.skipped_duplicates} sudah ada)` : ''
        const truncated = res.matched >= 500 ? ` — ${res.matched} hasil, hanya 500 pertama` : ''
        showToast(`✅ ${res.added} lagu ditambahkan${dup}${truncated}`, 'success')
      } else {
        showToast('❌ Gagal menambah semua hasil', 'error')
      }
    }
  }
}

// ========== AI VOCAL REMOVE ==========
async function triggerVocalRemove() {
  if (!store.currentSong?.song_id) return
  vocalRemoving.value = true
  try {
    const res = await axios.post(`/api/tasks/vocal-remove/${store.currentSong.song_id}?method=ffmpeg`)
    showToast('🎵 Vocal removal dimulai! Task: ' + res.data.task_id?.slice(0, 8), 'info')
    pollVocalTask(res.data.task_id)
  } catch (e) {
    showToast('❌ Gagal memulai vocal removal', 'error')
    vocalRemoving.value = false
  }
}
function pollVocalTask(taskId) {
  clearInterval(vocalPollTimer)
  let tries = 0
  vocalPollTimer = setInterval(async () => {
    tries++
    try {
      const res = await axios.get(`/api/tasks/status/${taskId}`)
      if (res.data.ready) {
        clearInterval(vocalPollTimer); vocalPollTimer = null
        vocalRemoving.value = false
        if (res.data.successful) showToast('✅ Vocal removal selesai!', 'success')
        else showToast('❌ Vocal removal gagal', 'error')
      } else if (tries >= 60) {
        clearInterval(vocalPollTimer); vocalPollTimer = null
        vocalRemoving.value = false
        showToast('⏳ Vocal removal berjalan di background...', 'info')
      }
    } catch (e) {
      clearInterval(vocalPollTimer); vocalPollTimer = null
      vocalRemoving.value = false
      showToast('⚠️ Tidak dapat cek status task', 'warning')
    }
  }, 3000)
}

// ========== LIFECYCLE ==========
onMounted(() => {
  store.setScreenType('operator')
  fetchSongs(); store.fetchGenres(); store.fetchQueue(); store.fetchStats(); store.fetchPipeline()
  store.fetchRoomSession()
  fetchRooms(); fetchFavorites(); fetchHistory()
  setupProgressListener()
  window.addEventListener('keydown', onWindowKeydown)
  sessionTimer = setInterval(() => { sessionNow.value = Date.now() }, 1000)
  pipelineTimer = setInterval(() => store.fetchPipeline(), 30000)
})

onUnmounted(() => {
  if (store.socket) store.socket.off('playback_progress')
  window.removeEventListener('keydown', onWindowKeydown)
  clearInterval(vocalPollTimer)
  clearInterval(sessionTimer)
  clearInterval(pipelineTimer)
})
</script>

<style scoped>
/* ===== THEME VARIABLES ===== */
.operator-app {
  --bg: #f1f5f9;
  --surface: #ffffff;
  --surface-2: #f8fafc;
  --surface-3: #f1f5f9;
  --border: #e2e8f0;
  --border-soft: #f1f5f9;
  --text: #1e293b;
  --muted: #64748b;
  --muted-2: #94a3b8;
  --faint: #cbd5e1;
  --hover: #f1f5f9;
  --red-soft: #fef2f2;
  --red-border: #fecaca;
  --blue-soft: #eff6ff;
  --blue-border: #bfdbfe;
  --red: #ef4444;
  --blue: #3b82f6;
  --green: #10b981;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
}
.operator-app.dark {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-2: #243041;
  --surface-3: #334155;
  --border: #334155;
  --border-soft: #293548;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --muted-2: #64748b;
  --faint: #475569;
  --hover: #334155;
  --red-soft: rgba(239,68,68,0.14);
  --red-border: #7f1d1d;
  --blue-soft: rgba(59,130,246,0.14);
  --blue-border: #1e3a8a;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.4);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.4);
}

.operator-app {
  height: 100vh; display: flex; flex-direction: column;
  background: var(--bg); font-family: 'Inter', sans-serif;
  color: var(--text); overflow: hidden;
}

/* ===== CONNECTION BANNER ===== */
.conn-banner {
  padding: 0.4rem 1rem; text-align: center;
  background: linear-gradient(90deg, #dc2626, #f59e0b);
  color: #fff; font-size: 0.75rem; font-weight: 600;
  z-index: 30;
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ===== TOP BAR ===== */
.top-bar {
  display: flex; align-items: center;
  padding: 0.5rem 1rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  gap: 1rem; z-index: 20;
}
.bar-left { display: flex; align-items: center; gap: 0.5rem; min-width: 180px; position: relative; }
.bar-logo { width: 32px; height: 32px; border-radius: 8px; object-fit: contain; }
.bar-title { font-weight: 700; font-size: 0.85rem; display: block; }
.room-select-wrap {
  position: relative; display: flex; align-items: center; gap: 0.25rem;
  cursor: pointer; padding: 0.25rem 0.6rem; border-radius: 8px;
  background: var(--surface-3); transition: background 0.15s;
}
.room-select-wrap:hover { background: var(--hover); }
.bar-room { font-size: 0.7rem; color: var(--muted); font-weight: 600; }
.room-arrow { font-size: 0.55rem; color: var(--muted-2); }
.room-dropdown {
  position: absolute; top: calc(100% + 6px); left: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px; box-shadow: var(--shadow-md);
  z-index: 200; min-width: 240px; overflow: hidden;
  animation: scaleIn 0.15s ease-out;
}
.room-option { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; padding: 0.6rem 0.85rem; cursor: pointer; font-size: 0.8rem; }
.room-option:hover { background: var(--hover); }
.room-option.active { background: var(--red-soft); color: var(--red); font-weight: 600; }
.room-meta { display: flex; align-items: center; gap: 0.4rem; }
.room-busy { width: 7px; height: 7px; border-radius: 50%; background: var(--green); }
.room-busy.active { background: var(--red); animation: pulse 1.2s infinite; }
.room-cap { font-size: 0.6rem; color: var(--muted-2); }
.room-empty { padding: 0.75rem; font-size: 0.75rem; color: var(--muted-2); text-align: center; }
.bar-center { flex: 1; }
.search-box { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 0.75rem; z-index: 1; }
.search-input {
  width: 100%; padding: 0.55rem 2rem;
  border: 2px solid var(--border);
  border-radius: 10px; font-size: 0.85rem;
  background: var(--surface-2); color: var(--text);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-input:focus { outline: none; border-color: var(--red); box-shadow: 0 0 0 3px rgba(239,68,68,0.12); }
.search-input::placeholder { color: var(--muted-2); }
.search-clear { position: absolute; right: 0.5rem; background: var(--surface-3); border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; color: var(--muted); }
.bar-right { display: flex; align-items: center; gap: 0.5rem; font-size: 0.7rem; color: var(--muted); }
.btn-launch { padding: 0.35rem 0.75rem; background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff; border: none; border-radius: 8px; font-weight: 600; font-size: 0.75rem; cursor: pointer; transition: transform 0.1s, opacity 0.2s; }
.btn-launch:hover { opacity: 0.9; }
.btn-launch:active { transform: scale(0.96); }
.conn-status { display: flex; align-items: center; gap: 0.3rem; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.online { background: var(--green); box-shadow: 0 0 6px rgba(16,185,129,0.6); }
.status-dot:not(.online) { background: var(--red); animation: pulse 1.2s infinite; }
.conn-text { font-size: 0.6rem; color: var(--muted-2); }
.shortcut-hint { font-size: 0.58rem; color: var(--faint); display: flex; align-items: center; gap: 0.2rem; }
kbd {
  background: var(--surface-3); border: 1px solid var(--border);
  border-bottom-width: 2px; border-radius: 4px;
  padding: 0.05rem 0.35rem; font-size: 0.55rem; font-weight: 700;
  font-family: 'Inter', sans-serif; color: var(--muted);
}
.btn-icon { background: none; border: none; font-size: 1.1rem; cursor: pointer; padding: 0.3rem; text-decoration: none; border-radius: 8px; }
.btn-icon:hover { background: var(--surface-3); }

.main-layout { flex: 1; display: flex; overflow: hidden; }

/* ===== QUEUE PANEL ===== */
.queue-panel { width: 320px; min-width: 320px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-soft); }
.panel-header h3 { font-size: 0.85rem; font-weight: 700; }
.header-actions { display: flex; align-items: center; gap: 0.5rem; }
.btn-clear-queue { min-width: 36px; height: 36px; background: var(--red-soft); border: 1px solid var(--red-border); border-radius: 8px; cursor: pointer; font-size: 0.85rem; }
.btn-clear-queue:active { transform: scale(0.92); }
.queue-badge { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; padding: 0.1rem 0.55rem; border-radius: 1rem; font-size: 0.7rem; font-weight: 700; }

.room-session-bar { display: flex; align-items: center; gap: 0.5rem; margin: 0.5rem 0.75rem 0; padding: 0.5rem 0.75rem; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; }
.room-session-bar.active { background: var(--red-soft); border-color: var(--red-border); }
.room-session-bar.urgent { animation: urgentPulse 1s infinite; }
.rs-icon { font-size: 1rem; }
.rs-detail { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.rs-label { font-size: 0.55rem; font-weight: 700; text-transform: uppercase; color: var(--red); letter-spacing: 0.5px; }
.rs-time { font-size: 0.75rem; font-weight: 600; margin: 0.1rem 0; }
.rs-progress { height: 4px; background: var(--red-border); border-radius: 2px; overflow: hidden; }
.rs-fill { height: 100%; background: linear-gradient(90deg, #ef4444, #f59e0b); border-radius: 2px; transition: width 0.3s; }
.rs-idle { font-size: 0.7rem; font-weight: 700; color: var(--muted-2); letter-spacing: 0.5px; text-transform: uppercase; }
@keyframes urgentPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); } 50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); } }

.now-playing-card {
  margin: 0.5rem 0.75rem; padding: 0.6rem;
  background: linear-gradient(135deg, var(--red-soft), var(--blue-soft));
  border-radius: 10px; border: 1px solid var(--red-border);
  display: flex; gap: 0.6rem; align-items: center;
}
.np-art { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: var(--shadow-sm); }
.np-detail { flex: 1; min-width: 0; }
.np-label { font-size: 0.55rem; text-transform: uppercase; color: var(--red); font-weight: 700; }
.np-title { font-weight: 700; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.np-artist { font-size: 0.68rem; color: var(--muted-2); }
.ending-soon { margin-top: 0.25rem; padding: 0.2rem 0.5rem; background: #fef3c7; color: #92400e; border-radius: 4px; font-size: 0.6rem; font-weight: 600; }
.ending-soon.pulse { animation: pulse 1s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.np-progress { margin-top: 0.3rem; }
.progress-track { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #ef4444, #3b82f6); border-radius: 2px; transition: width 0.3s; }
.progress-time { display: flex; justify-content: space-between; font-size: 0.55rem; color: var(--muted-2); margin-top: 0.1rem; }
.np-controls { display: flex; flex-direction: column; gap: 0.3rem; }
.np-btn { min-width: 40px; height: 40px; border-radius: 8px; border: none; background: var(--surface); cursor: pointer; font-size: 0.85rem; box-shadow: var(--shadow-sm); }
.np-btn:active { transform: scale(0.92); }

.queue-list { flex: 1; overflow-y: auto; padding: 0 0.75rem; }
.queue-item { display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 0.4rem; border-radius: 8px; margin-bottom: 0.2rem; border: 2px solid transparent; transition: background 0.15s, border-color 0.15s; }
.queue-item:hover { background: var(--surface-3); }
.queue-item.is-next { background: var(--red-soft); border-color: var(--red-border); }
.queue-item.is-dragging { opacity: 0.4; }
.queue-item.drop-target { border-color: var(--blue); background: var(--blue-soft); }
.drag-handle { cursor: grab; color: var(--faint); font-size: 0.9rem; touch-action: none; }
.queue-rank { width: 26px; height: 26px; background: var(--surface-3); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.7rem; color: var(--muted); flex-shrink: 0; }
.rank-next { background: var(--red); color: #fff; }
.queue-detail { flex: 1; min-width: 0; }
.queue-song { font-weight: 600; font-size: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.queue-artist { font-size: 0.65rem; color: var(--muted-2); display: flex; align-items: center; gap: 0.3rem; }
.guest-badge { font-size: 0.55rem; padding: 0.05rem 0.35rem; background: var(--blue-soft); color: var(--blue); border-radius: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90px; }
.queue-actions { display: flex; align-items: center; gap: 0.25rem; }
.queue-move { display: flex; flex-direction: column; gap: 0.1rem; }
.move-btn { width: 40px; height: 20px; border: none; background: var(--surface-3); border-radius: 4px; cursor: pointer; font-size: 0.5rem; color: var(--muted); padding: 0; }
.move-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.move-btn:active:not(:disabled) { background: var(--blue-soft); }
.btn-play-now { min-width: 40px; height: 40px; background: var(--green); border: none; border-radius: 8px; color: #fff; cursor: pointer; font-size: 0.8rem; }
.btn-queue-next { min-width: 40px; height: 40px; background: var(--blue-soft); border: 1px solid var(--blue-border); border-radius: 8px; color: var(--blue); cursor: pointer; font-size: 0.8rem; transition: all 0.15s; }
.btn-queue-next:hover { background: var(--blue); color: #fff; }
.btn-queue-next:active { transform: scale(0.92); }
.btn-remove { min-width: 40px; height: 40px; background: none; border: none; color: var(--red); cursor: pointer; font-size: 0.9rem; border-radius: 8px; }
.btn-remove:active { background: var(--red-soft); }
.queue-empty { text-align: center; padding: 2rem 1rem; color: var(--muted-2); }
.empty-art { font-size: 2rem; }
.empty-sub { font-size: 0.65rem; margin-top: 0.3rem; }

.batch-bar { display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 0.75rem; background: var(--blue-soft); border-top: 2px solid var(--blue); flex-wrap: wrap; }
.batch-count { font-weight: 700; font-size: 0.75rem; color: var(--blue); }
.btn-batch-add { padding: 0.45rem 0.75rem; background: var(--blue); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.7rem; }
.btn-batch-select-all, .btn-batch-clear { padding: 0.45rem 0.75rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.7rem; color: var(--muted); }
/* ===== PIPELINE BAR ===== */
.pipeline-bar {
  margin: 0.5rem 0.75rem 0;
  padding: 0.45rem 0.6rem;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: border-color 0.3s;
}
.pipeline-bar.ok { border-color: var(--border); }
.pipeline-bar.warn { border-color: #f59e0b; background: rgba(245, 158, 11, 0.08); }
.pipe-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.3rem; }
.pipe-title { font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
.pipe-live { font-size: 0.5rem; color: var(--muted-2); }
.pipe-live.on { color: var(--green); animation: pulse 1.6s infinite; }
.pipe-cells { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.3rem; }
.pipe-cell {
  text-align: center; padding: 0.25rem 0.15rem;
  background: var(--surface); border-radius: 8px;
  border: 1px solid var(--border-soft);
}
.pipe-cell.warn { border-color: #f59e0b; background: rgba(245, 158, 11, 0.12); }
.pc-icon { display: block; font-size: 0.7rem; }
.pc-val { display: block; font-size: 0.72rem; font-weight: 700; color: var(--text); line-height: 1.2; }
.pc-label { display: block; font-size: 0.5rem; color: var(--muted-2); text-transform: uppercase; letter-spacing: 0.3px; }

.queue-footer { display: flex; gap: 0.35rem; padding: 0.5rem 0.75rem; border-top: 1px solid var(--border-soft); }
.stat-pill { flex: 1; text-align: center; background: var(--surface-2); border-radius: 8px; padding: 0.35rem 0.2rem; font-size: 0.55rem; color: var(--muted-2); }
.stat-pill strong { display: block; font-size: 0.8rem; color: var(--text); }
.stat-pill em { font-style: normal; }

/* ===== BROWSER ===== */
.browser-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: var(--bg); }
.browser-tabs { display: flex; gap: 0.25rem; padding: 0.5rem 1rem 0; background: var(--surface); border-bottom: 1px solid var(--border-soft); }
.tab-btn { padding: 0.5rem 0.85rem; background: transparent; border: none; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 0.75rem; font-weight: 500; color: var(--muted); border-bottom: 2px solid transparent; transition: all 0.15s; }
.tab-btn:hover { background: var(--surface-3); }
.tab-btn.active { color: var(--red); font-weight: 700; border-bottom: 2px solid var(--red); }
.filter-strip { display: flex; align-items: center; gap: 0.3rem; padding: 0.5rem 1rem; background: var(--surface); border-bottom: 1px solid var(--border-soft); overflow-x: auto; }
.filter-chip { display: flex; align-items: center; gap: 0.25rem; padding: 0.4rem 0.6rem; background: var(--surface-3); border: 2px solid transparent; border-radius: 2rem; cursor: pointer; font-size: 0.7rem; white-space: nowrap; transition: all 0.15s; flex-shrink: 0; }
.filter-chip:hover { border-color: var(--red-border); }
.filter-chip.active { background: var(--surface); border-color: var(--red); color: var(--red); font-weight: 600; }
.chip-emoji { font-size: 0.75rem; }
.chip-count { font-size: 0.55rem; color: var(--muted-2); background: var(--surface); border-radius: 1rem; padding: 0.05rem 0.35rem; }
.sort-wrap { margin-left: auto; display: flex; align-items: center; gap: 0.3rem; flex-shrink: 0; }
.btn-add-all { padding: 0.4rem 0.7rem; background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none; border-radius: 2rem; cursor: pointer; font-size: 0.68rem; font-weight: 600; white-space: nowrap; transition: transform 0.1s, opacity 0.2s; }
.btn-add-all:hover { opacity: 0.9; }
.btn-add-all:active { transform: scale(0.95); }
.sort-label { font-size: 0.65rem; color: var(--muted-2); }
.sort-select { padding: 0.35rem 0.5rem; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; font-size: 0.7rem; color: var(--text); cursor: pointer; }
.sort-select:focus { outline: none; border-color: var(--red); }

.song-grid { flex: 1; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 0.3rem; padding: 0.5rem 1rem; align-content: start; }
.skeleton-card { display: flex; gap: 0.5rem; background: var(--surface); border-radius: 10px; padding: 0.5rem; border: 1px solid var(--border-soft); }
.sk-thumb { width: 38px; height: 38px; border-radius: 8px; background: linear-gradient(90deg, var(--surface-3) 25%, var(--border) 50%, var(--surface-3) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
.sk-lines { flex: 1; }
.sk-line { height: 10px; background: linear-gradient(90deg, var(--surface-3) 25%, var(--border) 50%, var(--surface-3) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 4px; margin-bottom: 5px; }
.w-75 { width: 75%; } .w-50 { width: 50%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.browser-empty { grid-column: 1/-1; text-align: center; padding: 3rem 1rem; color: var(--muted-2); }
.empty-emoji { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
.browser-empty h3 { color: var(--muted); margin-bottom: 0.3rem; }
.browser-empty p { font-size: 0.75rem; }
.load-more-row { text-align: center; padding: 0.5rem; }
.btn-load-more { padding: 0.55rem 1.5rem; background: var(--surface); border: 2px solid var(--border); border-radius: 2rem; cursor: pointer; font-size: 0.75rem; font-weight: 600; color: var(--muted); transition: all 0.2s; }
.btn-load-more:hover { border-color: var(--red); color: var(--red); }

.history-list { flex: 1; overflow-y: auto; padding: 0.5rem 1rem; }
.history-group { margin-bottom: 0.5rem; }
.history-date { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; color: var(--muted-2); padding: 0.4rem 0.2rem; letter-spacing: 0.5px; }
.history-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.6rem; background: var(--surface); border-radius: 8px; margin-bottom: 0.25rem; border: 1px solid var(--border-soft); }
.history-time { font-size: 0.65rem; color: var(--muted-2); min-width: 45px; }
.history-info { flex: 1; min-width: 0; }
.history-title { font-weight: 600; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.history-artist { font-size: 0.68rem; color: var(--muted-2); }
.card-add {
  min-width: 40px; height: 40px; border-radius: 50%;
  border: 2px solid var(--red); background: var(--surface);
  color: var(--red); font-size: 1rem; font-weight: 700; cursor: pointer;
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.card-add:hover { background: var(--red); color: #fff; }
.card-add:active { transform: scale(0.9); }

/* ===== YOUTUBE ===== */
.yt-chip .yt-online { width: 7px; height: 7px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 6px rgba(239,68,68,0.8); animation: pulse 1.2s infinite; }
.yt-panel { flex: 1; overflow-y: auto; padding: 0.5rem 1rem; align-content: start; }
.yt-header-row { padding: 0.3rem 0.2rem 0.5rem; }
.yt-note { font-size: 0.7rem; color: var(--muted-2); }
.yt-item { display: flex; align-items: center; gap: 0.65rem; padding: 0.5rem; background: var(--surface); border: 1px solid var(--border-soft); border-radius: 10px; margin-bottom: 0.35rem; transition: background 0.15s, border-color 0.15s; }
.yt-item:hover { border-color: var(--red-border); }
.yt-thumb { width: 96px; height: 54px; border-radius: 8px; object-fit: cover; flex-shrink: 0; background: var(--surface-3); }
.yt-detail { flex: 1; min-width: 0; }
.yt-title { font-weight: 600; font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.yt-artist { font-size: 0.68rem; color: var(--muted-2); display: flex; align-items: center; gap: 0.3rem; }
.yt-dur { color: var(--blue); font-weight: 600; }
.yt-tag { font-size: 0.55rem; font-weight: 700; color: #fff; background: linear-gradient(135deg, #ef4444, #dc2626); padding: 0.08rem 0.35rem; border-radius: 4px; margin-left: 0.3rem; vertical-align: middle; }
.yt-loading { text-align: center; padding: 3rem 1rem; color: var(--muted-2); }
.yt-loading p { font-size: 0.8rem; margin-top: 0.6rem; }
.spinner-ring { width: 34px; height: 34px; border: 3px solid var(--border); border-top-color: var(--red); border-radius: 50%; margin: 0 auto; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.yt-error { text-align: center; padding: 3rem 1rem; color: var(--muted-2); }
.yt-error h3 { color: var(--muted); margin-bottom: 0.3rem; }
.yt-error p { font-size: 0.75rem; max-width: 420px; margin: 0 auto; }

/* ===== TOASTS ===== */
.toast-stack { position: fixed; bottom: 1.5rem; left: 50%; transform: translateX(-50%); z-index: 300; display: flex; flex-direction: column; gap: 0.4rem; align-items: center; pointer-events: none; }
.operator-toast {
  display: flex; align-items: center; gap: 0.5rem;
  background: #1e293b; color: #fff;
  padding: 0.6rem 1.25rem; border-radius: 2rem;
  font-size: 0.8rem; box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  border-left: 4px solid #3b82f6;
}
.operator-toast.toast-success { border-left-color: #10b981; }
.operator-toast.toast-error { border-left-color: #ef4444; }
.operator-toast.toast-warning { border-left-color: #f59e0b; }
.toast-icon { font-size: 0.9rem; }
.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateY(20px) scale(0.9); }
.toast-leave-to { opacity: 0; transform: translateY(10px) scale(0.9); }

/* ===== CONFIRM ===== */
.confirm-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 400; display: flex; align-items: center; justify-content: center; }
.confirm-card { background: var(--surface); color: var(--text); border-radius: 16px; padding: 1.5rem; text-align: center; max-width: 320px; width: 90%; box-shadow: var(--shadow-md); animation: scaleIn 0.2s ease-out; }
.confirm-icon { font-size: 2rem; display: block; margin-bottom: 0.5rem; }
.confirm-actions { display: flex; gap: 0.5rem; margin-top: 1rem; }
.btn-cancel { flex: 1; padding: 0.6rem; background: var(--surface-3); color: var(--text); border: none; border-radius: 8px; cursor: pointer; }
.btn-danger { flex: 1; padding: 0.6rem; background: var(--red); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
@keyframes scaleIn { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } }

button:focus-visible, select:focus-visible, input:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }

/* Scrollbar sesuai tema */
.queue-list::-webkit-scrollbar, .song-grid::-webkit-scrollbar, .history-list::-webkit-scrollbar { width: 8px; }
.queue-list::-webkit-scrollbar-thumb, .song-grid::-webkit-scrollbar-thumb, .history-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
</style>
