#!/usr/bin/env bash
# ============================================================
# Pipeline Monitor - Sync (XP) -> Transcode -> Database
# ============================================================
# Penggunaan:
#   ./pipeline_monitor.sh            # tampil sekali
#   ./pipeline_monitor.sh --watch    # refresh tiap 5 detik (Ctrl+C berhenti)
#   ./pipeline_monitor.sh --watch 10 # refresh tiap 10 detik
# ============================================================
set -u

STATE="/srv/karaoke_media/sync_state.json"
LAGU="/srv/karaoke_media/lagu"
TRANS="/srv/karaoke_media/transcoded"
MASTER_EXTS="mpg mpeg avi mkv wmv flv vob m2v mpv 3gp dat"

WATCH=""
INTERVAL=5
if [ "${1:-}" = "--watch" ]; then
  WATCH=1
  INTERVAL="${2:-5}"
fi

render() {
  local now
  now=$(date '+%H:%M:%S')

  # ---- Sync ----
  if [ -f "$STATE" ]; then
    python3 - "$STATE" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
badge = " DONE" if s.get("done") else " SYNC"
fase = s.get("phase", "?")
done_f = int(s.get("copied_files") or 0)
total = s.get("total_files")
err = int(s.get("errors") or 0)
hang = s.get("hang_dirs") or []
h = ("  hang: " + ", ".join(hang[:3])) if hang else ""
print(f"  Sync      : {fase}{badge}  | tersalin {done_f} file | total {total or '?'} | error {err}{h}")
print(f"  File kini  : {(s.get('current_file') or '')[:70]}")
PY
  else
    echo "  Sync      : belum ada state file"
  fi

  # ---- Transcode & Sumber ----
  local sources mp4 part stale deleted est
  sources=$(for e in $MASTER_EXTS; do find "$LAGU" -iname "*.$e" 2>/dev/null; done | wc -l)
  mp4=$(find "$TRANS" -iname '*.mp4' 2>/dev/null | wc -l)
  part=$(find "$TRANS" -iname '*.part' -mmin -60 2>/dev/null | wc -l)
  stale=$(find "$TRANS" -iname '*.part' -mmin +60 2>/dev/null | wc -l)

  local queue pending
  queue=$(docker exec karaoke_redis redis-cli -n 1 LLEN transcoding 2>/dev/null || echo "?")
  pending=$(docker exec karaoke_redis redis-cli -n 0 SCARD transcode:pending 2>/dev/null || echo "?")

  echo "  Transcode : MP4 siap $mp4 | sumber master tersisa $sources | antrian $queue task | proses aktif $pending | .part aktif $part (basi $stale)"

  # ---- Aktivitas transcode (berbasis filesystem, andal tanpa log docker) ----
  local baru stale2
  baru=$(find "$TRANS" -iname '*.mp4' -mmin -10 2>/dev/null | wc -l)
  stale2=$(find "$TRANS" -iname '*.part' -mmin +60 2>/dev/null | wc -l)
  echo "  Aktivitas : $baru MP4 baru (10 mnt terakhir) | $stale2 .part basi (harus 0)"

  # ---- Disk ----
  local disk
  disk=$(df -h /srv 2>/dev/null | awk 'NR==2 {print "  Disk /srv : "$3" terpakai / "$2" (bebas "$4")"}')
  echo "$disk"

  # ---- YouTube ----
  local ytkey
  ytkey=$(docker exec karaoke_backend printenv YOUTUBE_API_KEY 2>/dev/null | wc -c)
  if [ "${ytkey:-0}" -gt 10 ]; then
    echo "  YouTube   : API key aktif ✅"
  else
    echo "  YouTube   : API key BELUM diset (fitur YouTube nonaktif)"
  fi
  echo "  Update    : $now"
}

if [ -n "$WATCH" ]; then
  while true; do
    clear
    echo "══════════════════════════════════════════════════════════"
    echo "  PIPELINE MONITOR — BPF KARAOKE  (refresh tiap ${INTERVAL}s, Ctrl+C berhenti)"
    echo "══════════════════════════════════════════════════════════"
    render
    echo "══════════════════════════════════════════════════════════"
    sleep "$INTERVAL"
  done
else
  echo "══════════════════════════════════════════════════════════"
  echo "  PIPELINE MONITOR — BPF KARAOKE"
  echo "══════════════════════════════════════════════════════════"
  render
  echo "══════════════════════════════════════════════════════════"
  echo "  Gunakan: ./pipeline_monitor.sh --watch  untuk mode pantau real-time"
fi
