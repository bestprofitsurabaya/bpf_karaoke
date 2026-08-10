import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { io } from 'socket.io-client'
import axios from 'axios'

export const useKaraokeStore = defineStore('karaoke', () => {
  // State
  const songs = ref([])
  const queue = ref([])
  const currentSong = ref(null)
  const isPlaying = ref(false)
  const currentVolume = ref(80)
  const vocalMode = ref('stereo')
  const searchQuery = ref('')
  const selectedGenre = ref(null)
  const selectedLanguage = ref(null)
  const screenType = ref('operator')
  const roomId = ref(localStorage.getItem('karaoke_room') || 'default')
  const isDarkMode = ref(localStorage.getItem('karaoke_dark') === '1')
  const socket = ref(null)
  const isConnected = ref(false)
  const genres = ref([])
  const languages = ref([])
  const stats = ref({})
  // Pipeline sync → transcode (panel operator, auto-refresh)
  const pipeline = ref(null)
  const token = ref(localStorage.getItem('auth_token') || '')
  const error = ref(null)
  const keyShift = ref(0)
  const vocalAI = ref(false)
  const roomMood = ref(null)
  const roomSession = ref({ active: false, session: null })
  // YouTube: cari lagu yang tidak ada di database lokal (YouTube Data API v3)
  const youtubeMode = ref(false)
  const youtubeResults = ref([])
  const youtubeSearching = ref(false)
  const youtubeError = ref(null)
  const fetchingSongs = ref(false)
  const hasMoreSongs = ref(false)
  // Pause manual oleh operator/user (jangan di-reset oleh refresh queue realtime)
  const manuallyPaused = ref(false)
  // Revisi antrian dari server (header X-Queue-Revision) untuk proteksi race reorder
  const queueRevision = ref(0)

  // Getters
  // Catatan: filter/sort lagu dilakukan server-side di /api/songs (lihat fetchSongs),
  // sehingga getter client-side tidak lagi diperlukan.
  const waitingQueue = computed(() => queue.value.filter(item => item.status === 'waiting'))

  // Actions
  function setScreenType(type) { screenType.value = type }

  function setRoomId(id) {
    if (id === roomId.value) return
    const oldRoom = roomId.value
    roomId.value = id
    localStorage.setItem('karaoke_room', id)
    // Reset revisi antrian (milik room lama) agar reorder tidak salah ditolak
    queueRevision.value = 0
    // Re-sync socket room agar event realtime tetap diterima setelah ganti room
    if (socket.value?.connected) {
      socket.value.emit('leave_room', { room_id: oldRoom })
      socket.value.emit('register', { type: screenType.value, room_id: id })
      socket.value.emit('join_room', { type: screenType.value, room_id: id })
    }
    fetchQueue()  // Auto-refresh queue saat ganti room
  }

  function connectSocket() {
    const wsUrl = window.location.origin
    socket.value = io(wsUrl, {
      transports: ['websocket', 'polling'],
      path: '/socket.io/',
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000
    })

    socket.value.on('connect', () => {
      isConnected.value = true
      console.log('✅ Socket connected:', socket.value.id)
      socket.value.emit('register', { type: screenType.value, room_id: roomId.value })
      socket.value.emit('join_room', { type: screenType.value, room_id: roomId.value })
    })

    socket.value.on('disconnect', (reason) => {
      isConnected.value = false
      console.log('❌ Socket disconnected:', reason)
    })

    socket.value.on('connect_error', (err) => {
      console.error('Socket error:', err.message)
    })

    // Backend emit: "play"
    socket.value.on('play', (data) => {
      console.log('🎵 Play event:', data)
      currentSong.value = { song_id: data.song_id, queue_id: data.queue_id, song_title: '', song_artist: '', file_format: '', youtube_id: '', auto_play: data.auto_play || false }
      isPlaying.value = true
      manuallyPaused.value = false
      if (data.song_id) fetchSongDetail(data.song_id)
    })

    // Backend emit: "ctrl"
    socket.value.on('ctrl', (data) => {
      console.log('🎮 Control:', data)
      if (data.action === 'pause') { isPlaying.value = false; manuallyPaused.value = true }
      if (data.action === 'resume') { isPlaying.value = true; manuallyPaused.value = false }
      if (data.action === 'skip') { isPlaying.value = false; currentSong.value = null; manuallyPaused.value = false; fetchQueue() }
      if (data.action === 'stop') { isPlaying.value = false; currentSong.value = null; manuallyPaused.value = false }
    })

    // Backend emit: "vol"
    socket.value.on('vol', (data) => { currentVolume.value = data.volume })
    // Backend emit: "vocal"
    socket.value.on('vocal', (data) => { vocalMode.value = data.channel })
    // Backend emit: "queue_updated"
    socket.value.on('queue_updated', (data) => {
      if (data && typeof data.revision === 'number') queueRevision.value = data.revision
      fetchQueue()
    })
    // Backend emit: "ok"
    socket.value.on('ok', (data) => {
      console.log('✅ Registered:', data)
      // Sinkronkan key shift room saat (re)connect
      if (typeof data.key_shift === 'number') keyShift.value = data.key_shift
      // Sinkronkan sesi room saat (re)connect
      fetchRoomSession()
    })

    // Backend emit: "room_session" (start/extend/end oleh admin)
    socket.value.on('room_session', (data) => {
      roomSession.value = { active: data.status === 'active', session: data }
    })
    // Backend emit: "queue_empty"
    socket.value.on('queue_empty', () => { isPlaying.value = false; currentSong.value = null; manuallyPaused.value = false; fetchQueue() })
  }

  async function fetchSongDetail(songId) {
    try {
      const res = await axios.get(`/api/songs/${songId}`)
      const song = res.data
      if (song && currentSong.value) {
        currentSong.value.song_title = song.title
        currentSong.value.song_artist = song.artist || ''
        currentSong.value.file_format = song.file_format || ''
        // 'yt:<videoId>' -> youtube_id untuk embed player
        if ((song.file_format === 'youtube') && String(song.file_path || '').startsWith('yt:')) {
          currentSong.value.youtube_id = String(song.file_path).slice(3)
        } else {
          currentSong.value.youtube_id = ''
        }
      }
    } catch (e) { console.error('Fetch song detail:', e) }
  }

  async function fetchSongs({ limit = 300, offset = 0, append = false, sort = null } = {}) {
    fetchingSongs.value = true
    try {
      const params = { limit }
      if (offset > 0) params.offset = offset
      if (sort) params.sort = sort
      if (searchQuery.value) params.search = searchQuery.value
      if (selectedGenre.value) params.genre = selectedGenre.value
      if (selectedLanguage.value) params.language = selectedLanguage.value
      const res = await axios.get('/api/songs', { params })
      songs.value = append ? [...songs.value, ...res.data] : res.data
      hasMoreSongs.value = res.data.length >= limit
      error.value = null
    } catch (err) { console.error('Fetch songs:', err) }
    fetchingSongs.value = false
  }

  async function fetchQueue() {
    try {
      const res = await axios.get(`/api/queue/${roomId.value}`)
      queue.value = res.data
      const rev = Number(res.headers?.['x-queue-revision'])
      if (!Number.isNaN(rev)) queueRevision.value = rev
      // Update current song jika ada yang playing (tapi jangan timpa status pause manual)
      const playing = res.data.find(q => q.status === 'playing')
      if (playing && playing.song) {
        currentSong.value = {
          song_id: playing.song_id,
          queue_id: playing.id,
          song_title: playing.song.title,
          song_artist: playing.song.artist || '',
          file_format: playing.song.file_format || '',
          youtube_id: (playing.song.file_format === 'youtube' && String(playing.song.file_path || '').startsWith('yt:'))
            ? String(playing.song.file_path).slice(3) : ''
        }
        if (!manuallyPaused.value) isPlaying.value = true
      }
    } catch (err) { console.error('Fetch queue:', err) }
  }

  async function fetchGenres() {
    try {
      const res = await axios.get('/api/songs/genres')
      genres.value = res.data
    } catch (err) { console.error('Fetch genres:', err) }
  }

  async function fetchStats() {
    try {
      // Endpoint publik untuk operator (admin stats terproteksi auth)
      const res = await axios.get('/api/stats')
      stats.value = res.data
    } catch (err) { console.error('Fetch stats:', err) }
  }

  async function fetchPipeline() {
    try {
      const res = await axios.get('/api/pipeline')
      pipeline.value = res.data
    } catch (err) { console.error('Fetch pipeline:', err) }
  }

  async function fetchMood() {
    try {
      const res = await axios.get(`/api/ai/mood/${roomId.value}`)
      roomMood.value = res.data
    } catch (e) { /* silent */ }
  }

  async function fetchRoomSession() {
    try {
      const res = await axios.get(`/api/rooms/${roomId.value}/session/current`)
      roomSession.value = res.data
    } catch (e) { /* silent */ }
  }

  async function addToQueue(songId, requesterName = null) {
    try {
      const res = await axios.post('/api/queue', { song_id: songId, room_id: roomId.value, requester_name: requesterName })
      await fetchQueue()
      return res.data || true
    } catch (err) { console.error('Add queue:', err); return false }
  }

  // ========== YOUTUBE ==========
  async function youtubeSearch(q) {
    youtubeError.value = null
    if (!q || !q.trim()) { youtubeResults.value = []; return }
    youtubeSearching.value = true
    try {
      const res = await axios.get('/api/youtube/search', { params: { q: q.trim(), limit: 12 } })
      youtubeResults.value = res.data.results || []
    } catch (err) {
      youtubeError.value = err.response?.data?.detail
        || 'Gagal mencari di YouTube — pastikan YOUTUBE_API_KEY sudah diset'
      youtubeResults.value = []
    }
    youtubeSearching.value = false
  }

  async function addYouTubeToQueue(item, requesterName = null) {
    try {
      const res = await axios.post('/api/youtube/queue', {
        youtube_id: item.youtube_id,
        title: item.title,
        artist: item.artist,
        room_id: roomId.value,
        requester_name: requesterName
      })
      await fetchQueue()
      return res.data
    } catch (err) { console.error('Add youtube queue:', err); return false }
  }

  function clearYoutube() {
    youtubeResults.value = []
    youtubeError.value = null
  }

  async function playNext(songId) {
    // Tambah lalu geser ke posisi tepat setelah lagu yang sedang diputar (index 1)
    const item = await addToQueue(songId)
    if (!item) return false
    const isNowPlaying = currentSong.value && isPlaying.value
    if (waitingQueue.value.length === 1 && !isNowPlaying) {
      // Antrian sebelumnya kosong -> langsung putar
      playSong(item.song_id, item.id)
      return true
    }
    const order = waitingQueue.value.map(q => q.id)
    const idx = order.indexOf(item.id)
    if (idx > 1) {
      order.splice(idx, 1)
      order.splice(1, 0, item.id)
      if (socket.value?.connected) {
        socket.value.emit('reorder_queue', {
          room_id: roomId.value,
          queue_ids: order,
          revision: queueRevision.value
        })
      }
    }
    return true
  }

  async function addAllFiltered() {
    // Tambah SEMUA lagu hasil filter (search/genre/language) ke antrian
    try {
      const params = { room_id: roomId.value, limit: 500 }
      if (searchQuery.value) params.search = searchQuery.value
      if (selectedGenre.value) params.genre = selectedGenre.value
      if (selectedLanguage.value) params.language = selectedLanguage.value
      const res = await axios.post('/api/queue/batch-filter', null, { params })
      await fetchQueue()
      return res.data
    } catch (err) { console.error('Add all filtered:', err); return null }
  }

  async function removeFromQueue(queueId) {
    try {
      await axios.delete(`/api/queue/${queueId}?room_id=${roomId.value}`)
      await fetchQueue()
    } catch (err) { console.error('Remove queue:', err) }
  }

  function playSong(songId, queueId) {
    if (socket.value && isConnected.value) {
      console.log('▶️ Emitting play_song:', { song_id: songId, queue_id: queueId, room_id: roomId.value })
      socket.value.emit('play_song', { song_id: songId, room_id: roomId.value, queue_id: queueId })
      // Optimistic update: langsung set isPlaying
      isPlaying.value = true
      manuallyPaused.value = false
      currentSong.value = { song_id: songId, queue_id: queueId, song_title: '', song_artist: '' }
      fetchSongDetail(songId)
    }
  }

  function pauseSong() {
    manuallyPaused.value = true
    if (socket.value && isConnected.value) socket.value.emit('pause_song', { room_id: roomId.value })
  }
  function resumeSong() {
    manuallyPaused.value = false
    if (socket.value && isConnected.value) socket.value.emit('resume_song', { room_id: roomId.value })
  }
  function skipSong(queueId) { if (socket.value && isConnected.value) socket.value.emit('skip_song', { room_id: roomId.value, queue_id: queueId }) }

  function setVolume(volume) {
    currentVolume.value = volume
    if (socket.value && isConnected.value) socket.value.emit('set_volume', { room_id: roomId.value, volume: volume })
  }

  function toggleVocal(channel) {
    vocalMode.value = channel
    if (socket.value && isConnected.value) socket.value.emit('toggle_vocal', { room_id: roomId.value, channel: channel })
  }

  function changeKey(shift) {
    keyShift.value = shift
    if (socket.value && isConnected.value) socket.value.emit('key_change', { key_shift: shift, room_id: roomId.value })
  }

  async function generatePlaylist(mood) {
    try {
      const res = await axios.post('/api/ai/playlist/generate', { type: 'mood', value: mood, count: 10 })
      if (res.data.songs) {
        for (const s of res.data.songs) {
          if (!waitingQueue.value.some(q => q.song_id === s.id)) await addToQueue(s.id)
        }
      }
    } catch (e) { console.error('AI playlist:', e) }
  }

  return {
    songs, queue, currentSong, isPlaying, currentVolume, vocalMode,
    searchQuery, selectedGenre, selectedLanguage, screenType, roomId,
    isDarkMode, socket, isConnected, genres, languages, stats, pipeline, token, error,
    keyShift, vocalAI, roomMood, roomSession,
    fetchingSongs, hasMoreSongs, manuallyPaused, queueRevision,
    waitingQueue,
    youtubeMode, youtubeResults, youtubeSearching, youtubeError,
    setScreenType, setRoomId, connectSocket,
    fetchSongs, fetchQueue, fetchGenres, fetchStats, fetchPipeline, fetchMood, fetchRoomSession,
    addToQueue, playNext, addAllFiltered, removeFromQueue, playSong, pauseSong, resumeSong,
    skipSong, setVolume, toggleVocal, changeKey, generatePlaylist, fetchSongDetail,
    youtubeSearch, addYouTubeToQueue, clearYoutube
  }
})
