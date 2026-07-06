<template>
  <div class="home-screen">
    <div class="welcome-container">
      <h1 class="title">🎤 BPF Karaoke System</h1>
      <p class="subtitle">Sistem Karaoke Modern</p>
      <div class="menu-grid">
        <router-link to="/operator?screen=1" class="menu-card">
          <span class="icon">🖥️</span>
          <span class="label">Operator Screen</span>
          <span class="desc">Touchscreen untuk pilih lagu</span>
        </router-link>
        <router-link to="/player?screen=2" class="menu-card">
          <span class="icon">📺</span>
          <span class="label">Player Screen</span>
          <span class="desc">Tampilan TV Karaoke</span>
        </router-link>
        <router-link to="/remote" class="menu-card">
          <span class="icon">📱</span>
          <span class="label">Remote Control</span>
          <span class="desc">Kontrol dari HP</span>
        </router-link>
        <router-link to="/admin" class="menu-card">
          <span class="icon">⚙️</span>
          <span class="label">Admin Panel</span>
          <span class="desc">Manajemen sistem</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  padding: 2rem;
}

.welcome-container {
  text-align: center;
  max-width: 800px;
}

.title {
  font-size: 3rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 1.2rem;
  opacity: 0.7;
  margin-bottom: 3rem;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.5rem;
}

.menu-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 1rem;
  padding: 2rem 1.5rem;
  text-decoration: none;
  color: inherit;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.menu-card:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-4px);
}

.icon {
  font-size: 2.5rem;
}

.label {
  font-size: 1.1rem;
  font-weight: 600;
}

.desc {
  font-size: 0.8rem;
  opacity: 0.6;
}
</style>
