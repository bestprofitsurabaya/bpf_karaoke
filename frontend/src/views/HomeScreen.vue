<template>
  <div class="home-screen">
    <!-- Navigation -->
    <nav class="home-nav">
      <div class="nav-brand">
        <span class="brand-icon">🎤</span>
        <span class="brand-text">
          <span class="text-red">BPF</span>
          <span class="text-blue">Karaoke</span>
        </span>
      </div>
      <div class="nav-links">
        <a href="#features" class="nav-link">Fitur</a>
        <a href="#roles" class="nav-link">Panduan</a>
        <router-link to="/admin" class="nav-link">Admin</router-link>
      </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-pulse"></span>
          Sistem Karaoke Modern
        </div>
        <h1 class="hero-title">
          Nyanyi Tanpa Batas,<br>
          <span class="gradient-text">Kontrol Tanpa Ribet</span>
        </h1>
        <p class="hero-desc">
          Sistem karaoke profesional dengan dual-screen, remote control via smartphone,
          dan manajemen lagu yang mudah. Hadirkan pengalaman karaoke terbaik untuk pelanggan Anda.
        </p>
        <div class="hero-actions">
          <router-link to="/operator?screen=1" class="btn-hero-primary">
            <span>🖥️</span> Mulai Operasi
          </router-link>
          <router-link to="/remote" class="btn-hero-secondary">
            <span>📱</span> Coba Remote
          </router-link>
        </div>
      </div>
      <div class="hero-visual">
        <div class="hero-card-stack">
          <div class="hero-card card-1">
            <div class="card-inner">
              <span class="card-emoji">🎵</span>
              <span>1000+ Lagu</span>
            </div>
          </div>
          <div class="hero-card card-2">
            <div class="card-inner">
              <span class="card-emoji">📱</span>
              <span>Remote HP</span>
            </div>
          </div>
          <div class="hero-card card-3">
            <div class="card-inner">
              <span class="card-emoji">🖥️</span>
              <span>Dual Screen</span>
            </div>
          </div>
        </div>
        <div class="hero-circle"></div>
      </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="features-section">
      <h2 class="section-title">Fitur <span class="gradient-text">Unggulan</span></h2>
      <div class="features-grid">
        <div class="feature-card" v-for="feature in features" :key="feature.title">
          <div class="feature-icon" :style="{ background: feature.gradient }">
            {{ feature.icon }}
          </div>
          <h3>{{ feature.title }}</h3>
          <p>{{ feature.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Roles Guide Section -->
    <section id="roles" class="roles-section">
      <h2 class="section-title">Panduan <span class="gradient-text">Pengguna</span></h2>
      <div class="roles-grid">
        <div class="role-card" v-for="role in roles" :key="role.name">
          <div class="role-header" :style="{ background: role.gradient }">
            <span class="role-icon">{{ role.icon }}</span>
            <h3>{{ role.name }}</h3>
          </div>
          <div class="role-body">
            <ul>
              <li v-for="step in role.steps" :key="step">
                <span class="step-dot"></span>
                {{ step }}
              </li>
            </ul>
            <router-link :to="role.link" class="role-btn">
              {{ role.btnText }}
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="home-footer">
      <p>© 2026 IT BPF Surabaya - PT BESTPROFIT FUTURES SURABAYA. All rights reserved.</p>
      <p class="footer-sub">Powered by Vue 3 + FastAPI + Socket.IO</p>
    </footer>
  </div>
</template>

<script setup>
const features = [
  {
    icon: '🖥️',
    title: 'Dual Screen',
    desc: 'Layar operator touchscreen dan layar TV terpisah. Operator bisa mencari lagu tanpa mengganggu tampilan karaoke.',
    gradient: 'linear-gradient(135deg, #ef4444, #dc2626)'
  },
  {
    icon: '📱',
    title: 'Remote Smartphone',
    desc: 'Pelanggan bisa request lagu langsung dari HP mereka. Cukup scan QR code, tanpa install aplikasi.',
    gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)'
  },
  {
    icon: '🎤',
    title: 'Vocal Control',
    desc: 'Fitur menghilangkan vokal penyanyi asli. Bisa pilih channel kiri, kanan, atau stereo sesuai kebutuhan.',
    gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)'
  },
  {
    icon: '📋',
    title: 'Smart Queue',
    desc: 'Antrian lagu yang bisa diatur ulang, skip, atau pause. Dilengkapi riwayat lagu yang sudah diputar.',
    gradient: 'linear-gradient(135deg, #f59e0b, #d97706)'
  },
  {
    icon: '🔍',
    title: 'Smart Search',
    desc: 'Pencarian lagu super cepat dengan toleransi typo. Filter berdasarkan genre, bahasa, atau penyanyi.',
    gradient: 'linear-gradient(135deg, #10b981, #059669)'
  },
  {
    icon: '📊',
    title: 'Dashboard Admin',
    desc: 'Pantau statistik pemutaran, scan lagu baru otomatis, dan kelola semua konten dari satu panel.',
    gradient: 'linear-gradient(135deg, #ec4899, #db2777)'
  }
]

const roles = [
  {
    name: 'Operator / Kasir',
    icon: '🖥️',
    gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
    steps: [
      'Buka halaman Operator Screen',
      'Gunakan touchscreen untuk mencari lagu',
      'Klik lagu untuk menambahkan ke antrian',
      'Atur urutan antrian dengan drag & drop',
      'Play, pause, atau skip lagu yang sedang diputar'
    ],
    link: '/operator?screen=1',
    btnText: '🎵 Buka Operator Screen'
  },
  {
    name: 'Pelanggan / Tamu',
    icon: '📱',
    gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    steps: [
      'Scan QR Code yang muncul di layar TV',
      'Buka halaman Remote di browser HP',
      'Cari lagu favorit Anda',
      'Klik tombol + untuk request lagu',
      'Lagu akan masuk antrian dan diputar bergiliran'
    ],
    link: '/remote',
    btnText: '📱 Buka Remote Control'
  },
  {
    name: 'Admin / Pengelola',
    icon: '⚙️',
    gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
    steps: [
      'Login ke Admin Panel',
      'Scan folder media untuk menambah lagu',
      'Pantau statistik pemutaran',
      'Kelola playlist dan kategori',
      'Atur pengguna dan hak akses'
    ],
    link: '/admin',
    btnText: '⚙️ Buka Admin Panel'
  }
]
</script>

<style scoped>
.home-screen {
  height: 100vh;
  overflow-y: auto;
  scroll-behavior: smooth;
}

/* Navigation */
.home-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 800;
}

.brand-icon {
  font-size: 1.5rem;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
}

.nav-link {
  text-decoration: none;
  color: #4b5563;
  font-weight: 500;
  transition: color 0.3s;
  font-size: 0.9rem;
}

.nav-link:hover {
  color: #ef4444;
}

/* Hero Section */
.hero-section {
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: 6rem 2rem 4rem;
  gap: 4rem;
}

.hero-content {
  flex: 1;
  animation: fadeInUp 0.8s ease-out;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: white;
  padding: 0.5rem 1rem;
  border-radius: 50px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #ef4444;
  box-shadow: 0 2px 10px rgba(239, 68, 68, 0.1);
  margin-bottom: 1.5rem;
}

.badge-pulse {
  width: 8px;
  height: 8px;
  background: #ef4444;
  border-radius: 50%;
  animation: pulse-glow 2s infinite;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 900;
  line-height: 1.2;
  margin-bottom: 1.5rem;
  color: #1f2937;
}

.hero-desc {
  font-size: 1.1rem;
  color: #6b7280;
  line-height: 1.7;
  margin-bottom: 2rem;
  max-width: 500px;
}

.hero-actions {
  display: flex;
  gap: 1rem;
}

.btn-hero-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 2rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border-radius: 50px;
  text-decoration: none;
  font-weight: 600;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
  transition: all 0.3s;
}

.btn-hero-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
}

.btn-hero-secondary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 2rem;
  background: white;
  color: #3b82f6;
  border-radius: 50px;
  text-decoration: none;
  font-weight: 600;
  border: 2px solid #3b82f6;
  transition: all 0.3s;
}

.btn-hero-secondary:hover {
  background: #eff6ff;
  transform: translateY(-2px);
}

.hero-visual {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-circle {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(59, 130, 246, 0.1));
  border-radius: 50%;
  position: absolute;
  animation: float 6s ease-in-out infinite;
}

.hero-card-stack {
  position: relative;
  z-index: 1;
}

.hero-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
  position: absolute;
  animation: float 4s ease-in-out infinite;
}

.hero-card.card-1 {
  top: -150px;
  left: -100px;
  animation-delay: 0s;
}

.hero-card.card-2 {
  top: -50px;
  right: -120px;
  animation-delay: 1s;
}

.hero-card.card-3 {
  bottom: -120px;
  left: -50px;
  animation-delay: 2s;
}

.card-inner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
}

.card-emoji {
  font-size: 1.5rem;
}

/* Features Section */
.features-section {
  padding: 4rem 2rem;
}

.section-title {
  text-align: center;
  font-size: 2.5rem;
  font-weight: 800;
  margin-bottom: 3rem;
  color: #1f2937;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-card {
  background: white;
  padding: 2rem;
  border-radius: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  transition: all 0.3s;
  border: 1px solid #f3f4f6;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}

.feature-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.75rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #1f2937;
}

.feature-card p {
  color: #6b7280;
  line-height: 1.6;
  font-size: 0.95rem;
}

/* Roles Section */
.roles-section {
  padding: 4rem 2rem;
  background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 100%);
}

.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.role-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0,0,0,0.08);
  transition: all 0.3s;
}

.role-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}

.role-header {
  padding: 2rem 1.5rem;
  text-align: center;
  color: white;
}

.role-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 0.5rem;
}

.role-header h3 {
  font-size: 1.5rem;
  font-weight: 700;
}

.role-body {
  padding: 1.5rem;
}

.role-body ul {
  list-style: none;
  margin-bottom: 1.5rem;
}

.role-body li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  color: #4b5563;
  font-size: 0.9rem;
}

.step-dot {
  width: 6px;
  height: 6px;
  background: #ef4444;
  border-radius: 50%;
  flex-shrink: 0;
}

.role-btn {
  display: block;
  text-align: center;
  padding: 0.75rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s;
}

.role-btn:hover {
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
}

/* Footer */
.home-footer {
  text-align: center;
  padding: 2rem;
  background: white;
  color: #9ca3af;
  font-size: 0.85rem;
}

.footer-sub {
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
    padding: 5rem 1.5rem 2rem;
    gap: 2rem;
  }
  
  .hero-title {
    font-size: 2.2rem;
  }
  
  .hero-actions {
    flex-direction: column;
  }
  
  .hero-visual {
    display: none;
  }
  
  .section-title {
    font-size: 1.8rem;
  }
}
</style>
