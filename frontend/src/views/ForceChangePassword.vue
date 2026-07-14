<template>
  <div class="force-change-page">
    <div class="change-card">
      <!-- Header -->
      <div class="card-header">
        <div class="header-icon">🔐</div>
        <h1>Ganti Password</h1>
        <p>Demi keamanan, Anda harus mengganti password sebelum melanjutkan.</p>
      </div>

      <!-- Alert Messages -->
      <div v-if="errorMsg" class="alert alert-error">
        <span>⚠️</span> {{ errorMsg }}
      </div>
      <div v-if="successMsg" class="alert alert-success">
        <span>✅</span> {{ successMsg }}
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="change-form">
        <!-- New Password -->
        <div class="form-group">
          <label>Password Baru</label>
          <div class="input-wrap">
            <span class="input-icon">🔒</span>
            <input 
              v-model="newPassword" 
              :type="showNew ? 'text' : 'password'"
              placeholder="Masukkan password baru"
              class="form-input"
              @input="checkStrength"
            />
            <button type="button" @click="showNew = !showNew" class="toggle-btn">
              {{ showNew ? '🙈' : '👁️' }}
            </button>
          </div>
        </div>

        <!-- Password Strength Indicator -->
        <div class="strength-section" v-if="newPassword">
          <div class="strength-bar">
            <div class="strength-fill" :style="{ width: strength.score + '%', background: strengthColor }"></div>
          </div>
          <span class="strength-label" :style="{ color: strengthColor }">
            {{ strength.level === 'weak' ? 'Lemah' : strength.level === 'medium' ? 'Cukup' : 'Kuat' }}
          </span>
          
          <!-- Checklist -->
          <div class="checklist">
            <div v-for="check in checks" :key="check.key" class="check-item" :class="{ pass: check.pass }">
              <span class="check-icon">{{ check.pass ? '✅' : '⬜' }}</span>
              <span>{{ check.label }}</span>
            </div>
          </div>
        </div>

        <!-- Confirm Password -->
        <div class="form-group">
          <label>Konfirmasi Password Baru</label>
          <div class="input-wrap">
            <span class="input-icon">✅</span>
            <input 
              v-model="confirmPassword" 
              :type="showConfirm ? 'text' : 'password'"
              placeholder="Ulangi password baru"
              class="form-input"
              :class="{ 'input-error': confirmPassword && newPassword !== confirmPassword }"
            />
          </div>
          <span v-if="confirmPassword && newPassword !== confirmPassword" class="field-error">
            Password tidak cocok
          </span>
        </div>

        <!-- Submit -->
        <button type="submit" class="btn-submit" :disabled="!canSubmit || loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>🔒 Simpan Password Baru</span>
        </button>
      </form>

      <!-- Security Note -->
      <div class="security-note">
        <span>🛡️</span>
        <p>Password Anda dienkripsi dengan standar industri (bcrypt). Tidak ada yang bisa melihat password Anda, termasuk administrator sistem.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const newPassword = ref('')
const confirmPassword = ref('')
const showNew = ref(false)
const showConfirm = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')
const strength = ref({ score: 0, level: 'weak', checks: {} })

const checks = computed(() => [
  { key: 'length_8', label: 'Minimal 8 karakter', pass: strength.value.checks?.length_8 || false },
  { key: 'has_uppercase', label: 'Huruf besar (A-Z)', pass: strength.value.checks?.has_uppercase || false },
  { key: 'has_lowercase', label: 'Huruf kecil (a-z)', pass: strength.value.checks?.has_lowercase || false },
  { key: 'has_number', label: 'Angka (0-9)', pass: strength.value.checks?.has_number || false },
  { key: 'has_special', label: 'Karakter spesial (!@#$%)', pass: strength.value.checks?.has_special || false },
])

const strengthColor = computed(() => {
  if (strength.value.level === 'strong') return '#10b981'
  if (strength.value.level === 'medium') return '#f59e0b'
  return '#ef4444'
})

const canSubmit = computed(() => {
  return strength.value.level !== 'weak' && 
         newPassword.value === confirmPassword.value && 
         newPassword.value.length >= 8
})

const tempToken = computed(() => {
  return route.query.temp_token || ''
})

async function checkStrength() {
  if (!newPassword.value) {
    strength.value = { score: 0, level: 'weak', checks: {} }
    return
  }
  
  try {
    const res = await axios.post('/api/auth/check-password-strength', {
      new_password: newPassword.value,
      confirm_password: newPassword.value
    })
    strength.value = res.data.score
  } catch(e) {
    // Fallback: local check
    let score = 0
    const p = newPassword.value
    if (p.length >= 8) score += 20
    if (p.length >= 12) score += 15
    if (/[A-Z]/.test(p)) score += 20
    if (/[a-z]/.test(p)) score += 15
    if (/[0-9]/.test(p)) score += 15
    if (/[!@#$%^&*]/.test(p)) score += 15
    strength.value = {
      score: Math.min(score, 100),
      level: score < 40 ? 'weak' : score < 70 ? 'medium' : 'strong',
      checks: {
        length_8: p.length >= 8,
        length_12: p.length >= 12,
        has_uppercase: /[A-Z]/.test(p),
        has_lowercase: /[a-z]/.test(p),
        has_number: /[0-9]/.test(p),
        has_special: /[!@#$%^&*]/.test(p),
      }
    }
  }
}

async function handleSubmit() {
  if (!canSubmit.value) return
  
  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''
  
  try {
    const token = localStorage.getItem('temp_token') || tempToken.value
    
    const res = await axios.post('/api/auth/force-change-password', {
      new_password: newPassword.value,
      confirm_password: confirmPassword.value
    }, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    // Simpan access token baru
    localStorage.setItem('auth_token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    localStorage.removeItem('temp_token')
    
    successMsg.value = 'Password berhasil diubah! Mengalihkan...'
    
    setTimeout(() => {
      router.push('/admin')
    }, 1500)
    
  } catch(err) {
    errorMsg.value = err.response?.data?.detail || 'Gagal mengubah password. Coba lagi.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Cek apakah ada temp_token dari login response
  const token = route.query.temp_token
  if (token) {
    localStorage.setItem('temp_token', token)
  }
})
</script>

<style scoped>
.force-change-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
  padding: 1rem;
}

.change-card {
  background: white;
  border-radius: 20px;
  padding: 2.5rem 2rem;
  max-width: 460px;
  width: 100%;
  box-shadow: 0 25px 50px rgba(0,0,0,0.1);
}

.card-header {
  text-align: center;
  margin-bottom: 2rem;
}

.header-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 0.75rem;
}

.card-header h1 {
  font-size: 1.5rem;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.card-header p {
  color: #64748b;
  font-size: 0.9rem;
  line-height: 1.5;
}

/* Alerts */
.alert {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  margin-bottom: 1rem;
  font-size: 0.85rem;
  font-weight: 500;
}

.alert-error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.alert-success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

/* Form */
.change-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 0.75rem;
  z-index: 1;
}

.form-input {
  width: 100%;
  padding: 0.7rem 2.5rem 0.7rem 2.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
}

.form-input.input-error {
  border-color: #ef4444;
}

.toggle-btn {
  position: absolute;
  right: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
}

.field-error {
  font-size: 0.75rem;
  color: #ef4444;
  font-weight: 500;
}

/* Strength */
.strength-section {
  background: #f8fafc;
  padding: 0.75rem;
  border-radius: 8px;
}

.strength-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.35rem;
}

.strength-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.strength-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.checklist {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  color: #94a3b8;
}

.check-item.pass {
  color: #16a34a;
}

.check-icon {
  font-size: 0.8rem;
}

/* Submit */
.btn-submit {
  width: 100%;
  padding: 0.8rem;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(59,130,246,0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Security Note */
.security-note {
  display: flex;
  gap: 0.5rem;
  margin-top: 1.5rem;
  padding: 0.75rem;
  background: #f0fdf4;
  border-radius: 8px;
  font-size: 0.75rem;
  color: #16a34a;
  line-height: 1.4;
}
</style>
