<template>
  <div class="song-card" :class="{ 'is-in-queue': inQueue, 'is-selected': selected }" @click="emit('toggle-select', song)">
    <div class="card-check">
      <input type="checkbox" :checked="selected" @click.stop="emit('toggle-select', song)" :aria-label="`Pilih ${song.title}`" />
    </div>
    <div class="card-id">#{{ song.id }}</div>
    <div class="card-thumb" :style="{ background: thumbGradient(song.genre) }" aria-hidden="true">
      <span class="thumb-icon">🎵</span>
    </div>
    <div class="card-info">
      <div class="card-title" :title="song.title">{{ song.title }}</div>
      <div class="card-artist">{{ song.artist || 'Unknown' }}</div>
      <div class="card-meta" v-if="showMeta">
        <span v-if="song.genre" class="meta-tag">{{ song.genre }}</span>
        <span class="meta-plays">▶ {{ song.play_count || 0 }}x</span>
      </div>
    </div>
    <button class="card-play-next" :aria-label="`Putar berikutnya: ${song.title}`" title="Putar berikutnya (⏩)" @click.stop="emit('play-next', song)">
      ⏩
    </button>
    <button class="card-star" :class="{ favorited }" :aria-label="favorited ? `Hapus favorit ${song.title}` : `Tambah favorit ${song.title}`" @click.stop="emit('toggle-favorite', song)">
      {{ favorited ? '⭐' : '☆' }}
    </button>
    <button class="card-add" :class="{ added: inQueue }" :disabled="inQueue" :title="inQueue ? 'Sudah di antrian' : 'Tambah ke antrian'" :aria-label="`Tambah ${song.title} ke antrian`" @click.stop="emit('add', song)">
      {{ inQueue ? '✓' : '+' }}
    </button>
  </div>
</template>

<script setup>
import { thumbGradient } from '@/utils/helpers'

defineProps({
  song: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  inQueue: { type: Boolean, default: false },
  favorited: { type: Boolean, default: false },
  showMeta: { type: Boolean, default: true }
})
const emit = defineEmits(['toggle-select', 'toggle-favorite', 'add', 'play-next'])
</script>

<style scoped>
.song-card {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: var(--surface, #fff);
  padding: 0.45rem 0.5rem;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid var(--border-soft, #f1f5f9);
  transition: all 0.15s;
  min-height: 48px;
}
.song-card:hover { border-color: var(--red-border, #fecaca); box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.08)); }
.song-card:active { transform: scale(0.985); }
.song-card.is-selected { border-color: var(--blue, #3b82f6); background: var(--blue-soft, #eff6ff); }
.song-card.is-in-queue .card-title { color: var(--green, #059669); }
.card-check { width: 20px; }
.card-check input { width: 16px; height: 16px; accent-color: var(--blue, #3b82f6); cursor: pointer; }
.card-id { font-size: 0.6rem; color: var(--muted-2, #94a3b8); min-width: 30px; font-weight: 600; }
.card-thumb { width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.thumb-icon { font-size: 0.85rem; color: white; }
.card-info { flex: 1; min-width: 0; }
.card-title { font-weight: 600; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text, #1e293b); }
.card-artist { font-size: 0.68rem; color: var(--muted-2, #94a3b8); }
.card-meta { display: flex; gap: 0.3rem; margin-top: 0.05rem; }
.meta-tag { font-size: 0.55rem; padding: 0.05rem 0.3rem; background: var(--blue-soft, #eff6ff); color: var(--blue, #3b82f6); border-radius: 3px; }
.meta-plays { font-size: 0.55rem; color: var(--faint, #cbd5e1); }
.card-play-next {
  min-width: 40px; height: 40px;
  background: var(--surface-3, #f1f5f9);
  border: none; border-radius: 8px;
  cursor: pointer; font-size: 0.9rem;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.card-play-next:hover { background: var(--blue-soft, #eff6ff); }
.card-play-next:active { transform: scale(0.92); }
.card-star {
  min-width: 40px; height: 40px;
  background: none; border: none;
  font-size: 1rem; cursor: pointer; padding: 0.15rem;
  display: flex; align-items: center; justify-content: center;
}
.card-star.favorited { color: #f59e0b; }
.card-add {
  min-width: 40px; height: 40px;
  border-radius: 50%;
  border: 2px solid var(--red, #ef4444);
  background: var(--surface, #fff);
  color: var(--red, #ef4444);
  font-size: 1rem; font-weight: 700; cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.card-add:hover { background: var(--red, #ef4444); color: #fff; }
.card-add:active { transform: scale(0.9); }
.card-add:disabled { opacity: 0.55; cursor: not-allowed; }
.card-add.added { background: var(--green, #10b981); border-color: var(--green, #10b981); color: #fff; }
button:focus-visible { outline: 2px solid var(--blue, #3b82f6); outline-offset: 2px; }
</style>
