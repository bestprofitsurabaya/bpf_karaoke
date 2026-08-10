#!/usr/bin/env bash
# ============================================================
# Cek status sinkronisasi bank karaoke (Windows XP) + transcode
# Penggunaan: ./check_sync.sh   (jalankan kapan saja)
# ============================================================

STATE="/srv/karaoke_media/sync_state.json"

echo "=============================================="
echo "  STATUS SINKRONISASI BANK KARAOKE (SMB1/XP)"
echo "=============================================="

if [ ! -f "$STATE" ]; then
  echo "  ⏸  State file belum ada — sync belum berjalan."
  echo "  Cek container: docker compose logs karaoke_sync --tail 20"
  exit 0
fi

python3 - "$STATE" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
if s.get("done"):
    badge = " ✅ SEMUA LAGU TERSALIN"
else:
    badge = " 🔄 MENGIRIM..."
print(f"  Fase      : {s.get('phase')}{badge}")
print(f"  Tersalin  : {s.get('copied_files')} file  ({s.get('copied_bytes',0)/1024/1024/1024:.1f} GB)")
print(f"  Terlihat  : {s.get('discovered_files')} file  (total bank: {s.get('total_files') or '? (masih dihitung)'})")
print(f"  Skipped   : {s.get('skipped_existing')}  |  Error: {s.get('errors')}")
print(f"  Paralel   : {s.get('parallel', 1)} koneksi SMB")
cur = s.get('current_file') or ''
print(f"  File kini : {cur[:80]}")
print(f"  Disk /srv : {s.get('disk',{}).get('free_gb')} GB bebas  {('⚠️ ' + s['disk']['warning']) if s.get('disk',{}).get('warning') else ''}")
print(f"  Update    : {s.get('updated_at')}")
PY

echo "----------------------------------------------"
echo "  PIPELINE TRANSCODE & DATABASE"
echo "----------------------------------------------"

TRANSCODED=$(find /srv/karaoke_media/transcoded -name '*.mp4' 2>/dev/null | wc -l)
echo "  File MP4 ter-transcode : $TRANSCODED"

if docker ps --format '{{.Names}}' | grep -q karaoke_backend; then
  SONGS=$(docker exec karaoke_backend python3 -c "
import asyncio, sys; sys.path.insert(0, '/app')
from database import async_session
from models import Song
from sqlalchemy import select, func
async def m():
    async with async_session() as s:
        print((await s.execute(select(func.count(Song.id)))).scalar())
asyncio.run(m())" 2>/dev/null | tail -1)
  echo "  Lagu di database       : $SONGS"
  QUEUE=$(docker exec karaoke_redis redis-cli -n 1 LLEN transcoding 2>/dev/null)
  PENDING=$(docker exec karaoke_redis redis-cli -n 0 SCARD transcode:pending 2>/dev/null)
  echo "  Antrian transcode      : ${QUEUE:-?} task  (proses aktif: ${PENDING:-?})"
else
  echo "  (container backend tidak berjalan)"
fi

echo "=============================================="
