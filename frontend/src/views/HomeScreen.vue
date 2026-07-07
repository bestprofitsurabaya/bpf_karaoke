<template>
  <div class="home-screen">
    <!-- Navigation -->
    <nav class="home-nav">
      <div class="nav-brand">
        <img src="/icons/icon-512x512.png" alt="BPF" class="nav-logo" />
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
          Best Profit Futures Entertainment
        </div>
        <h1 class="hero-title">
          Karaoke Modern dengan<br>
          <span class="gradient-text">AI & Remote Control</span>
        </h1>
        <p class="hero-desc">
          Sistem karaoke profesional dengan dual-screen, remote via smartphone,
          AI recommendations, dan manajemen lagu modern.
        </p>
        <div class="hero-actions">
          <router-link to="/operator?screen=1" class="btn-hero-primary">
            🖥️ Mulai Operasi
          </router-link>
          <router-link to="/remote" class="btn-hero-secondary">
            📱 Coba Remote
          </router-link>
        </div>
      </div>
      <div class="hero-visual">
        <img src="/icons/icon-512x512.png" alt="BPF Karaoke" class="hero-logo" />
      </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="features-section">
      <h2 class="section-title">Fitur <span class="gradient-text">Unggulan</span></h2>
      <div class="features-grid">
        <div class="feature-card" v-for="f in features" :key="f.title">
          <div class="feature-icon" :style="{ background: f.gradient }">{{ f.icon }}</div>
          <h3>{{ f.title }}</h3>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Roles Section -->
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
                <span class="step-dot"></span>{{ step }}
              </li>
            </ul>
            <router-link :to="role.link" class="role-btn">{{ role.btnText }}</router-link>
          </div>
        </div>
      </div>
    </section>

    <footer class="home-footer">
      <p>© 2026 BPF Karaoke System - Best Profit Futures. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup>
const features = [
  { icon: '🖥️', title: 'Dual Screen', desc: 'Layar operator dan TV terpisah untuk pengalaman profesional.', gradient: 'linear-gradient(135deg, #ef4444, #dc2626)' },
  { icon: '📱', title: 'Remote HP', desc: 'Pelanggan request lagu dari smartphone via QR Code.', gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)' },
  { icon: '🤖', title: 'AI Smart', desc: 'Rekomendasi lagu, mood detection, dan smart search.', gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)' },
  { icon: '🎤', title: 'Vocal Control', desc: 'Hilangkan vokal penyanyi asli dengan channel switching.', gradient: 'linear-gradient(135deg, #f59e0b, #d97706)' },
  { icon: '📋', title: 'Smart Queue', desc: 'Antrian lagu fleksibel dengan drag & drop reorder.', gradient: 'linear-gradient(135deg, #10b981, #059669)' },
  { icon: '📊', title: 'Dashboard', desc: 'Statistik lengkap dan manajemen konten terpusat.', gradient: 'linear-gradient(135deg, #ec4899, #db2777)' }
]

const roles = [
  {
    name: 'Operator / Kasir', icon: '🖥️',
    gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
    steps: ['Buka Operator Screen', 'Cari lagu dengan search/filter', 'Klik untuk tambah ke antrian', 'Atur urutan & putar lagu'],
    link: '/operator?screen=1', btnText: '🎵 Buka Operator'
  },
  {
    name: 'Pelanggan / Tamu', icon: '📱',
    gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    steps: ['Scan QR di layar TV', 'Buka remote di browser HP', 'Cari & request lagu', 'Lihat antrian Anda'],
    link: '/remote', btnText: '📱 Buka Remote'
  },
  {
    name: 'Admin / Pengelola', icon: '⚙️',
    gradient: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
    steps: ['Login Admin Panel', 'Scan folder media', 'Pantau statistik', 'Kelola user & playlist'],
    link: '/admin', btnText: '⚙️ Buka Admin'
  }
]
</script>

<style scoped>
.home-screen { height: 100vh; overflow-y: auto; scroll-behavior: smooth; }

.home-nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.75rem 2rem;
  background: rgba(255,255,255,0.95); backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0,0,0,0.05);
}
.nav-brand { display: flex; align-items: center; gap: 0.6rem; }

/* SOLUSI: CSS atur ukuran logo navbar */
.nav-logo {
  width: 38px;        /* ← Ukuran kecil untuk navbar */
  height: 38px;
  border-radius: 8px;
  object-fit: contain;
  background: white;
  padding: 2px;
}

.brand-text { font-size: 1.2rem; font-weight: 800; }
.nav-links { display: flex; gap: 1.5rem; }
.nav-link { text-decoration: none; color: #4b5563; font-weight: 500; font-size: 0.9rem; }
.nav-link:hover { color: #ef4444; }

.hero-section {
  min-height: 100vh; display: flex; align-items: center;
  padding: 6rem 2rem 4rem; gap: 4rem;
}
.hero-content { flex: 1; animation: fadeInUp 0.8s ease-out; }
.hero-badge {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: white; padding: 0.5rem 1rem; border-radius: 50px;
  font-size: 0.8rem; font-weight: 600; color: #ef4444;
  box-shadow: 0 2px 10px rgba(239,68,68,0.1); margin-bottom: 1.5rem;
}
.badge-pulse {
  width: 8px; height: 8px; background: #ef4444; border-radius: 50%;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
  50% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
}
.hero-title { font-size: 3rem; font-weight: 900; line-height: 1.2; margin-bottom: 1.5rem; color: #1f2937; }
.gradient-text {
  background: linear-gradient(135deg, #ef4444, #3b82f6);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-desc { font-size: 1.1rem; color: #6b7280; line-height: 1.7; margin-bottom: 2rem; max-width: 500px; }
.hero-actions { display: flex; gap: 1rem; }
.btn-hero-primary {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.875rem 2rem; background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white; border-radius: 50px; text-decoration: none;
  font-weight: 600; box-shadow: 0 4px 15px rgba(239,68,68,0.3);
  transition: all 0.3s;
}
.btn-hero-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(239,68,68,0.4); }
.btn-hero-secondary {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.875rem 2rem; background: white; color: #3b82f6;
  border-radius: 50px; text-decoration: none; font-weight: 600;
  border: 2px solid #3b82f6; transition: all 0.3s;
}
.btn-hero-secondary:hover { background: #eff6ff; transform: translateY(-2px); }
.hero-visual { flex: 1; display: flex; align-items: center; justify-content: center; }

/* SOLUSI: CSS atur ukuran logo hero */
.hero-logo {
  width: 280px;       /* ← Ukuran besar untuk hero */
  height: 280px;
  border-radius: 40px;
  object-fit: contain;
  background: white;
  padding: 15px;
  box-shadow: 0 25px 50px rgba(239,68,68,0.2);
  animation: float 4s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-15px); }
}

.features-section { padding: 4rem 2rem; }
.section-title { text-align: center; font-size: 2.5rem; font-weight: 800; margin-bottom: 3rem; color: #1f2937; }
.features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto; }
.feature-card {
  background: white; padding: 2rem; border-radius: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: all 0.3s;
  border: 1px solid #f3f4f6;
}
.feature-card:hover { transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
.feature-icon {
  width: 60px; height: 60px; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.75rem; margin-bottom: 1rem;
}
.feature-card h3 { font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem; color: #1f2937; }
.feature-card p { color: #6b7280; line-height: 1.6; font-size: 0.95rem; }

.roles-section { padding: 4rem 2rem; background: linear-gradient(135deg, #fef2f2 0%, #eff6ff 100%); }
.roles-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto; }
.role-card {
  background: white; border-radius: 16px; overflow: hidden;
  box-shadow: 0 4px 15px rgba(0,0,0,0.08); transition: all 0.3s;
}
.role-card:hover { transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.12); }
.role-header { padding: 2rem 1.5rem; text-align: center; color: white; }
.role-icon { font-size: 3rem; display: block; margin-bottom: 0.5rem; }
.role-header h3 { font-size: 1.5rem; font-weight: 700; }
.role-body { padding: 1.5rem; }
.role-body ul { list-style: none; margin-bottom: 1.5rem; }
.role-body li {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.5rem 0; color: #4b5563; font-size: 0.9rem;
}
.step-dot { width: 6px; height: 6px; background: #ef4444; border-radius: 50%; flex-shrink: 0; }
.role-btn {
  display: block; text-align: center; padding: 0.75rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white; border-radius: 10px; text-decoration: none;
  font-weight: 600; transition: all 0.3s;
}
.role-btn:hover { box-shadow: 0 4px 15px rgba(239,68,68,0.3); }

.home-footer { text-align: center; padding: 2rem; background: white; color: #9ca3af; font-size: 0.85rem; }

@media (max-width: 768px) {
  .hero-section { flex-direction: column; padding: 5rem 1.5rem 2rem; }
  .hero-title { font-size: 2rem; }
  .hero-logo { width: 180px; height: 180px; }
  .hero-actions { flex-direction: column; }
}
</style>
