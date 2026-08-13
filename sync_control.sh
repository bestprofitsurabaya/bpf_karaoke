#!/usr/bin/env bash
# ============================================================
# sync_control.sh — KONTROL MANUAL proses pemindahan file
# bank karaoke dari Windows XP (SMB1) ke /srv/karaoke_media
# ============================================================
# Cara pakai:
#   ./sync_control.sh status    # lihat status proses (container + progress)
#   ./sync_control.sh start     # MULAI / lanjutkan proses pemindahan
#   ./sync_control.sh pause     # JEDA proses (aman — lanjut dari titik henti)
#
# Prinsip keamanan proses (lihat backend/services/smb_sync.py):
#   - Setiap file disalin ke ".part" lalu di-rename atomik -> tidak ada
#     file korup walau di-stop di tengah.
#   - Progres disimpan ke /srv/karaoke_media/sync_state.json tiap ±5 detik
#     -> saat di-start lagi, lanjut otomatis (incremental, tidak mengulang).
# ============================================================
set -euo pipefail

cd "$(dirname "$0")"   # jalankan dari mana pun, konteks compose tetap benar

STATE="/srv/karaoke_media/sync_state.json"
SERVICE="karaoke_sync"
CMD="${1:-status}"

case "$CMD" in
  status)
    echo "=============================================="
    echo "  KONTROL SYNC KARAOKE (XP -> server)"
    echo "=============================================="
    # --- Status container ---
    if docker ps --format '{{.Names}}' | grep -qx "$SERVICE"; then
      echo "  Proses   : ✅ BERJALAN"
      docker ps --filter "name=^${SERVICE}$" --format "             container: {{.Names}} (up {{.Status}})"
    elif docker ps -a --format '{{.Names}}' | grep -qx "$SERVICE"; then
      echo "  Proses   : ⏸️  DI-JEDA (container ada, tidak berjalan)"
    else
      echo "  Proses   : ⏸️  DI-JEDA (container belum dibuat)"
    fi

    # --- Progress dari state file ---
    if [ ! -f "$STATE" ]; then
      echo "  Progress : belum ada — sync belum pernah berjalan."
      exit 0
    fi
    python3 - "$STATE" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
done = s.get("done")
badge = " ✅ SEMUA LAGU TERSALIN" if done else " 🔄 MENGIRIM (jeda: file state terakhir)"
print(f"  Progress : {s.get('copied_files')} file tersalin / {s.get('total_files')} ({s.get('percent',0):.1f}%){badge}")
print(f"             {s.get('copied_bytes',0)/1024/1024/1024:.1f} GB | error {s.get('errors')} | pass ke-{s.get('passes')}")
print(f"  Terakhir : {s.get('updated_at')}")
PY
    echo "----------------------------------------------"
    echo "  Lanjut : ./sync_control.sh start"
    echo "  Jeda   : ./sync_control.sh pause"
    echo "=============================================="
    ;;

  start)
    echo "▶️  Memulai sync karaoke (resume incremental dari state)..."
    docker compose up -d "$SERVICE"
    echo "  ✅ Proses berjalan. Pantau: ./sync_control.sh status"
    ;;

  pause)
    if ! docker ps --format '{{.Names}}' | grep -qx "$SERVICE"; then
      echo "  ⏸️  Proses memang sedang tidak berjalan (sudah di-jeda)."
      exit 0
    fi
    echo "⏸️  Menjeda proses pemindahan file (SIGTERM — aman, state tersimpan)..."
    docker compose stop "$SERVICE"
    echo "  ✅ Proses di-jeda. Lanjutkan kapan saja: ./sync_control.sh start"
    ;;

  *)
    echo "Penggunaan: $0 {status|start|pause}"
    exit 1
    ;;
esac
