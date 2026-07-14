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
  const roomId = ref('KARAOKE BPF SBY')
  const isDarkMode = ref(true)
  const socket = ref(null)
  const isConnected = ref(false)
  const genres = ref([])
  const languages = ref([])
  const stats = ref({})
  const token = ref(localStorage.getItem('auth_token') || '')
  const error = ref(null)
  const keyShift = ref(0)
  const vocalAI = ref(false)
  const roomMood = ref(null)

  // Getters
  const filteredSongs = computed(() => {
    let result = songs.value
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(song =>
        song.title.toLowerCase().includes(query) ||
        (song.artist && song.artist.toLowerCase().includes(query))
      )
    }
    if (selectedGenre.value) result = result.filter(song => song.genre === selectedGenre.value)
    if (selectedLanguage.value) result = result.filter(song => song.language === selectedLanguage.value)
    return result
  })

  const waitingQueue = computed(() => queue.value.filter(item => item.status === 'waiting'))

  // Actions
  function setScreenType(type) { screenType.value = type }
  function setRoomId(id) { roomId.value = id }

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
      currentSong.value = { song_id: data.song_id, queue_id: data.queue_id, song_title: '', song_artist: '', auto_play: data.auto_play || false }
      isPlaying.value = true
      if (data.song_id) fetchSongDetail(data.song_id)
    })

    // Backend emit: "ctrl"
    socket.value.on('ctrl', (data) => {
      console.log('🎮 Control:', data)
      if (data.action === 'pause') isPlaying.value = false
      if (data.action === 'resume') isPlaying.value = true
      if (data.action === 'skip') { isPlaying.value = false; currentSong.value = null; fetchQueue() }
      if (data.action === 'stop') { isPlaying.value = false; currentSong.value = null }
    })

    // Backend emit: "vol"
    socket.value.on('vol', (data) => { currentVolume.value = data.volume })
    // Backend emit: "vocal"
    socket.value.on('vocal', (data) => { vocalMode.value = data.channel })
    // Backend emit: "queue_updated"
    socket.value.on('queue_updated', () => { fetchQueue() })
    // Backend emit: "ok"
    socket.value.on('ok', (data) => { console.log('✅ Registered:', data) })
    // Backend emit: "queue_empty"
    socket.value.on('queue_empty', () => { isPlaying.value = false; currentSong.value = null; fetchQueue() })
  }

  async function fetchSongDetail(songId) {
    try {
      const res = await axios.get('/api/songs?limit=500')
      const song = res.data.find(s => s.id === songId)
      if (song && currentSong.value) {
        currentSong.value.song_title = song.title
        currentSong.value.song_artist = song.artist || ''
      }
    } catch (e) { console.error('Fetch song detail:', e) }
  }

  async function fetchSongs() {
    try {
      const params = { limit: 300 }
      if (searchQuery.value) params.search = searchQuery.value
      if (selectedGenre.value) params.genre = selectedGenre.value
      if (selectedLanguage.value) params.language = selectedLanguage.value
      const res = await axios.get('/api/songs', { params })
      songs.value = res.data
      error.value = null
    } catch (err) { console.error('Fetch songs:', err) }
  }

  async function fetchQueue() {
    try {
      const res = await axios.get(`/api/queue/${roomId.value}`)
      queue.value = res.data
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
      const res = await axios.get('/api/admin/stats')
      stats.value = res.data
    } catch (err) { console.error('Fetch stats:', err) }
  }

  async function fetchMood() {
    try {
      const res = await axios.get(`/api/ai/mood/${roomId.value}`)
      roomMood.value = res.data
    } catch (e) { /* silent */ }
  }

  async function addToQueue(songId) {
    try {
      await axios.post('/api/queue', { song_id: songId, room_id: roomId.value })
      await fetchQueue()
      return true
    } catch (err) { console.error('Add queue:', err); return false }
  }

  async function removeFromQueue(queueId) {
    try {
      await axios.delete(`/api/queue/${queueId}?room_id=${roomId.value}`)
      await fetchQueue()
    } catch (err) { console.error('Remove queue:', err) }
  }

  function playSong(songId, queueId) {
    if (socket.value && isConnected.value) {
      console.log('▶️ Emitting play_song:', { song_id: songId, queue_id: queueId })
      socket.value.emit('play_song', { song_id: songId, room_id: roomId.value, queue_id: queueId })
    }
  }

  function pauseSong() { if (socket.value && isConnected.value) socket.value.emit('pause_song', { room_id: roomId.value }) }
  function resumeSong() { if (socket.value && isConnected.value) socket.value.emit('resume_song', { room_id: roomId.value }) }
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
    isDarkMode, socket, isConnected, genres, languages, stats, token, error,
    keyShift, vocalAI, roomMood,
    filteredSongs, waitingQueue,
    setScreenType, setRoomId, connectSocket,
    fetchSongs, fetchQueue, fetchGenres, fetchStats, fetchMood,
    addToQueue, removeFromQueue, playSong, pauseSong, resumeSong,
    skipSong, setVolume, toggleVocal, changeKey, generatePlaylist, fetchSongDetail
  }
})
