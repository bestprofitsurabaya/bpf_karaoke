<template>
  <div class="login-page">
    <!-- Background Decoration -->
    <div class="login-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>

    <!-- Login Card -->
    <div class="login-container">
      <div class="login-card">
        <!-- Logo & Header -->
        <div class="login-header">
          <img src="/icons/icon-512x512.png" alt="BPF Karaoke" class="login-logo" />
          <h1 class="login-title">
            <span class="text-red">BPF</span>
            <span class="text-blue"> Karaoke</span>
          </h1>
          <p class="login-subtitle">Admin Panel Login</p>
        </div>

        <!-- Error Alert -->
        <div v-if="errorMessage" class="alert alert-error animate-shake">
          <span class="alert-icon">⚠️</span>
          <span>{{ errorMessage }}</span>
          <button @click="errorMessage = ''" class="alert-close">×</button>
        </div>

        <!-- Success Alert -->
        <div v-if="successMessage" class="alert alert-success">
          <span class="alert-icon">✅</span>
          <span>{{ successMessage }}</span>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="login-form" v-if="!showChangePassword">
          <div class="form-group">
            <label for="username" class="form-label">Username</label>
            <div class="input-wrapper">
              <span class="input-icon">👤</span>
              <input
                id="username"
                v-model="username"
                type="text"
                placeholder="Masukkan username"
                class="form-input"
                :class="{ 'input-error': fieldErrors.username }"
                required
                autocomplete="username"
                :disabled="isLoading"
              />
            </div>
            <span v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</span>
          </div>

          <div class="form-group">
            <label for="password" class="form-label">Password</label>
            <div class="input-wrapper">
              <span class="input-icon">🔒</span>
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="Masukkan password"
                class="form-input"
                :class="{ 'input-error': fieldErrors.password }"
                required
                autocomplete="current-password"
                :disabled="isLoading"
              />
              <button type="button" @click="showPassword = !showPassword" class="toggle-password">
                {{ showPassword ? '🙈' : '👁️' }}
              </button>
            </div>
            <span v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</span>
          </div>

          <button type="submit" class="btn-login" :disabled="isLoading">
            <span v-if="isLoading" class="spinner"></span>
            <span v-else>🔐 Masuk</span>
          </button>
        </form>

        <!-- Change Password Form -->
        <form @submit.prevent="handleChangePassword" class="login-form" v-else>
          <h3 class="form-section-title">🔑 Ganti Password</h3>
          
          <div class="form-group">
            <label class="form-label">Password Lama</label>
            <div class="input-wrapper">
              <span class="input-icon">🔒</span>
              <input
                v-model="oldPassword"
                :type="showOldPass ? 'text' : 'password'"
                placeholder="Password saat ini"
                class="form-input"
                required
                :disabled="isLoading"
              />
              <button type="button" @click="showOldPass = !showOldPass" class="toggle-password">
                {{ showOldPass ? '🙈' : '👁️' }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Password Baru</label>
            <div class="input-wrapper">
              <span class="input-icon">✨</span>
              <input
                v-model="newPassword"
                :type="showNewPass ? 'text' : 'password'"
                placeholder="Minimal 8 karakter"
                class="form-input"
                required
                :disabled="isLoading"
                @input="checkPasswordStrength"
              />
            </div>
            <!-- Password Strength Indicator -->
            <div class="password-strength" v-if="newPassword">
              <div class="strength-bar">
                <div class="strength-fill" :style="{ width: passwordStrength + '%', background: strengthColor }"></div>
              </div>
              <span class="strength-text" :style="{ color: strengthColor }">{{ strengthLabel }}</span>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Konfirmasi Password Baru</label>
            <div class="input-wrapper">
              <span class="input-icon">✅</span>
              <input
                v-model="confirmPassword"
                :type="showConfirmPass ? 'text' : 'password'"
                placeholder="Ulangi password baru"
                class="form-input"
                :class="{ 'input-error': confirmPassword && newPassword !== confirmPassword }"
                required
                :disabled="isLoading"
              />
            </div>
            <span v-if="confirmPassword && newPassword !== confirmPassword" class="field-error">
              Password tidak cocok
            </span>
          </div>

          <div class="form-actions">
            <button type="button" @click="showChangePassword = false" class="btn-cancel">
              ← Kembali
            </button>
            <button type="submit" class="btn-save" :disabled="isLoading">
              <span v-if="isLoading" class="spinner"></span>
              <span v-else>💾 Simpan</span>
            </button>
          </div>
        </form>

        <!-- Footer -->
        <div class="login-footer">
          <button v-if="!showChangePassword" @click="showChangePassword = true" class="link-btn">
            🔑 Ganti Password
          </button>
          <router-link to="/" class="link-btn">🏠 Kembali ke Home</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

// State
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const fieldErrors = ref({})

// Change Password State
const showChangePassword = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showOldPass = ref(false)
const showNewPass = ref(false)
const showConfirmPass = ref(false)

// Password Strength
const passwordStrength = ref(0)
const strengthLabel = ref('')
const strengthColor = ref('#ef4444')

// Methods
const checkPasswordStrength = () => {
  const pwd = newPassword.value
  let strength = 0
  
  if (pwd.length >= 8) strength += 25
  if (pwd.length >= 12) strength += 10
  if (/[A-Z]/.test(pwd)) strength += 20
  if (/[0-9]/.test(pwd)) strength += 20
  if (/[^A-Za-z0-9]/.test(pwd)) strength += 25
  
  passwordStrength.value = Math.min(strength, 100)
  
  if (strength < 40) {
    strengthLabel.value = 'Lemah'
    strengthColor.value = '#ef4444'
  } else if (strength < 70) {
    strengthLabel.value = 'Cukup'
    strengthColor.value = '#f59e0b'
  } else {
    strengthLabel.value = 'Kuat'
    strengthColor.value = '#10b981'
  }
}

const validateLoginForm = () => {
  fieldErrors.value = {}
  if (!username.value.trim()) {
    fieldErrors.value.username = 'Username harus diisi'
  }
  if (!password.value) {
    fieldErrors.value.password = 'Password harus diisi'
  }
  return Object.keys(fieldErrors.value).length === 0
}

const handleLogin = async () => {
  if (!validateLoginForm()) return
  
  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const response = await axios.post('/api/auth/login', {
      username: username.value,
      password: password.value
    })
    
    localStorage.setItem('auth_token', response.data.access_token)
    localStorage.setItem('user', JSON.stringify(response.data.user))
    
    successMessage.value = 'Login berhasil! Mengalihkan...'
    
    setTimeout(() => {
      router.push('/admin')
    }, 1000)
    
  } catch (err) {
    if (err.response?.status === 401) {
      errorMessage.value = 'Username atau password salah'
    } else if (err.response?.status === 429) {
      errorMessage.value = 'Terlalu banyak percobaan. Coba lagi nanti.'
    } else {
      errorMessage.value = 'Gagal terhubung ke server. Periksa koneksi.'
    }
  } finally {
    isLoading.value = false
  }
}

const handleChangePassword = async () => {
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = 'Password baru tidak cocok'
    return
  }
  
  if (!newPassword.value || newPassword.value.length < 8) {
    errorMessage.value = 'Password minimal 8 karakter'
    return
  }
  
  isLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      errorMessage.value = 'Session expired. Silakan login ulang.'
      isLoading.value = false
      return
    }
    
    const res = await axios.post('/api/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
      confirm_password: confirmPassword.value
    }, {
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    if (res.data && res.data.message) {
      successMessage.value = res.data.message
      showChangePassword.value = false
      oldPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
    }
    
  } catch (err) {
    if (err.response?.status === 401) {
      errorMessage.value = 'Password lama salah atau session expired'
    } else if (err.response?.data?.detail) {
      errorMessage.value = err.response.data.detail
    } else {
      errorMessage.value = 'Gagal mengubah password. Coba lagi.'
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 50%, #fef2f2 100%);
}

/* Background Animation */
.login-bg { position: absolute; inset: 0; overflow: hidden; }
.bg-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.15;
  animation: float 8s ease-in-out infinite;
}
.bg-circle-1 { width: 400px; height: 400px; background: #ef4444; top: -100px; right: -100px; }
.bg-circle-2 { width: 300px; height: 300px; background: #3b82f6; bottom: -80px; left: -80px; animation-delay: 2s; }
.bg-circle-3 { width: 200px; height: 200px; background: #8b5cf6; top: 50%; left: 50%; animation-delay: 4s; }
@keyframes float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-20px) scale(1.05); }
}

/* Login Card */
.login-container { position: relative; z-index: 1; width: 100%; max-width: 420px; padding: 1rem; }
.login-card {
  background: white;
  border-radius: 20px;
  padding: 2.5rem 2rem;
  box-shadow: 0 25px 50px rgba(0,0,0,0.1);
  animation: fadeInUp 0.6s ease-out;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-header { text-align: center; margin-bottom: 2rem; }
.login-logo {
  width: 80px; height: 80px;
  border-radius: 16px;
  object-fit: contain;
  background: white;
  padding: 8px;
  box-shadow: 0 4px 15px rgba(239,68,68,0.2);
  margin-bottom: 1rem;
}
.login-title { font-size: 1.8rem; font-weight: 900; }
.text-red { color: #ef4444; }
.text-blue { color: #3b82f6; }
.login-subtitle { color: #6b7280; font-size: 0.9rem; margin-top: 0.25rem; }

/* Alerts */
.alert {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.75rem 1rem; border-radius: 10px;
  margin-bottom: 1rem; font-size: 0.85rem; font-weight: 500;
}
.alert-error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.alert-success { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.alert-icon { font-size: 1rem; }
.alert-close { margin-left: auto; background: none; border: none; cursor: pointer; font-size: 1.2rem; }
.animate-shake { animation: shake 0.5s ease-in-out; }
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* Form */
.login-form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.35rem; }
.form-label { font-size: 0.85rem; font-weight: 600; color: #374151; }
.input-wrapper { position: relative; display: flex; align-items: center; }
.input-icon { position: absolute; left: 0.75rem; font-size: 1rem; z-index: 1; }
.form-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  font-size: 0.95rem;
  transition: all 0.3s;
  background: #f9fafb;
}
.form-input:focus { outline: none; border-color: #ef4444; background: white; box-shadow: 0 0 0 3px rgba(239,68,68,0.1); }
.form-input.input-error { border-color: #ef4444; }
.form-input:disabled { opacity: 0.6; cursor: not-allowed; }
.toggle-password {
  position: absolute; right: 0.75rem;
  background: none; border: none; cursor: pointer; font-size: 1.1rem;
}
.field-error { font-size: 0.75rem; color: #ef4444; font-weight: 500; }

/* Password Strength */
.password-strength { display: flex; align-items: center; gap: 0.5rem; }
.strength-bar { flex: 1; height: 4px; background: #e5e7eb; border-radius: 2px; overflow: hidden; }
.strength-fill { height: 100%; border-radius: 2px; transition: all 0.3s; }
.strength-text { font-size: 0.7rem; font-weight: 600; }

/* Buttons */
.btn-login {
  width: 100%; padding: 0.875rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white; border: none; border-radius: 10px;
  font-size: 1rem; font-weight: 600; cursor: pointer;
  transition: all 0.3s; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
}
.btn-login:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(239,68,68,0.3); }
.btn-login:disabled { opacity: 0.6; cursor: not-allowed; }

.form-section-title { font-size: 1.1rem; font-weight: 700; color: #1f2937; }
.form-actions { display: flex; gap: 0.75rem; }
.btn-cancel, .btn-save {
  flex: 1; padding: 0.75rem; border-radius: 10px;
  font-weight: 600; cursor: pointer; transition: all 0.3s;
  display: flex; align-items: center; justify-content: center;
}
.btn-cancel { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
.btn-save { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: none; }
.btn-save:hover:not(:disabled) { box-shadow: 0 4px 15px rgba(59,130,246,0.3); }
.btn-save:disabled { opacity: 0.6; }

.login-footer { display: flex; justify-content: center; gap: 1rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #f3f4f6; }
.link-btn { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 0.85rem; text-decoration: none; }
.link-btn:hover { color: #ef4444; }

/* Spinner */
.spinner {
  width: 20px; height: 20px;
  border: 3px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 480px) {
  .login-card { padding: 1.5rem; }
  .login-title { font-size: 1.5rem; }
}
</style>
