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
  const roomId = ref('default')
  const isDarkMode = ref(true)
  const socket = ref(null)
  const isConnected = ref(false)
  const genres = ref([])
  const languages = ref([])
  const stats = ref({})
  const token = ref(localStorage.getItem('auth_token') || '')
  const error = ref(null)
  const success = ref(null)

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
    if (selectedGenre.value) {
      result = result.filter(song => song.genre === selectedGenre.value)
    }
    if (selectedLanguage.value) {
      result = result.filter(song => song.language === selectedLanguage.value)
    }
    return result
  })

  const waitingQueue = computed(() => {
    return queue.value.filter(item => item.status === 'waiting')
  })

  const currentQueue = computed(() => {
    return queue.value.find(item => item.status === 'playing')
  })

  // Actions
  function setScreenType(type) {
    screenType.value = type
  }

  function setRoomId(id) {
    roomId.value = id
  }

  function connectSocket() {
    const wsUrl = import.meta.env.VITE_WS_URL || window.location.origin
    socket.value = io(wsUrl, {
      transports: ['websocket', 'polling'],
      path: '/socket.io'
    })

    socket.value.on('connect', () => {
      isConnected.value = true
      socket.value.emit('register', {
        type: screenType.value,
        room_id: roomId.value
      })
      socket.value.emit('join_room', {
        type: screenType.value,
        room_id: roomId.value
      })
    })

    socket.value.on('disconnect', () => {
      isConnected.value = false
    })

    socket.value.on('play_video', (data) => {
      currentSong.value = data
      isPlaying.value = true
    })

    socket.value.on('control_video', (data) => {
      if (data.action === 'pause') isPlaying.value = false
      if (data.action === 'resume') isPlaying.value = true
      if (data.action === 'skip') {
        isPlaying.value = false
        currentSong.value = null
      }
    })

    socket.value.on('set_volume', (data) => {
      currentVolume.value = data.volume
    })

    socket.value.on('toggle_vocal', (data) => {
      vocalMode.value = data.channel
    })

    socket.value.on('queue_updated', () => {
      fetchQueue()
    })
  }

  async function fetchSongs() {
    try {
      const params = {}
      if (searchQuery.value) params.search = searchQuery.value
      if (selectedGenre.value) params.genre = selectedGenre.value
      if (selectedLanguage.value) params.language = selectedLanguage.value

      const response = await axios.get('/api/songs', {
        params: { ...params, limit: 100 }
      })
      songs.value = response.data
    } catch (err) {
      error.value = 'Failed to fetch songs'
    }
  }

  async function fetchQueue() {
    try {
      const response = await axios.get(`/api/queue/${roomId.value}`)
      queue.value = response.data
    } catch (err) {
      error.value = 'Failed to fetch queue'
    }
  }

  async function fetchGenres() {
    try {
      const response = await axios.get('/api/songs/genres')
      genres.value = response.data
    } catch (err) {
      console.error('Failed to fetch genres')
    }
  }

  async function fetchLanguages() {
    try {
      const response = await axios.get('/api/songs/languages')
      languages.value = response.data
    } catch (err) {
      console.error('Failed to fetch languages')
    }
  }

  async function addToQueue(songId) {
    try {
      await axios.post('/api/queue', {
        song_id: songId,
        room_id: roomId.value
      })
      await fetchQueue()
      return true
    } catch (err) {
      error.value = 'Failed to add to queue'
      return false
    }
  }

  async function removeFromQueue(queueId) {
    try {
      await axios.delete(`/api/queue/${queueId}?room_id=${roomId.value}`)
      await fetchQueue()
    } catch (err) {
      error.value = 'Failed to remove from queue'
    }
  }

  function playSong(songId, queueId) {
    if (socket.value && isConnected.value) {
      socket.value.emit('play_song', {
        song_id: songId,
        room_id: roomId.value,
        queue_id: queueId
      })
    }
  }

  function pauseSong() {
    if (socket.value && isConnected.value) {
      socket.value.emit('pause_song', { room_id: roomId.value })
    }
  }

  function resumeSong() {
    if (socket.value && isConnected.value) {
      socket.value.emit('resume_song', { room_id: roomId.value })
    }
  }

  function skipSong(queueId) {
    if (socket.value && isConnected.value) {
      socket.value.emit('skip_song', {
        room_id: roomId.value,
        queue_id: queueId
      })
    }
  }

  function setVolume(volume) {
    currentVolume.value = volume
    if (socket.value && isConnected.value) {
      socket.value.emit('set_volume', {
        room_id: roomId.value,
        volume: volume
      })
    }
  }

  function toggleVocal(channel) {
    vocalMode.value = channel
    if (socket.value && isConnected.value) {
      socket.value.emit('toggle_vocal', {
        room_id: roomId.value,
        channel: channel
      })
    }
  }

  async function fetchStats() {
    try {
      const response = await axios.get('/api/admin/stats')
      stats.value = response.data
    } catch (err) {
      console.error('Failed to fetch stats')
    }
  }

  return {
    songs, queue, currentSong, isPlaying, currentVolume, vocalMode,
    searchQuery, selectedGenre, selectedLanguage, screenType, roomId,
    isDarkMode, socket, isConnected, genres, languages, stats, token,
    error, success,
    filteredSongs, waitingQueue, currentQueue,
    setScreenType, setRoomId, connectSocket,
    fetchSongs, fetchQueue, fetchGenres, fetchLanguages,
    addToQueue, removeFromQueue, playSong, pauseSong, resumeSong,
    skipSong, setVolume, toggleVocal, fetchStats
  }
})
