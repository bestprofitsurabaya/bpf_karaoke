<template>
  <aside class="control-panel" aria-label="Panel kontrol pemutaran">
    <section class="ctrl-section">
      <h4 class="ctrl-title">▶️ Playback</h4>
      <button class="pb-btn primary" :disabled="!hasSong" @click="emit('toggle-play')" :aria-label="isPlaying ? 'Pause' : 'Play'">
        {{ isPlaying ? '⏸ Pause' : '▶ Play' }}
      </button>
      <div class="pb-row">      <button class="pb-btn" :disabled="!hasSong" @click="emit('skip')" aria-label="Skip ke lagu berikutnya">⏭ Skip</button>
      </div>
      <div class="keyboard-hints">
        <span class="hint-item"><kbd>Space</kbd> Play/Pause</span>
        <span class="hint-item"><kbd>→</kbd> Skip</span>
        <span class="hint-item"><kbd>/</kbd> Cari</span>
      </div>
    </section>

    <section class="ctrl-section">
      <h4 class="ctrl-title">🎹 Pitch / Nada</h4>
      <div class="key-display">
        <button class="key-btn" :disabled="keyShift <= -12" @click="emit('change-key', -1)" aria-label="Turunkan nada">−</button>
        <div class="key-value" @click="emit('change-key', 0)" title="Klik untuk reset ke 0">
          <span class="key-num">{{ keyShift > 0 ? '+' : '' }}{{ keyShift }}</span>
          <span class="key-semi">semitone</span>
        </div>
        <button class="key-btn" :disabled="keyShift >= 12" @click="emit('change-key', 1)" aria-label="Naikkan nada">+</button>
      </div>
    </section>

    <section class="ctrl-section">
      <h4 class="ctrl-title">🎤 Vocal</h4>
      <div class="vocal-btns" role="group" aria-label="Mode vocal">
        <button v-for="m in modes" :key="m.id" class="vocal-btn" :class="{ active: vocalMode === m.id }" @click="emit('toggle-vocal', m.id)">
          {{ m.label }}
        </button>
      </div>
      <button class="btn-vocal-remove" :disabled="vocalRemoving || !hasSong" @click="emit('vocal-remove')">
        {{ vocalRemoving ? '⏳ Vocal removal...' : '🎵 AI Vocal Remove' }}
      </button>
    </section>

    <section class="ctrl-section">
      <h4 class="ctrl-title">🔊 Volume</h4>
      <div class="volume-row">
        <button class="vol-mute" @click="emit('toggle-mute')" :aria-label="volume > 0 ? 'Mute' : 'Unmute'">{{ volume > 0 ? '🔊' : '🔇' }}</button>
        <input type="range" min="0" max="100" :value="volume" @input="emit('set-volume', Number($event.target.value))" class="vol-slider" aria-label="Volume" />
      </div>
      <div class="vol-value">{{ volume }}%</div>
    </section>
  </aside>
</template>

<script setup>
defineProps({
  isPlaying: Boolean,
  hasSong: Boolean,
  keyShift: { type: Number, default: 0 },
  vocalMode: { type: String, default: 'stereo' },
  volume: { type: Number, default: 80 },
  vocalRemoving: Boolean
})
const emit = defineEmits(['toggle-play', 'skip', 'change-key', 'toggle-vocal', 'vocal-remove', 'set-volume', 'toggle-mute'])

const modes = [
  { id: 'stereo', label: 'Stereo' },
  { id: 'left', label: 'Kiri' },
  { id: 'right', label: 'Kanan' }
]
</script>

<style scoped>
.control-panel {
  width: 230px; min-width: 230px;
  background: var(--surface, #fff);
  border-left: 1px solid var(--border, #e2e8f0);
  padding: 0.5rem;
  display: flex; flex-direction: column; gap: 0.5rem;
  overflow-y: auto;
}
.control-panel::-webkit-scrollbar { width: 8px; }
.control-panel::-webkit-scrollbar-thumb { background: var(--border, #e2e8f0); border-radius: 4px; }
.ctrl-section { background: var(--surface-2, #f8fafc); border: 1px solid var(--border-soft, #f1f5f9); border-radius: 10px; padding: 0.6rem; }
.ctrl-title { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; color: var(--muted, #64748b); margin-bottom: 0.4rem; }
.playback-btns { display: flex; flex-direction: column; gap: 0.3rem; }
.pb-btn {
  flex: 1; padding: 0.5rem;
  border: none; border-radius: 8px;
  font-weight: 600; cursor: pointer; font-size: 0.75rem;
  transition: transform 0.1s, opacity 0.2s;
}
.pb-btn:active { transform: scale(0.97); }
.pb-btn.primary { background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff; width: 100%; }
.pb-btn:not(.primary) { background: var(--surface-3, #f1f5f9); color: var(--text, #475569); }
.pb-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.pb-row { display: flex; gap: 0.3rem; margin-top: 0.3rem; }
.keyboard-hints { margin-top: 0.4rem; display: flex; flex-direction: column; gap: 0.15rem; }
.hint-item { display: flex; align-items: center; gap: 0.35rem; font-size: 0.6rem; color: var(--faint, #cbd5e1); }
kbd {
  background: var(--surface-3, #f1f5f9);
  border: 1px solid var(--border, #e2e8f0);
  border-bottom-width: 2px;
  border-radius: 4px;
  padding: 0.05rem 0.4rem;
  font-family: 'Inter', sans-serif;
  font-size: 0.58rem;
  font-weight: 700;
  color: var(--text, #475569);
}
.key-display { display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
.key-btn {
  width: 44px; height: 44px;
  border: 2px solid var(--border, #e2e8f0);
  border-radius: 10px;
  background: var(--surface, #fff);
  cursor: pointer; font-weight: 700; font-size: 1.1rem;
  color: var(--text, #1e293b);
  transition: all 0.15s;
}
.key-btn:hover:not(:disabled) { border-color: var(--red, #ef4444); }
.key-btn:active:not(:disabled) { transform: scale(0.92); }
.key-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.key-value { text-align: center; cursor: pointer; min-width: 64px; }
.key-num { font-size: 1.3rem; font-weight: 800; color: var(--text, #1e293b); }
.key-semi { display: block; font-size: 0.5rem; color: var(--faint, #cbd5e1); text-transform: uppercase; }
.vocal-btns { display: flex; gap: 0.25rem; }
.vocal-btn {
  flex: 1; padding: 0.45rem 0.2rem;
  background: var(--surface-3, #f1f5f9);
  border: 2px solid transparent; border-radius: 8px;
  cursor: pointer; font-size: 0.65rem; font-weight: 600;
  color: var(--muted, #64748b);
  transition: all 0.15s;
}
.vocal-btn.active { background: var(--surface, #fff); border-color: var(--red, #ef4444); color: var(--red, #ef4444); }
.btn-vocal-remove {
  width: 100%; margin-top: 0.4rem; padding: 0.45rem;
  background: linear-gradient(135deg, #8b5cf6, #6d28d9);
  color: #fff; border: none; border-radius: 8px;
  cursor: pointer; font-size: 0.68rem; font-weight: 600;
  transition: transform 0.1s;
}
.btn-vocal-remove:active { transform: scale(0.98); }
.btn-vocal-remove:disabled { opacity: 0.5; cursor: not-allowed; }
.volume-row { display: flex; align-items: center; gap: 0.4rem; }
.vol-mute {
  min-width: 40px; height: 40px;
  background: var(--surface-3, #f1f5f9);
  border: none; border-radius: 8px;
  cursor: pointer; font-size: 1rem;
  display: flex; align-items: center; justify-content: center;
}
.vol-mute:active { transform: scale(0.92); }
.vol-slider { flex: 1; accent-color: #ef4444; height: 4px; }
.vol-value { text-align: center; font-weight: 700; font-size: 0.75rem; margin-top: 0.15rem; color: var(--text, #1e293b); }
button:focus-visible { outline: 2px solid var(--blue, #3b82f6); outline-offset: 2px; }
</style>
