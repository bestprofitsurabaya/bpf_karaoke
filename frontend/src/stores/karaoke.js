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
  const roomId = ref(localStorage.getItem('karaoke_room') || 'Room 1')
  const isDarkMode = ref(true)
  const socket = ref(null)
  const isConnected = ref(false)
  const genres = ref([])
  const languages = ref([])
  const stats = ref({})
  const token = ref(localStorage.getItem('auth_token') || '')
  const error = ref(null)
  const availableRooms = ref([])

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
    return result
  })

  const waitingQueue = computed(() => queue.value.filter(item => item.status === 'waiting'))
  const currentQueue = computed(() => queue.value.find(item => item.status === 'playing'))

  // Actions
  function setScreenType(type) { screenType.value = type }
  
  function setRoomId(id) { 
    roomId.value = id
    localStorage.setItem('karaoke_room', id)
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

    // Event listeners
    socket.value.on('play', (data) => {
      console.log('🎵 Play event:', data)
      currentSong.value = { song_id: data.song_id, queue_id: data.queue_id, song_title: '', song_artist: '', auto_play: data.auto_play || false }
      isPlaying.value = true
      if (data.song_id) fetchSongDetail(data.song_id)
    })

    socket.value.on('ctrl', (data) => {
      console.log('🎮 Control:', data)
      if (data.action === 'pause') isPlaying.value = false
      if (data.action === 'resume') isPlaying.value = true
      if (data.action === 'skip' || data.action === 'stop') {
        isPlaying.value = false
        currentSong.value = null
        fetchQueue()
      }
    })

    socket.value.on('vol', (data) => { currentVolume.value = data.volume })
    socket.value.on('vocal', (data) => { vocalMode.value = data.channel })
    socket.value.on('queue_updated', () => { fetchQueue() })
    socket.value.on('ok', (data) => { console.log('✅ Registration confirmed:', data) })
    
    socket.value.on('queue_empty', (data) => {
      console.log('📭 Queue empty for room:', data.room_id)
      if (data.room_id === roomId.value) {
        currentSong.value = null
        isPlaying.value = false
      }
    })
  }

  async function fetchSongDetail(songId) {
    try {
      const res = await axios.get('/api/songs?limit=1000')
      const song = res.data.find(s => s.id === songId)
      if (song && currentSong.value) {
        currentSong.value.song_title = song.title
        currentSong.value.song_artist = song.artist || ''
      }
    } catch (err) { console.error('Fetch song detail error:', err) }
  }

  // API calls
  async function fetchSongs() {
    try {
      const params = { limit: 250 }
      if (searchQuery.value) params.search = searchQuery.value
      if (selectedGenre.value) params.genre = selectedGenre.value
      const response = await axios.get('/api/songs', { params })
      songs.value = response.data
      error.value = null
    } catch (err) { console.error('Fetch songs error:', err) }
  }

  async function fetchQueue() {
    try {
      const response = await axios.get(`/api/queue/${encodeURIComponent(roomId.value)}`)
      queue.value = response.data
    } catch (err) { console.error('Fetch queue error:', err) }
  }

  async function fetchGenres() {
    try {
      const response = await axios.get('/api/songs/genres')
      genres.value = response.data
    } catch (err) { console.error('Fetch genres error:', err) }
  }

  async function fetchStats() {
    try {
      const response = await axios.get('/api/admin/stats')
      stats.value = response.data
    } catch (err) { console.error('Fetch stats error:', err) }
  }

  async function fetchRooms() {
    try {
      const response = await axios.get('/api/rooms/active')
      availableRooms.value = response.data.rooms || []
    } catch (err) { console.error('Fetch rooms error:', err) }
  }

  async function addToQueue(songId) {
    try {
      await axios.post('/api/queue', { song_id: songId, room_id: roomId.value })
      await fetchQueue()
      return true
    } catch (err) { console.error('Add to queue error:', err); return false }
  }

  async function removeFromQueue(queueId) {
    try {
      await axios.delete(`/api/queue/${queueId}?room_id=${encodeURIComponent(roomId.value)}`)
      await fetchQueue()
    } catch (err) { console.error('Remove from queue error:', err) }
  }

  function playSong(songId, queueId) {
    if (socket.value && isConnected.value) {
      socket.value.emit('play_song', { song_id: songId, room_id: roomId.value, queue_id: queueId })
    }
  }

  function pauseSong() {
    if (socket.value && isConnected.value) socket.value.emit('pause_song', { room_id: roomId.value })
  }

  function resumeSong() {
    if (socket.value && isConnected.value) socket.value.emit('resume_song', { room_id: roomId.value })
  }

  function skipSong(queueId) {
    if (socket.value && isConnected.value) socket.value.emit('skip_song', { room_id: roomId.value, queue_id: queueId })
  }

  function setVolume(volume) {
    currentVolume.value = volume
    if (socket.value && isConnected.value) socket.value.emit('set_volume', { room_id: roomId.value, volume: volume })
  }

  function toggleVocal(channel) {
    vocalMode.value = channel
    if (socket.value && isConnected.value) socket.value.emit('toggle_vocal', { room_id: roomId.value, channel: channel })
  }

  return {
    songs, queue, currentSong, isPlaying, currentVolume, vocalMode,
    searchQuery, selectedGenre, selectedLanguage, screenType, roomId,
    isDarkMode, socket, isConnected, genres, languages, stats, token, error,
    availableRooms,
    filteredSongs, waitingQueue, currentQueue,
    setScreenType, setRoomId, connectSocket,
    fetchSongs, fetchQueue, fetchGenres,
    addToQueue, removeFromQueue, playSong, pauseSong, resumeSong,
    skipSong, setVolume, toggleVocal, fetchStats, fetchSongDetail, fetchRooms
  }
})
