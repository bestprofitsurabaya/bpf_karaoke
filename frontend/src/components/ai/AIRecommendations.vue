<template>
  <div class="ai-recommendations">
    <div class="ai-header">
      <span class="ai-icon">🤖</span>
      <h3>AI Smart Features</h3>
      <span class="ai-badge">ML Powered</span>
    </div>

    <!-- Tabs -->
    <div class="ai-tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="{ active: activeTab === tab.id }"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- Mood Detection -->
    <div v-if="activeTab === 'mood'" class="mood-section">
      <div class="mood-card" v-if="moodData">
        <div class="mood-emoji">{{ moodData.mood_emoji || '🎵' }}</div>
        <div class="mood-info">
          <div class="mood-label">Mood Ruangan</div>
          <div class="mood-value">{{ moodData.current_mood || 'neutral' }}</div>
          <div class="mood-confidence" v-if="moodData.confidence">
            Confidence: {{ (moodData.confidence * 100).toFixed(0) }}%
          </div>
        </div>
      </div>
      <div class="mood-suggestion" v-if="moodData && moodData.suggestion">
        💡 {{ moodData.suggestion }}
      </div>
      <button @click="fetchMood" class="refresh-mood">🔄 Deteksi Mood</button>
    </div>

    <!-- Smart Search -->
    <div v-if="activeTab === 'search'" class="search-section">
      <div class="ai-search-box">
        <input 
          v-model="searchQuery" 
          @input="smartSearch" 
          placeholder="🔍 Cari dengan AI (toleran typo)..."
          class="ai-search-input"
        >
      </div>
      <div v-if="searchSuggestions.length > 0" class="suggestions">
        <span class="suggest-label">Maksud Anda:</span>
        <button 
          v-for="sug in searchSuggestions" 
          :key="sug"
          @click="searchQuery = sug; smartSearch()"
          class="suggest-chip"
        >
          {{ sug }}
        </button>
      </div>
      <div class="search-results" v-if="searchResults.length > 0">
        <div 
          v-for="result in searchResults.slice(0, 5)" 
          :key="result.id"
          class="search-result-item"
          @click="$emit('addToQueue', result.id)"
        >
          <span class="result-score">{{ result.match_score || 80 }}%</span>
          <div>
            <div class="result-title">{{ result.title }}</div>
            <div class="result-artist">{{ result.artist || 'Unknown' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Auto Playlist -->
    <div v-if="activeTab === 'playlist'" class="playlist-section">
      <div class="quick-playlists">
        <button 
          v-for="pl in quickPlaylists" 
          :key="pl.id"
          @click="generatePlaylist(pl)"
          class="playlist-btn"
        >
          <span class="pl-icon">{{ pl.icon }}</span>
          <span class="pl-name">{{ pl.name }}</span>
        </button>
      </div>
      <div v-if="generatedPlaylist" class="generated-playlist">
        <h4>🎵 {{ generatedPlaylist.name }}</h4>
        <div class="playlist-songs">
          <div 
            v-for="song in (generatedPlaylist.songs || []).slice(0, 10)" 
            :key="song.id"
            class="pl-song"
            @click="$emit('addToQueue', song.id)"
          >
            <span>{{ song.title }}</span>
            <button class="add-pl-btn">+</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Similar Songs -->
    <div v-if="activeTab === 'similar'" class="similar-section">
      <p class="similar-hint">Klik lagu untuk rekomendasi</p>
      <div v-if="similarSongs.length > 0" class="similar-list">
        <div 
          v-for="song in similarSongs" 
          :key="song.song_id"
          class="similar-item"
        >
          <div class="similar-score">{{ ((song.similarity_score || 0.8) * 100).toFixed(0) }}%</div>
          <div>
            <div class="similar-title">Song #{{ song.song_id }}</div>
            <div class="similar-reason">{{ song.reason || 'Similar' }}</div>
          </div>
          <button @click="$emit('addToQueue', song.song_id)" class="add-similar-btn">+</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['addToQueue'])

const activeTab = ref('mood')
const moodData = ref(null)
const searchQuery = ref('')
const searchResults = ref([])
const searchSuggestions = ref([])
const quickPlaylists = ref([])
const generatedPlaylist = ref(null)
const similarSongs = ref([])

const tabs = [
  { id: 'mood', label: 'Mood', icon: '🎭' },
  { id: 'search', label: 'Cari', icon: '🔍' },
  { id: 'playlist', label: 'Playlist', icon: '🎵' },
  { id: 'similar', label: 'Mirip', icon: '🔄' }
]

let searchTimeout

const fetchMood = async () => {
  try {
    const response = await axios.get('/api/ai/mood/default')
    moodData.value = response.data
  } catch (err) {
    console.error('Failed to fetch mood:', err)
  }
}

const smartSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    if (searchQuery.value.length < 2) {
      searchResults.value = []
      searchSuggestions.value = []
      return
    }
    
    try {
      const response = await axios.post('/api/ai/search', {
        query: searchQuery.value,
        limit: 10
      })
      searchResults.value = response.data.results || []
      searchSuggestions.value = response.data.did_you_mean || []
    } catch (err) {
      console.error('Search failed:', err)
    }
  }, 300)
}

const fetchQuickPlaylists = async () => {
  try {
    const response = await axios.get('/api/ai/playlist/quick')
    quickPlaylists.value = response.data.playlists || []
  } catch (err) {
    console.error('Failed to fetch playlists:', err)
  }
}

const generatePlaylist = async (pl) => {
  try {
    const response = await axios.post('/api/ai/playlist/generate', {
      type: pl.type,
      value: pl.value || null,
      count: 15
    })
    generatedPlaylist.value = response.data
  } catch (err) {
    console.error('Failed to generate playlist:', err)
  }
}

defineExpose({ fetchSimilar: async (songId) => {
  try {
    const response = await axios.get(`/api/ai/recommend/${songId}`)
    similarSongs.value = response.data.recommendations || []
  } catch (err) {
    console.error('Failed to fetch similar:', err)
  }
}})

onMounted(() => {
  fetchMood()
  fetchQuickPlaylists()
})
</script>

<style scoped>
.ai-recommendations {
  background: white;
  border-radius: 16px;
  padding: 1.25rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.ai-icon {
  font-size: 1.5rem;
}

.ai-header h3 {
  font-size: 1rem;
  font-weight: 700;
  color: #1f2937;
}

.ai-badge {
  font-size: 0.65rem;
  padding: 0.15rem 0.5rem;
  background: linear-gradient(135deg, #fef2f2, #eff6ff);
  color: #3b82f6;
  border-radius: 10px;
  font-weight: 600;
  margin-left: auto;
}

.ai-tabs {
  display: flex;
  gap: 0.25rem;
  margin-bottom: 1rem;
  background: #f3f4f6;
  border-radius: 10px;
  padding: 0.25rem;
}

.ai-tabs button {
  flex: 1;
  padding: 0.5rem;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  color: #6b7280;
  transition: all 0.2s;
}

.ai-tabs button.active {
  background: white;
  color: #ef4444;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.mood-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: linear-gradient(135deg, #fef2f2, #eff6ff);
  padding: 1rem;
  border-radius: 12px;
  margin-bottom: 0.75rem;
}

.mood-emoji {
  font-size: 2.5rem;
}

.mood-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #6b7280;
}

.mood-value {
  font-size: 1.2rem;
  font-weight: 700;
  color: #1f2937;
  text-transform: capitalize;
}

.mood-confidence {
  font-size: 0.75rem;
  color: #9ca3af;
}

.mood-suggestion {
  background: #fffbeb;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #92400e;
  margin-bottom: 0.75rem;
}

.refresh-mood {
  width: 100%;
  padding: 0.5rem;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #4b5563;
}

.ai-search-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 0.9rem;
  transition: all 0.3s;
}

.ai-search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.suggestions {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.suggest-label {
  font-size: 0.7rem;
  color: #9ca3af;
}

.suggest-chip {
  padding: 0.25rem 0.75rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 15px;
  cursor: pointer;
  font-size: 0.75rem;
  color: #3b82f6;
}

.search-results {
  margin-top: 0.75rem;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.search-result-item:hover {
  background: #f9fafb;
}

.result-score {
  background: #10b981;
  color: white;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
}

.result-title {
  font-weight: 600;
  font-size: 0.85rem;
  color: #1f2937;
}

.result-artist {
  font-size: 0.75rem;
  color: #6b7280;
}

.quick-playlists {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.playlist-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.playlist-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
}

.pl-icon {
  font-size: 1.5rem;
}

.pl-name {
  font-size: 0.7rem;
  font-weight: 500;
  color: #4b5563;
  text-align: center;
}

.generated-playlist {
  background: #f9fafb;
  border-radius: 12px;
  padding: 1rem;
}

.generated-playlist h4 {
  font-size: 0.95rem;
  margin-bottom: 0.75rem;
}

.pl-song {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0;
  font-size: 0.8rem;
  cursor: pointer;
}

.pl-song:hover {
  color: #ef4444;
}

.add-pl-btn {
  width: 24px;
  height: 24px;
  background: #ef4444;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
}

.similar-hint {
  font-size: 0.8rem;
  color: #9ca3af;
  margin-bottom: 0.75rem;
}

.similar-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 8px;
}

.similar-score {
  background: #8b5cf6;
  color: white;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
}

.similar-title {
  font-weight: 600;
  font-size: 0.85rem;
}

.similar-reason {
  font-size: 0.7rem;
  color: #6b7280;
}

.add-similar-btn {
  margin-left: auto;
  width: 28px;
  height: 28px;
  background: #8b5cf6;
  border: none;
  border-radius: 6px;
  color: white;
  cursor: pointer;
}
</style>
