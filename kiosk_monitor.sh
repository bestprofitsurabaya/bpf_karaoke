#!/bin/bash
# ============================================================
# kiosk_monitor.sh — Monitoring jarak jauh layar kiosk karaoke
# ============================================================
# Ambil screenshot X dari kiosk (operator + player), lalu upload ke
# folder share Nextcloud publik (link diberikan user) via WebDAV.
#
# Dipasang sebagai cron di server (contoh, tiap 15 menit):
#   */15 * * * * /path/to/kiosk_monitor.sh >> /var/log/kiosk_monitor.log 2>&1
#
# Prasyarat:
#   - SSH key server -> kiosk sudah terpasang (tanpa password)
#   - ImageMagick (convert) di server untuk crop + timestamp
#   - curl untuk upload WebDAV ke Nextcloud (akses via localhost:443
#     karena hairpin NAT router memblokir akses ke IP publik dari dalam)
# ============================================================
set -u

KIOSK_IP="${KIOSK_MONITOR_IP:-192.168.100.140}"
SSH_KEY="${KIOSK_MONITOR_KEY:-$HOME/.ssh/kiosk_monitor}"
NC_BASE="${KIOSK_MONITOR_NC:-https://localhost}"
# Token WebDAV Nextcloud — JANGAN hardcode di repo. Baca dari env atau file
# (dibuat sekali: echo '<token>' > ~/.kiosk_monitor_token && chmod 600).
NC_TOKEN="${KIOSK_MONITOR_TOKEN:-$(cat "$HOME/.kiosk_monitor_token" 2>/dev/null)}"
[ -z "$NC_TOKEN" ] && { echo "  ❌ KIOSK_MONITOR_TOKEN / ~/.kiosk_monitor_token kosong — isi dulu."; exit 1; }
NC_WEBDAV="$NC_BASE/public.php/webdav"
TMPDIR="${KIOSK_MONITOR_TMP:-/tmp}"

TS=$(date '+%Y-%m-%d %H:%M WIB')
RAW="$TMPDIR/kiosk_mon_raw.png"
FULL="$TMPDIR/kiosk_mon_full.png"

echo "[$(date '+%F %T')] mulai monitoring kiosk $KIOSK_IP"

# 1. Screenshot X (root window) dari kiosk
if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -i "$SSH_KEY" \
      "kiosk@$KIOSK_IP" \
      "DISPLAY=:0 XAUTHORITY=/home/kiosk/.Xauthority import -window root $RAW 2>/dev/null"; then
  echo "  ❌ SSH/screenshot gagal — kiosk tidak terjangkau?"
  exit 1
fi
if ! scp -o StrictHostKeyChecking=no -o ConnectTimeout=8 -i "$SSH_KEY" \
      "kiosk@$KIOSK_IP:$RAW" "$RAW" 2>/dev/null; then
  echo "  ❌ scp gagal"
  exit 1
fi

# 2. Belah layar: kiri = LG TV (operator), kanan = HDMI (player)
GEOM=$(identify -format "%wx%h" "$RAW" 2>/dev/null)
case "$GEOM" in
  2048x768)  OP_CROP="1024x768+0+0"; PL_CROP="1024x768+1024+0" ;;
  1024x768)  OP_CROP="1024x768+0+0"; PL_CROP="1024x768+0+0" ;;  # fallback single
  *)         echo "  ⚠️ geometri tak dikenal ($GEOM) — upload mentah"
             OP_CROP=""; PL_CROP="" ;;
esac
convert "$RAW" -fill white -undercolor "#00000090" -pointsize 20 \
  -gravity SouthEast -annotate +6+6 "Kiosk $KIOSK_IP - $TS" "$FULL"

upload() { # $1=file $2=nama-remote
  curl -sk --max-time 30 -u "$NC_TOKEN:" -T "$1" "$NC_WEBDAV/$2" \
    -o /dev/null -w "  ✅ $2 -> HTTP %{http_code}\n"
}

if [ -n "$OP_CROP" ]; then
  convert "$FULL" -crop "$OP_CROP" "$TMPDIR/kiosk_mon_op.png"
  convert "$FULL" -crop "$PL_CROP" "$TMPDIR/kiosk_mon_pl.png"
  upload "$TMPDIR/kiosk_mon_op.png" "kiosk_monitor_operator.png"
  upload "$TMPDIR/kiosk_mon_pl.png" "kiosk_monitor_player.png"
else
  upload "$FULL" "kiosk_monitor_full.png"
fi

# 3. Status singkat (xrandr + window chromium)
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -i "$SSH_KEY" \
  "kiosk@$KIOSK_IP" '
  echo "=== $TS ==="
  grep -o "video=[^ ]*" /proc/cmdline
  DISPLAY=:0 xrandr | grep -E "connected|current"
  pgrep -a -f "chromium --show-component" | grep -oE -- "--app=[^ ]+ .*--window-position=[0-9,]+" | sed "s|https://nasbpfsby.duckdns.org:8443/||"
  tail -3 /tmp/kiosk-autostart.log
' > "$TMPDIR/kiosk_mon_status.txt" 2>/dev/null
upload "$TMPDIR/kiosk_mon_status.txt" "kiosk_monitor_status.txt"

# Bersihkan file sementara (kecuali yang terakhir untuk debugging)
rm -f "$RAW" "$FULL" "$TMPDIR/kiosk_mon_op.png" "$TMPDIR/kiosk_mon_pl.png"
echo "  ✔ selesai"
