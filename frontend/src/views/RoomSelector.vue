<template>
  <div class="room-selector-page">
    <div class="ambient ambient-1"></div>
    <div class="ambient ambient-2"></div>

    <div class="selector-container">
      <div class="brand-block">
        <div class="logo-wrap">
          <img src="/icons/icon-512x512.png" alt="BPF" class="selector-logo" />
          <span class="logo-ring"></span>
        </div>
        <h1>BPF <span>Karaoke</span></h1>
        <p class="subtitle">Pilih Room untuk memulai</p>
      </div>

      <div class="room-grid" v-if="rooms.length">
        <div v-for="room in rooms" :key="room.name"
             class="room-card" :class="{ busy: room.session_status === 'active' }">
          <div class="room-top">
            <div class="room-icon">{{ room.session_status === 'active' ? '🔴' : '🟢' }}</div>
            <div class="room-meta">
              <h3>{{ room.name }}</h3>
              <p v-if="room.description">{{ room.description }}</p>
            </div>
            <span class="session-badge" :class="{ active: room.session_status === 'active' }">
              <template v-if="room.session_status === 'active'">
                Sisa {{ formatRemaining(room.session_remaining_seconds) }}
              </template>
              <template v-else>Kosong</template>
            </span>
          </div>

          <div class="room-stats">
            <span class="stat" :title="'Kapasitas room'">👥 {{ room.capacity }} orang</span>
            <span class="stat" :title="'Lagu dalam antrian'">🎵 {{ room.queue_count || 0 }} antrian</span>
          </div>

          <div class="room-links">
            <a :href="`/player?screen=2&room=${encodeURIComponent(room.name)}`"
               target="_blank" class="room-link player">
              📺 Player
            </a>
            <a :href="`/remote?room=${encodeURIComponent(room.name)}`"
               target="_blank" class="room-link remote">
              📱 Remote
            </a>
            <a :href="`/operator?screen=1&room=${encodeURIComponent(room.name)}`"
               class="room-link operator">
              🖥️
            </a>
          </div>
        </div>
      </div>
      <div v-else class="rooms-empty">Memuat room...</div>

      <a href="/operator?screen=1" class="operator-link">🖥️ Buka Operator (Semua Room)</a>
      <p class="footer-note">BPF Karaoke · Best Profit Futures Entertainment</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const rooms = ref([])
let refreshTimer = null

function formatRemaining(secs) {
  secs = Math.max(0, Math.floor(secs || 0))
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m} mnt ${String(s).padStart(2, '0')} dtk`
}

async function loadRooms() {
  try {
    const res = await axios.get('/api/rooms/active')
    rooms.value = res.data.rooms || []
  } catch(e) {
    // Fallback jika API belum siap
    rooms.value = [
      { name: 'Room 1', description: 'VIP Room', capacity: 10 },
      { name: 'Room 2', description: 'Regular', capacity: 8 },
      { name: 'Room 3', description: 'Family', capacity: 15 },
    ]
  }
}

onMounted(async () => {
  await loadRooms()
  // Auto-refresh status sesi & antrian tiap 20 detik
  refreshTimer = setInterval(loadRooms, 20000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style scoped>
.room-selector-page {
  min-height: 100vh;
  background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 45%, #2e1065 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  position: relative;
  overflow: hidden;
}

/* Ambient glow */
.ambient {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.35;
  pointer-events: none;
}
.ambient-1 { width: 420px; height: 420px; background: #ef4444; top: -120px; left: -80px; }
.ambient-2 { width: 420px; height: 420px; background: #3b82f6; bottom: -120px; right: -80px; }

.selector-container {
  text-align: center;
  max-width: 760px;
  width: 100%;
  position: relative;
  z-index: 1;
}

.brand-block { margin-bottom: 2rem; }
.logo-wrap { position: relative; display: inline-block; margin-bottom: 1rem; }
.selector-logo {
  width: 84px;
  height: 84px;
  border-radius: 20px;
  object-fit: contain;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  padding: 12px;
  position: relative;
  z-index: 1;
}
.logo-ring {
  position: absolute;
  inset: -8px;
  border-radius: 26px;
  border: 2px solid rgba(239,68,68,0.35);
  animation: ringPulse 2.6s ease-out infinite;
}
@keyframes ringPulse {
  0% { transform: scale(0.95); opacity: 0.7; }
  100% { transform: scale(1.25); opacity: 0; }
}

h1 { font-size: 2.4rem; font-weight: 900; color: white; letter-spacing: -0.5px; }
h1 span { background: linear-gradient(90deg, #ef4444, #3b82f6); -webkit-background-clip: text; background-clip: text; color: transparent; }
.subtitle { color: rgba(255,255,255,0.45); font-size: 0.95rem; margin-top: 0.3rem; }

.room-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 1rem;
  margin-bottom: 1.75rem;
  text-align: left;
}

.room-card {
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 18px;
  padding: 1.1rem 1.2rem;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
  animation: cardIn 0.4s ease-out backwards;
}
.room-card:nth-child(2) { animation-delay: 0.08s; }
.room-card:nth-child(3) { animation-delay: 0.16s; }
.room-card:nth-child(4) { animation-delay: 0.24s; }
@keyframes cardIn { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }

.room-card:hover {
  transform: translateY(-3px);
  border-color: rgba(239,68,68,0.45);
  box-shadow: 0 14px 34px rgba(0,0,0,0.35);
}
.room-card.busy {
  border-color: rgba(239,68,68,0.5);
  background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(255,255,255,0.05));
}

.room-top { display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.6rem; }
.room-icon { font-size: 1.5rem; }
.room-meta { flex: 1; min-width: 0; }
.room-meta h3 { font-size: 1.05rem; font-weight: 700; color: white; }
.room-meta p { font-size: 0.75rem; color: rgba(255,255,255,0.4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.session-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.25rem 0.7rem;
  border-radius: 1rem;
  background: rgba(16,185,129,0.15);
  color: #34d399;
  white-space: nowrap;
  border: 1px solid rgba(16,185,129,0.3);
}
.session-badge.active {
  background: rgba(239,68,68,0.15);
  color: #f87171;
  border-color: rgba(239,68,68,0.4);
  animation: busyPulse 1.6s ease-in-out infinite;
}
@keyframes busyPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.35); }
  50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); }
}

.room-stats { display: flex; gap: 0.9rem; margin-bottom: 0.9rem; }
.stat { font-size: 0.72rem; color: rgba(255,255,255,0.55); }

.room-links { display: flex; gap: 0.5rem; }
.room-link {
  padding: 0.45rem 0.9rem;
  border-radius: 10px;
  text-decoration: none;
  font-size: 0.78rem;
  font-weight: 700;
  color: white;
  transition: transform 0.15s, opacity 0.2s;
  flex: 1;
  text-align: center;
}
.room-link:hover { opacity: 0.88; transform: translateY(-1px); }
.room-link.player { background: linear-gradient(135deg, #ef4444, #dc2626); }
.room-link.remote { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.room-link.operator { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15); flex: 0 0 auto; padding: 0.45rem 0.7rem; }

.rooms-empty { color: rgba(255,255,255,0.4); padding: 2rem; }

.operator-link {
  display: inline-block;
  padding: 0.8rem 2.2rem;
  background: linear-gradient(135deg, rgba(239,68,68,0.9), rgba(220,38,38,0.9));
  color: white;
  border-radius: 2rem;
  text-decoration: none;
  font-weight: 700;
  font-size: 0.9rem;
  box-shadow: 0 12px 30px rgba(239,68,68,0.35);
  transition: transform 0.2s, box-shadow 0.2s;
}
.operator-link:hover { transform: translateY(-2px); box-shadow: 0 16px 40px rgba(239,68,68,0.45); }

.footer-note { color: rgba(255,255,255,0.25); font-size: 0.7rem; margin-top: 1.5rem; }

@media (max-width: 520px) {
  .room-grid { grid-template-columns: 1fr; }
  h1 { font-size: 1.9rem; }
}
</style>
