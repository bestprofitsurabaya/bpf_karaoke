<template>
  <div class="voice-scoring">
    <div class="score-header">
      <span class="score-icon">🎤</span>
      <h3>Vocal Score</h3>
      <span class="score-status" :class="{ active: isActive }">
        {{ isActive ? 'LIVE' : 'IDLE' }}
      </span>
    </div>

    <!-- Score Circle -->
    <div class="score-display">
      <svg class="score-circle" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="42" fill="none" stroke="#e5e7eb" stroke-width="8"/>
        <circle 
          cx="50" cy="50" r="42" 
          fill="none" 
          :stroke="scoreColor" 
          stroke-width="8"
          stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="scoreOffset"
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div class="score-value">
        <span class="score-number">{{ currentScore }}</span>
        <span class="score-unit">/100</span>
      </div>
    </div>

    <!-- Stars -->
    <div class="stars-display">
      <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= stars }">⭐</span>
    </div>

    <!-- Energy Bar -->
    <div class="energy-bar">
      <div class="energy-label">Energy: {{ energyLevel }}%</div>
      <div class="energy-track">
        <div 
          class="energy-fill" 
          :style="{ width: energyLevel + '%' }"
        ></div>
      </div>
    </div>

    <div class="singing-status" :class="{ singing: isActive }">
      <span class="status-indicator"></span>
      {{ isActive ? 'Sedang Bernyanyi 🎵' : 'Menunggu Vokal...' }}
    </div>

    <button @click="resetScore" class="reset-btn">🔄 Reset</button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const currentScore = ref(75)
const energyLevel = ref(65)
const isActive = ref(true)
const stars = ref(4)

const circumference = 2 * Math.PI * 42

const scoreOffset = computed(() => {
  return circumference - (currentScore.value / 100) * circumference
})

const scoreColor = computed(() => {
  if (currentScore.value >= 80) return '#10b981'
  if (currentScore.value >= 60) return '#f59e0b'
  return '#ef4444'
})

let scoreInterval

const simulateScore = () => {
  scoreInterval = setInterval(() => {
    if (Math.random() > 0.2) {
      isActive.value = true
      currentScore.value = Math.floor(Math.random() * 25) + 70
      energyLevel.value = Math.floor(Math.random() * 35) + 55
    } else {
      isActive.value = false
      energyLevel.value = Math.floor(Math.random() * 15) + 10
    }
    
    if (currentScore.value >= 90) stars.value = 5
    else if (currentScore.value >= 75) stars.value = 4
    else if (currentScore.value >= 60) stars.value = 3
    else if (currentScore.value >= 40) stars.value = 2
    else stars.value = 1
  }, 2500)
}

const resetScore = () => {
  currentScore.value = 0
  energyLevel.value = 0
  isActive.value = false
  stars.value = 0
}

onMounted(() => simulateScore())
onUnmounted(() => clearInterval(scoreInterval))
</script>

<style scoped>
.voice-scoring {
  background: white;
  border-radius: 16px;
  padding: 1.25rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  text-align: center;
}

.score-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.score-icon { font-size: 1.5rem; }

.score-header h3 {
  font-size: 1rem;
  font-weight: 700;
  color: #1f2937;
}

.score-status {
  font-size: 0.6rem;
  padding: 0.15rem 0.5rem;
  border-radius: 8px;
  font-weight: 600;
  background: #f3f4f6;
  color: #9ca3af;
}

.score-status.active {
  background: #ecfdf5;
  color: #10b981;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.score-display {
  position: relative;
  width: 130px;
  height: 130px;
  margin: 0 auto 0.75rem;
}

.score-circle { width: 100%; height: 100%; }

.score-value {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-number {
  font-size: 1.8rem;
  font-weight: 800;
  color: #1f2937;
}

.score-unit {
  font-size: 0.65rem;
  color: #9ca3af;
}

.stars-display { margin-bottom: 0.75rem; }

.star {
  font-size: 1.3rem;
  opacity: 0.2;
  transition: all 0.3s;
}

.star.filled { opacity: 1; }

.energy-bar {
  text-align: left;
  margin-bottom: 0.75rem;
}

.energy-label {
  font-size: 0.7rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.energy-track {
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.energy-fill {
  height: 100%;
  background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.singing-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #6b7280;
  margin-bottom: 0.75rem;
}

.singing-status.singing {
  background: #ecfdf5;
  color: #059669;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d1d5db;
}

.singing-status.singing .status-indicator {
  background: #10b981;
  animation: pulse 1s infinite;
}

.reset-btn {
  width: 100%;
  padding: 0.5rem;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  color: #4b5563;
}
</style>
