#!/usr/bin/env bash
# ============================================================
# Shutdown Aman Stack Karaoke + Host
# ============================================================
# Menghentikan semua container karaoke secara GRACEFUL (SIGTERM,
# bukan kill paksa) agar:
#   - ffmpeg/transcode selesai menulis .part (rename atomik aman)
#   - sync_state.json & Redis appendonly ter-flush
#   - Postgres shutdown bersih
# Setelah boot, pipeline LANJUT otomatis (restart: unless-stopped;
# .part basi di-sweep otomatis, sync resume, antrian Redis utuh).
#
# Penggunaan:
#   ./shutdown_karaoke.sh                 # stop stack saja (host tetap nyala)
#   ./shutdown_karaoke.sh --poweroff      # stop stack lalu matikan host
#   ./shutdown_karaoke.sh --wait=300      # tunggu s/d 300 detik utk stop
# ============================================================
set -u

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAIT_SEC=180
POWEROFF=0

while [ $# -gt 0 ]; do
  case "$1" in
    --poweroff) POWEROFF=1; shift ;;
    --wait=*) WAIT_SEC="${1#--wait=}"; shift ;;
    --wait) WAIT_SEC="${2:-180}"; shift 2 ;;
    *) echo "Argumen tidak dikenal: $1 (coba --help)"; exit 1 ;;
  esac
done

echo ">>> [1/4] Menyiapkan environment..."
cd "$BASE_DIR"

echo ">>> [2/4] Menghentikan stack karaoke secara graceful (max ${WAIT_SEC}s)..."
docker compose stop --time "$WAIT_SEC"
echo "    - Stack karaoke dihentikan."

# Flush semua data ke disk
echo ">>> [3/4] Flush cache ke disk..."
sync
sleep 2
echo "    - Disk flushed."

if [ "$POWEROFF" -eq 1 ]; then
  echo ">>> [4/4] Mematikan host dalam 10 detik (Ctrl+C untuk batal)..."
  sleep 10
  sudo shutdown -h now
else
  echo ">>> [4/4] Selesai — host TIDAK dimatikan (pakai --poweroff bila perlu)."
  echo
  echo "🔌 Sekarang aman untuk:"
  echo "   1. Matikan listrik / pasang HDD baru"
  echo "   2. Setelah HDD terpasang: jalankan  ./setup_hdd.sh"
  echo "   3. Nyalakan host → semua container karaoke hidup otomatis"
fi
