<template>
  <div class="room-selector-page">
    <div class="selector-container">
      <img src="/icons/icon-512x512.png" alt="BPF" class="selector-logo" />
      <h1>BPF Karaoke</h1>
      <h2>Pilih Room</h2>
      
      <div class="room-grid">
        <div v-for="room in rooms" :key="room.name" class="room-card">
          <div class="room-icon">🚪</div>
          <h3>{{ room.name }}</h3>
          <p v-if="room.description">{{ room.description }}</p>
          <span class="room-capacity">👥 {{ room.capacity }} orang</span>
          
          <div class="room-links">
            <a :href="`/player?screen=2&room=${encodeURIComponent(room.name)}`" 
               target="_blank" class="room-link player">
              📺 Player
            </a>
            <a :href="`/remote?room=${encodeURIComponent(room.name)}`" 
               target="_blank" class="room-link remote">
              📱 Remote
            </a>
          </div>
        </div>
      </div>
      
      <a href="/operator?screen=1" class="operator-link">🖥️ Buka Operator (Semua Room)</a>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const rooms = ref([])

onMounted(async () => {
  try {
    const res = await axios.get('/api/rooms/active')
    rooms.value = res.data.rooms || []
  } catch(e) {
    // Fallback
    rooms.value = [
      { name: 'Room 1', description: 'VIP Room', capacity: 10 },
      { name: 'Room 2', description: 'Regular', capacity: 8 },
      { name: 'Room 3', description: 'Family', capacity: 15 },
    ]
  }
})
</script>

<style scoped>
.room-selector-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #fef2f2, #eff6ff, #fef2f2);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.selector-container {
  text-align: center;
  max-width: 600px;
}

.selector-logo {
  width: 80px;
  height: 80px;
  border-radius: 16px;
  margin-bottom: 1rem;
}

h1 { font-size: 2rem; font-weight: 800; }
h2 { font-size: 1.2rem; color: #64748b; margin: 0.5rem 0 1.5rem; }

.room-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.room-card {
  background: white;
  border-radius: 16px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  text-align: left;
}

.room-icon { font-size: 2rem; }
.room-card h3 { font-size: 1.1rem; font-weight: 700; }
.room-card p { font-size: 0.8rem; color: #94a3b8; }
.room-capacity { font-size: 0.75rem; color: #64748b; }

.room-links {
  margin-left: auto;
  display: flex;
  gap: 0.5rem;
}

.room-link {
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 600;
  color: white;
}

.room-link.player { background: #ef4444; }
.room-link.remote { background: #3b82f6; }

.operator-link {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border-radius: 2rem;
  text-decoration: none;
  font-weight: 600;
}
</style>
