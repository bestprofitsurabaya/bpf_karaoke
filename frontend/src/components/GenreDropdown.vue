<template>
  <div class="genre-dropdown" ref="dropdownRef">
    <div class="dropdown-trigger" @click="isOpen = !isOpen">
      <span v-if="modelValue" class="selected-genre">
        <span class="genre-dot" :style="{ background: genreColor(modelValue) }"></span>
        {{ modelValue }}
      </span>
      <span v-else class="placeholder">{{ placeholder }}</span>
      <span class="arrow">▾</span>
    </div>
    
    <div class="dropdown-menu" v-if="isOpen">
      <!-- Search/Add new -->
      <div class="dropdown-search">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Cari atau ketik genre baru..."
          class="search-input"
          @keydown.enter="addNewGenre"
        />
        <button v-if="searchQuery && !isExactMatch" @click="addNewGenre" class="btn-add-new">
          + Buat "{{ searchQuery }}"
        </button>
      </div>
      
      <!-- Genre list -->
      <div class="dropdown-list">
        <button 
          v-for="genre in filteredGenres" 
          :key="genre.genre"
          @click="selectGenre(genre.genre)"
          class="genre-option"
          :class="{ active: modelValue === genre.genre }"
        >
          <span class="genre-dot" :style="{ background: genreColor(genre.genre) }"></span>
          <span class="genre-name">{{ genre.genre }}</span>
          <span class="genre-count">{{ genre.count }}</span>
        </button>
        
        <div v-if="filteredGenres.length === 0 && !searchQuery" class="empty-state">
          Memuat genre...
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Pilih Genre' }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const searchQuery = ref('')
const genres = ref([])
const dropdownRef = ref(null)

const filteredGenres = computed(() => {
  if (!searchQuery.value) return genres.value
  const q = searchQuery.value.toLowerCase()
  return genres.value.filter(g => g.genre.toLowerCase().includes(q))
})

const isExactMatch = computed(() => {
  return genres.value.some(g => g.genre.toLowerCase() === searchQuery.value.toLowerCase())
})

function selectGenre(genre) {
  emit('update:modelValue', genre)
  isOpen.value = false
  searchQuery.value = ''
}

function addNewGenre() {
  const newGenre = searchQuery.value.trim()
  if (newGenre) {
    emit('update:modelValue', newGenre)
    // Optimistically add to list
    if (!genres.value.find(g => g.genre === newGenre)) {
      genres.value.unshift({ genre: newGenre, count: 0, is_custom: true })
    }
    isOpen.value = false
    searchQuery.value = ''
  }
}

function genreColor(genre) {
  const colors = {
    'Pop Indonesia': '#ef4444',
    'Dangdut': '#f59e0b',
    'K-Pop': '#ec4899',
    'Barat': '#3b82f6',
    'Rock': '#1f2937',
    'Mandarin': '#dc2626',
    'Anak': '#10b981',
    'Religi': '#8b5cf6',
    'Daerah': '#f97316',
    'Jazz': '#6366f1',
    'EDM': '#06b6d4',
    'Hip Hop': '#84cc16',
    'Unknown': '#94a3b8'
  }
  return colors[genre] || '#64748b'
}

async function fetchGenres() {
  try {
    const res = await axios.get('/api/genres')
    genres.value = res.data.genres || []
  } catch(e) {
    console.error('Failed to fetch genres:', e)
  }
}

// Close on outside click
function handleClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  fetchGenres()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.genre-dropdown {
  position: relative;
  width: 100%;
}

.dropdown-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  background: white;
  transition: all 0.2s;
  min-height: 38px;
}

.dropdown-trigger:hover {
  border-color: #cbd5e1;
}

.selected-genre {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 500;
}

.placeholder {
  color: #94a3b8;
  font-size: 0.85rem;
}

.arrow {
  font-size: 0.7rem;
  color: #94a3b8;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
  z-index: 50;
  max-height: 300px;
  display: flex;
  flex-direction: column;
}

.dropdown-search {
  padding: 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.search-input {
  width: 100%;
  padding: 0.4rem 0.6rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.8rem;
}

.search-input:focus {
  outline: none;
  border-color: #ef4444;
}

.btn-add-new {
  width: 100%;
  padding: 0.35rem;
  margin-top: 0.25rem;
  background: #fef2f2;
  border: 1px dashed #fecaca;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
  color: #ef4444;
  font-weight: 600;
}

.dropdown-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem;
}

.genre-option {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.5rem;
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
}

.genre-option:hover {
  background: #f8fafc;
}

.genre-option.active {
  background: #fef2f2;
  color: #ef4444;
  font-weight: 600;
}

.genre-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.genre-name {
  flex: 1;
  text-align: left;
}

.genre-count {
  font-size: 0.65rem;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 0.1rem 0.4rem;
  border-radius: 1rem;
}

.empty-state {
  text-align: center;
  padding: 1rem;
  color: #94a3b8;
  font-size: 0.8rem;
}
</style>
