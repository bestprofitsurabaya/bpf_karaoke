#!/usr/bin/env bash
# ============================================================
# setup_kiosk.sh — Ubah PC JADUL menjadi PLAYER KARAOKE (thin client)
# ============================================================
# Tujuan: komputer tua (RAM 2GB DDR2, dst.) cukup dipakai sebagai
# LAYAR TV karaoke. Skrip ini mengubahnya jadi "kiosk" — boot
# langsung ke Player Screen fullscreen, tanpa login manual.
#
# Yang DIINSTALL / DIUBAH:
#   - Sistem grafis minimal (Xorg + Openbox — TANPA desktop penuh)
#   - Browser kiosk: Chromium (64-bit) / Firefox ESR (32-bit)
#   - Autologin user 'kiosk' + autostart player sejak boot
#   - zram (swap terkompresi di RAM — sangat membantu RAM 2GB)
#   - Timezone Asia/Jakarta + sinkronisasi jam (countdown sesi)
#   - PulseAudio (player pakai Web Audio utk routing vokal)
#
# TIDAK menyentuh server karaoke — semua kerja berat tetap di server.
#
# Penggunaan (di PC jadul, jalankan sebagai root):
#   sudo ./setup_kiosk.sh                       # default: Room 1
#   sudo ./setup_kiosk.sh --room="Room 2"       # pilih room lain
#   sudo ./setup_kiosk.sh --url="https://..."   # URL server custom
#
# IDEMPOTEN: aman dijalankan ulang — paket yang ada dilewati,
# konfigurasi ditimpa dengan nilai yang sama.
# ============================================================
set -u

KIOSK_USER="kiosk"
ROOM="Room 1"
URL="https://nasbpfsby.duckdns.org:8443/player?room="

while [ $# -gt 0 ]; do
  case "$1" in
    --room=*) ROOM="${1#--room=}"; shift ;;
    --room) ROOM="${2:-Room 1}"; shift 2 ;;
    --url=*) URL="${1#--url=}"; shift ;;
    --url) URL="${2:-}"; shift 2 ;;
    --user=*) KIOSK_USER="${1#--user=}"; shift ;;
    --help|-h) sed -n '1,45p' "$0" | grep '^#'; exit 0 ;;
    *) echo "Argumen tidak dikenal: $1 (coba --help)"; exit 1 ;;
  esac
done

# --- Tampilkan URL final yang akan dibuka player ---
# Room dengan spasi di-encode agar aman di URL (mis. "Room 1" -> "Room%201")
ROOM_ENC=$(echo "$ROOM" | sed 's/ /%20/g')
case "$URL" in
  */player?room=*|*/player\?room=*) PLAYER_URL="$URL" ;;
  *) PLAYER_URL="${URL}${ROOM_ENC}" ;;
esac

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say() { echo -e "$1"; }

say "${YELLOW}==================================================${NC}"
say "${YELLOW}  SETUP PLAYER KIOSK KARAOKE (thin client)${NC}"
say "${YELLOW}==================================================${NC}"
say "  Room target : $ROOM"
say "  URL player  : $PLAYER_URL"

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
        zram-generator pulseaudio NetworkManager unclutter-xfixes || true
      ;;
    pacman)
      pacman -Sy --noconfirm --needed xorg-server xorg-xinit lightdm openbox \
        chromium zram-generator pulseaudio networkmanager unclutter || true
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

# ---------- 5. Autostart: buka player fullscreen sejak boot ----------
say ">>> Menyiapkan autostart player (loop anti-crash)..."
mkdir -p "/home/$KIOSK_USER/.config/openbox"
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
say "  URL player      : $PLAYER_URL"
say "  Room            : $ROOM"
say ""
RAM_GB=$(awk '/MemTotal/{printf "%.1f", $2/1024/1024}' /proc/meminfo)
say "  RAM            : ${RAM_GB} GB"
swapon --show 2>/dev/null | sed 's/^/    swap          : /' || true
say ""
say "  ▶ LANJUTKAN: reboot PC ini."
say "    Setelah boot, langsung muncul layar player karaoke."
say "    Ketuk layar SEKALI saat ada prompt suara (kebijakan browser)."
say ""
say "  Jika video patah-patah (CPU jadul, decode software H.264):"
say "    - turunkan resolusi transcode ke 720p di server, atau"
say "    - tambahkan flag --enable-features=VaapiVideoDecodeLinuxGL"
say "      pada baris browser di autostart."
say ""
say "  Uji cepat tanpa reboot:  su - $KIOSK_USER -c 'startx'  (di TTY)"
say "${GREEN}==================================================${NC}"
