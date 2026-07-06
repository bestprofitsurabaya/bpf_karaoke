import { defineStore } from 'pinia'
import axios from 'axios'
import { io } from 'socket.io-client'

export const useKaraokeStore = defineStore('karaoke', {
  state: () => ({
    songs: [],
    waitingQueue: [],
    currentSong: null,
    isPlaying: false,
    currentVolume: 80,
    vocalMode: 'stereo',
    searchQuery: '',
    selectedGenre: null,
    genres: [],
    stats: {},
    roomId: localStorage.getItem('karaoke_room') || 'KARAOKE BPF SBY',
    screenType: 'operator',
    isConnected: false,
    socket: null
  }),

  getters: {
    filteredSongs: (state) => {
      return state.songs
    }
  },

  actions: {
    setRoomId(id) {
      this.roomId = id
      localStorage.setItem('karaoke_room', id)
      if (this.socket) {
        this.socket.emit('register', { type: this.screenType, room_id: this.roomId })
      }
    },
    setScreenType(type) {
      this.screenType = type
    },
    connectSocket() {
      if (this.socket) return;
      
      const wsUrl = import.meta.env.VITE_WS_URL || 'wss://nasbpfsby.duckdns.org:8443'
      this.socket = io(wsUrl, { transports: ['websocket'], secure: true })

      this.socket.on('connect', () => {
        this.isConnected = true
        this.socket.emit('register', { type: this.screenType, room_id: this.roomId })
      })

      this.socket.on('disconnect', () => {
        this.isConnected = false
      })

      this.socket.on('queue_updated', () => {
        this.fetchQueue()
      })

      this.socket.on('play', (data) => {
        const found = this.waitingQueue.find(q => q.id === data.queue_id)
        if (found) {
          this.currentSong = {
            queue_id: found.id,
            song_id: found.song_id,
            song_title: found.song.title,
            song_artist: found.song.artist,
            file_path: found.song.file_path
          }
        }
        this.isPlaying = true
      })

      this.socket.on('ctrl', (data) => {
        if (data.action === 'pause') this.isPlaying = false
        if (data.action === 'resume') this.isPlaying = true
        if (data.action === 'skip') {
          this.currentSong = null
          this.isPlaying = false
          this.fetchQueue()
        }
      })

      this.socket.on('vol', (data) => {
        this.currentVolume = data.volume
      })

      this.socket.on('vocal', (data) => {
        this.vocalMode = data.channel
      })
    },

    async fetchSongs() {
      try {
        let url = `/api/songs?limit=250`
        if (this.searchQuery) url += `&search=${encodeURIComponent(this.searchQuery)}`
        if (this.selectedGenre) url += `&genre=${encodeURIComponent(this.selectedGenre)}`
        const res = await axios.get(url)
        this.songs = res.data
      } catch (err) {
        console.error(err)
      }
    },

    async fetchGenres() {
      try {
        const res = await axios.get('/api/songs/genres')
        this.genres = res.data
      } catch (err) {
        console.error(err)
      }
    },

    async fetchQueue() {
      try {
        const res = await axios.get(`/api/queue/${encodeURIComponent(this.roomId)}`)
        this.waitingQueue = res.data
      } catch (err) {
        console.error(err)
      }
    },

    async fetchStats() {
      try {
        const res = await axios.get('/api/admin/stats')
        this.stats = res.data
      } catch (err) {
        console.error(err)
      }
    },

    async addToQueue(songId) {
      try {
        await axios.post('/api/queue', { song_id: songId, room_id: this.roomId })
        this.fetchQueue()
        return true
      } catch (err) {
        return false
      }
    },

    async removeFromQueue(queueId) {
      try {
        await axios.delete(`/api/queue/${queueId}?room_id=${encodeURIComponent(this.roomId)}`)
        this.fetchQueue()
      } catch (err) {
        console.error(err)
      }
    },

    playSong(songId, queueId) {
      if (this.socket) {
        this.socket.emit('play_song', { song_id: songId, queue_id: queueId, room_id: this.roomId })
      }
    },

    pauseSong() {
      if (this.socket) this.socket.emit('pause_song', { room_id: this.roomId })
    },

    resumeSong() {
      if (this.socket) this.socket.emit('resume_song', { room_id: this.roomId })
    },

    skipSong(queueId) {
      if (this.socket) this.socket.emit('skip_song', { queue_id: queueId, room_id: this.roomId })
    },

    setVolume(vol) {
      if (this.socket) this.socket.emit('set_volume', { volume: parseInt(vol), room_id: this.roomId })
    },

    toggleVocal(mode) {
      if (this.socket) this.socket.emit('toggle_vocal', { channel: mode, room_id: this.roomId })
    }
  }
})
