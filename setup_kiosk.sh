#!/usr/bin/env bash
# ============================================================
# setup_kiosk.sh — Ubah PC JADUL menjadi KIOSK KARAOKE (thin client)
# ============================================================
# Tujuan: komputer tua (RAM 2GB DDR2, dst.) dipakai sebagai
# mesin karaoke di ruangan — boot langsung ke aplikasi tanpa
# login manual. Dua mode:
#
#   [default / --player-only]
#     Satu layar: PLAYER (TV). Cocok utk PC terpisah khusus TV.
#
#   --dual
#     DUA layar pada SATU PC (setup standar ruangan):
#       Layar 1 -> OPERATOR  (/operator?room=...)
#       Layar 2 -> PLAYER/TV (/player?room=...)
#     Posisi monitor otomatis via xrandr; bisa ditimpa dengan
#     --operator-monitor= dan --player-monitor= (nama output,
#     mis. VGA-1 / HDMI-1).
#
# Yang DIINSTALL / DIUBAH:
#   - Sistem grafis minimal (Xorg + Openbox — TANPA desktop penuh)
#   - Browser kiosk: Chromium (64-bit) / Firefox ESR (32-bit)
#   - Autologin user 'kiosk' + autostart sejak boot
#   - zram (swap terkompresi di RAM — sangat membantu RAM 2GB)
#   - Timezone Asia/Jakarta + sinkronisasi jam (countdown sesi)
#   - PulseAudio (player pakai Web Audio utk routing vokal)
#
# TIDAK menyentuh server karaoke — semua kerja berat tetap di server.
# TIDAK menyentuh disk/partisi apa pun — skrip hanya install paket
# & tulis konfigurasi. HDD bank karaoke (2 HDD di mesin XP) aman
# dan TIDAK disentuh skrip ini.
#
# ⚠️  URUTAN PENTING (bila PC ini juga sumber bank XP):
#     1. Tuntaskan dulu sync bank ke server (bank 1 & 2) —
#        data bank hanya ada di PC ini. Jangan konversi OS
#        sebelum sync tuntas & terverifikasi.
#     2. Baru install Linux ringan (mis. Debian minimal) di
#        HDD SISTEM — biarkan 2 HDD bank apa adanya.
#     3. Jalankan skrip ini, lalu reboot.
#
# Penggunaan (di PC kiosk, sebagai root):
#   sudo ./setup_kiosk.sh                       # default: player saja, Room 1
#   sudo ./setup_kiosk.sh --dual                # operator + player (2 monitor)
#   sudo ./setup_kiosk.sh --dual --room="Room 2"
#   sudo ./setup_kiosk.sh --dual --operator-monitor=VGA-1 --player-monitor=HDMI-1
#   sudo ./setup_kiosk.sh --url="https://..."   # URL server custom
#
# IDEMPOTEN: aman dijalankan ulang — paket yang ada dilewati,
# konfigurasi ditimpa dengan nilai yang sama.
# ============================================================
set -u

KIOSK_USER="kiosk"
ROOM="Room 1"
BASE_URL="https://nasbpfsby.duckdns.org:8443"
DUAL=0
OP_MONITOR=""
PL_MONITOR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --room=*) ROOM="${1#--room=}"; shift ;;
    --room) ROOM="${2:-Room 1}"; shift 2 ;;
    --url=*) BASE_URL="${1#--url=}"; shift ;;
    --url) BASE_URL="${2:-}"; shift 2 ;;
    --user=*) KIOSK_USER="${1#--user=}"; shift ;;
    --dual) DUAL=1; shift ;;
    --player-only) DUAL=0; shift ;;
    --operator-monitor=*) OP_MONITOR="${1#--operator-monitor=}"; shift ;;
    --player-monitor=*) PL_MONITOR="${1#--player-monitor=}"; shift ;;
    --help|-h) sed -n '1,55p' "$0" | grep '^#'; exit 0 ;;
    *) echo "Argumen tidak dikenal: $1 (coba --help)"; exit 1 ;;
  esac
done

# --- URL final ---
# Room dengan spasi di-encode agar aman di URL (mis. "Room 1" -> "Room%201")
ROOM_ENC=$(echo "$ROOM" | sed 's/ /%20/g')
PLAYER_URL="${BASE_URL%/}/player?room=${ROOM_ENC}"
OPERATOR_URL="${BASE_URL%/}/operator?room=${ROOM_ENC}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say() { echo -e "$1"; }

say "${YELLOW}==================================================${NC}"
if [ "$DUAL" -eq 1 ]; then
  say "${YELLOW}  SETUP KIOSK KARAOKE — DUAL SCREEN (operator + player)${NC}"
else
  say "${YELLOW}  SETUP KIOSK KARAOKE — PLAYER SAJA (thin client)${NC}"
fi
say "${YELLOW}==================================================${NC}"
say "  Room        : $ROOM"
if [ "$DUAL" -eq 1 ]; then
  say "  Operator    : $OPERATOR_URL"
  say "  Player      : $PLAYER_URL"
else
  say "  URL player  : $PLAYER_URL"
fi

# ---------- Prasyarat ----------
[ "$(id -u)" -eq 0 ] || { say "${RED}❌ Jalankan sebagai root (sudo).${NC}"; exit 1; }

# ---------- 1. Deteksi arsitektur CPU ----------
ARCH=$(uname -m)
case "$ARCH" in
  x86_64|amd64)
    say "  CPU         : 64-bit (x86_64) — pakai Chromium kiosk ✅"
    BROWSER_PKG="chromium"
    ;;
  i386|i486|i586|i686)
    say "  CPU         : 32-bit (i686) — pakai Firefox ESR (Chromium tak ada utk 32-bit) ⚠️"
    say "              ⚠️ Firefox 32-bit berakhir di v144/140-ESR — anggap mesin ini EOL."
    say "              ⚠️ Mode --dual membutuhkan penempatan window via xdotool (best-effort)."
    BROWSER_PKG="firefox-esr"
    ;;
  *)
    say "${RED}❌ Arsitektur tak dikenal: $ARCH${NC}"
    exit 1
    ;;
esac

# ---------- 2. Deteksi package manager ----------
if command -v apt-get >/dev/null 2>&1; then
  PM="apt"
elif command -v dnf >/dev/null 2>&1; then
  PM="dnf"
elif command -v pacman >/dev/null 2>&1; then
  PM="pacman"
else
  say "${RED}❌ Skrip ini mendukung Debian/Ubuntu (apt), Fedora (dnf), Arch (pacman).${NC}"
  exit 1
fi

install_pkgs() {
  case "$PM" in
    apt)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get install -y --no-install-recommends \
        xserver-xorg-core xserver-xorg-input-evdev xserver-xorg-video-fbdev \
        xinit lightdm openbox \
        x11-xserver-utils xdotool \
        "$BROWSER_PKG" \
        zram-tools pulseaudio network-manager \
        unclutter-xfixes \
        || true
      # Paket video driver beragam antar hardware — pasang meta xorg bila ada
      # (gagal tidak apa-apa: driver generik fbdev sudah cukup utk layar kiosk)
      apt-get install -y --no-install-recommends xserver-xorg 2>/dev/null || true
      ;;
    dnf)
      dnf install -y xorg-x11-server-Xorg lightdm openbox chromium \
        xrandr xdotool \
        zram-generator pulseaudio NetworkManager unclutter-xfixes || true
      ;;
    pacman)
      pacman -Sy --noconfirm --needed xorg-server xorg-xinit lightdm openbox \
        chromium xorg-xrandr xdotool \
        zram-generator pulseaudio networkmanager unclutter || true
      ;;
  esac
}

say ""
say ">>> Memasang paket minimal (browser + grafis ringan + zram)..."
say "    Package manager: $PM | browser: $BROWSER_PKG"
install_pkgs

# Pastikan browser benar-benar terpasang
if command -v chromium >/dev/null 2>&1; then
  BROWSER_BIN="chromium"
elif command -v chromium-browser >/dev/null 2>&1; then
  BROWSER_BIN="chromium-browser"
elif command -v firefox >/dev/null 2>&1; then
  BROWSER_BIN="firefox"
elif command -v firefox-esr >/dev/null 2>&1; then
  BROWSER_BIN="firefox"
else
  say "${RED}❌ Browser tidak terpasang. Periksa jaringan apt (apt-get update).${NC}"
  exit 1
fi

# ---------- 3. Buat user kiosk (autologin) ----------
say ""
say ">>> Menyiapkan user '$KIOSK_USER' (autologin, tanpa password)..."
if ! id "$KIOSK_USER" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$KIOSK_USER"
  say "    User $KIOSK_USER dibuat."
else
  say "    User $KIOSK_USER sudah ada."
fi
usermod -aG audio,video,input "$KIOSK_USER" 2>/dev/null || true

# ---------- 4. LightDM: autologin langsung ke Openbox ----------
say ">>> Mengonfigurasi LightDM (autologin -> openbox)..."
mkdir -p /etc/lightdm
cat > /etc/lightdm/lightdm.conf <<EOF
[Seat:*]
autologin-user=$KIOSK_USER
autologin-session=openbox
user-session=openbox
greeter-session=lightdm-gtk-greeter
EOF
say "    /etc/lightdm/lightdm.conf ditulis."

# ---------- 5. Autostart sejak boot ----------
say ">>> Menyiapkan autostart kiosk (loop anti-crash)..."
mkdir -p "/home/$KIOSK_USER/.config/openbox"

if [ "$DUAL" -eq 1 ]; then
cat > "/home/$KIOSK_USER/.config/openbox/autostart" <<EOF
# Autostart Kiosk Karaoke DUAL SCREEN (dibuat setup_kiosk.sh --dual)
# Layar 1 = OPERATOR, Layar 2 = PLAYER. Urutan monitor otomatis via
# xrandr (output pertama = operator, kedua = player). Bisa ditimpa:
#   OPERATOR_MONITOR="VGA-1"  PLAYER_MONITOR="HDMI-1"
# sebelum baris while di bawah, atau set saat setup dengan
# --operator-monitor / --player-monitor.
xset s off -dpms &          # matikan blank layar & power-save monitor
pulseaudio --start --exit-idle-time=-1 &   # audio wajib untuk Web Audio API
unclutter -idle 3 &         # sembunyikan kursor mouse setelah 3 detik idle

# --- Deteksi monitor (nama output + geometri) ---
mon_list=()
# Ambil nama output yang barisnya mengandung ' connected' DAN memiliki kolom
# resolusi (WxH+X+Y) — kata 'primary' bisa muncul di kolom 3, jadi cek semua kolom.
while read -r line; do mon_list+=("\$line"); done < <(xrandr --query 2>/dev/null | awk '/ connected/ { for (i=1;i<=NF;i++) if (\$i ~ /^[0-9]+x[0-9]+\+[0-9]+\+[0-9]+$/) { print \$1; break } }')
[ "\${#mon_list[@]}" -eq 0 ] && mon_list=("default")

op_mon="\${OPERATOR_MONITOR:-\${mon_list[0]}}"
if [ -n "\${PLAYER_MONITOR:-}" ]; then pl_mon="\$PLAYER_MONITOR"; else pl_mon="\${mon_list[1]:-\${mon_list[0]}}"; fi

geom_of() { # $1 = monitor -> "X,Y WxH"
  local g; g=\$(xrandr --query 2>/dev/null | awk -v m="\$1" '\$0 ~ m && / connected/ { for (i=1;i<=NF;i++) if (\$i ~ /^[0-9]+x[0-9]+\+[0-9]+\+[0-9]+\$/) print \$i }')
  [ -z "\$g" ] && { echo "0,0 1024x768"; return; }
  local size=\${g%%+*}; local xy=\${g#*+}; echo "\${xy/+/,} \$size"
}
op_geom=\$(geom_of "\$op_mon"); pl_geom=\$(geom_of "\$pl_mon")
op_pos=\${op_geom%% *}; op_size=\${op_geom#* }
pl_pos=\${pl_geom%% *}; pl_size=\${pl_geom#* }

# --- OPERATOR (layar 1) ---
while true; do
  $BROWSER_BIN --app="$OPERATOR_URL" \\
    --window-position="\$op_pos" --window-size="\$op_size" \\
    --noerrdialogs --disable-infobars --disable-translate \\
    --disable-features=TranslateUI \\
    --autoplay-policy=no-user-gesture-required \\
    --disable-session-crashed-bubble &
  wait \$!
  sleep 3
done &

# --- PLAYER / TV (layar 2) ---
while true; do
  $BROWSER_BIN --app="$PLAYER_URL" \\
    --window-position="\$pl_pos" --window-size="\$pl_size" \\
    --noerrdialogs --disable-infobars --disable-translate \\
    --disable-features=TranslateUI \\
    --autoplay-policy=no-user-gesture-required \\
    --disable-session-crashed-bubble &
  wait \$!
  sleep 3
done &
EOF
else
cat > "/home/$KIOSK_USER/.config/openbox/autostart" <<EOF
# Autostart Player Karaoke (dibuat setup_kiosk.sh)
# Jalan loop: browser crash/tertutup -> buka lagi dalam 3 detik.
xset s off -dpms &          # matikan blank layar & power-save monitor
pulseaudio --start --exit-idle-time=-1 &   # audio wajib untuk Web Audio API
unclutter -idle 3 &         # sembunyikan kursor mouse setelah 3 detik idle

while true; do
  $BROWSER_BIN --kiosk \\
    --noerrdialogs --disable-infobars --disable-translate \\
    --disable-features=TranslateUI \\
    --autoplay-policy=no-user-gesture-required \\
    --disable-session-crashed-bubble \\
    --start-fullscreen \\
    "$PLAYER_URL"
  sleep 3
done &
EOF
fi
chown -R "$KIOSK_USER:$KIOSK_USER" "/home/$KIOSK_USER/.config"

# ---------- 6. zram: swap terkompresi di RAM (sangat membantu 2GB) ----------
say ">>> Mengaktifkan zram (swap terkompresi ±1GB di RAM)..."
case "$PM" in
  apt)
    if [ -f /etc/default/zramswap ]; then
      grep -q '^ALGO=' /etc/default/zramswap || echo 'ALGO=lz4' >> /etc/default/zramswap
      grep -q '^SIZE=' /etc/default/zramswap || echo 'SIZE=1024' >> /etc/default/zramswap
      grep -q '^PRIORITY=' /etc/default/zramswap || echo 'PRIORITY=100' >> /etc/default/zramswap
      systemctl enable zramswap >/dev/null 2>&1 || true
      systemctl restart zramswap >/dev/null 2>&1 || true
      say "    zramswap aktif (lz4, 1GB)."
    else
      say "    (paket zram-tools tak terpasang — lanjut tanpa zram)"
    fi
    ;;
  dnf)
    # zram-generator: cukup buat file konfigurasi
    mkdir -p /etc/systemd/zram-generator.conf.d
    echo '[zram0]' > /etc/systemd/zram-generator.conf.d/karaoke.conf
    echo 'zram-size = ram / 2' >> /etc/systemd/zram-generator.conf.d/karaoke.conf
    echo 'compression-algorithm = lz4' >> /etc/systemd/zram-generator.conf.d/karaoke.conf
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl start systemd-zram-setup@zram0.service >/dev/null 2>&1 || true
    say "    zram-generator dikonfigurasi (ram/2)."
    ;;
  pacman)
    echo '[zram0]' > /etc/systemd/zram-generator.conf
    echo 'zram-size = ram / 2' >> /etc/systemd/zram-generator.conf
    echo 'compression-algorithm = lz4' >> /etc/systemd/zram-generator.conf
    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl start systemd-zram-setup@zram0.service >/dev/null 2>&1 || true
    say "    zram-generator dikonfigurasi (ram/2)."
    ;;
esac

# ---------- 7. Timezone & jam (countdown sesi butuh waktu benar) ----------
say ">>> Mengatur timezone Asia/Jakarta + sinkronisasi jam..."
timedatectl set-timezone Asia/Jakarta 2>/dev/null || \
  ln -sf /usr/share/zoneinfo/Asia/Jakarta /etc/localtime
timedatectl set-ntp true 2>/dev/null || systemctl enable --now systemd-timesyncd 2>/dev/null || true

# ---------- 8. Aktifkan display manager (boot langsung ke layar) ----------
say ">>> Mengaktifkan LightDM sebagai display manager..."
case "$PM" in
  apt) systemctl enable lightdm >/dev/null 2>&1 || true ;;
  dnf) systemctl enable lightdm >/dev/null 2>&1 || true ;;
  pacman) systemctl enable lightdm >/dev/null 2>&1 || true ;;
esac

# ---------- 9. Verifikasi & ringkasan ----------
say ""
say "${GREEN}==================================================${NC}"
say "${GREEN}  SETUP SELESAI ✅${NC}"
say "${GREEN}==================================================${NC}"
say "  CPU/Arsitektur : $ARCH ($BROWSER_BIN)"
say "  User autologin  : $KIOSK_USER -> openbox"
say "  Browser kiosk   : $BROWSER_BIN"
if [ "$DUAL" -eq 1 ]; then
  say "  Mode            : DUAL SCREEN"
  say "  Operator        : $OPERATOR_URL"
  say "  Player          : $PLAYER_URL"
  [ -n "$OP_MONITOR" ] && say "  Monitor operator: $OP_MONITOR (di-set manual)"
  [ -n "$PL_MONITOR" ] && say "  Monitor player  : $PL_MONITOR (di-set manual)"
else
  say "  URL player      : $PLAYER_URL"
fi
say "  Room            : $ROOM"
say ""
RAM_GB=$(awk '/MemTotal/{printf "%.1f", $2/1024/1024}' /proc/meminfo)
say "  RAM            : ${RAM_GB} GB"
swapon --show 2>/dev/null | sed 's/^/    swap          : /' || true
say ""
say "  ▶ LANJUTKAN: reboot PC ini."
if [ "$DUAL" -eq 1 ]; then
  say "    Setelah boot: layar 1 = OPERATOR, layar 2 = PLAYER."
  say "    Jika posisi terbalik, jalankan ulang setup dengan"
  say "    --operator-monitor=... --player-monitor=... (nama output lihat: xrandr)."
else
  say "    Setelah boot, langsung muncul layar player karaoke."
fi
say "    Ketuk layar player SEKALI saat ada prompt suara (kebijakan browser)."
say ""
say "  Jika video patah-patah (CPU jadul, decode software H.264):"
say "    - turunkan resolusi transcode ke 720p di server, atau"
say "    - tambahkan flag --enable-features=VaapiVideoDecodeLinuxGL"
say "      pada baris browser di autostart."
say ""
say "  Uji cepat tanpa reboot:  su - $KIOSK_USER -c 'startx'  (di TTY)"
say "${GREEN}==================================================${NC}"
