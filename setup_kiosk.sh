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
#   - Resolusi aman 1024x768@60 (Xorg + kernel KMS) supaya TV jadul tidak "no signal"
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
ROOM="BPFSurabaya"
BASE_URL="https://nasbpfsby.duckdns.org:8443"
DUAL=0
OP_MONITOR=""
PL_MONITOR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --room=*) ROOM="${1#--room=}"; shift ;;
    --room) ROOM="${2:-BPFSurabaya}"; shift 2 ;;
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
PLAYER_URL="${BASE_URL%/}/player?room=${ROOM_ENC}&kiosk=1"
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
# Autostart POSIX (openbox menjalankan file ini dengan sh/dash — TIDAK support
# array/process substitution bash). Logika utama ditulis terpisah di
# kiosk-main.sh (bash) yang dipanggil dari sini.
cat > "/home/$KIOSK_USER/.config/openbox/autostart" <<EOF
#!/bin/sh
# Autostart Kiosk Karaoke DUAL SCREEN (dibuat setup_kiosk.sh --dual)
# POSIX sh — aman untuk dash. Logika utama (deteksi monitor, loop anti-crash,
# resolusi aman 1024x768) ada di /home/$KIOSK_USER/kiosk-main.sh (bash).
xset s off -dpms &          # matikan blank layar & power-save monitor
pulseaudio --start --exit-idle-time=-1 &   # audio wajib untuk Web Audio API
unclutter -idle 3 &         # sembunyikan kursor mouse setelah 3 detik idle

[ -x /home/$KIOSK_USER/kiosk-main.sh ] && /home/$KIOSK_USER/kiosk-main.sh >/dev/null 2>&1 &
EOF

# Script utama (bash) — heredoc QUOTED sehingga tidak ada escaping $ yang rumit;
# nilai dinamis disuntikkan via sed placeholder di bawah.
cat > "/home/$KIOSK_USER/kiosk-main.sh" <<'MAIN_EOF'
#!/bin/bash
# Kiosk Karaoke DUAL SCREEN — dijalankan dari autostart openbox (POSIX sh)
# Log: /tmp/kiosk-autostart.log
set -u
shopt -s nullglob

BROWSER="__BROWSER__"
OP_URL="__OP_URL__"
PL_URL="__PL_URL__"

log() { echo "[$(date '+%H:%M:%S')] $*" >> /tmp/kiosk-autostart.log; }
log "mulai"

# --- LOCKFILE single-instance ---
# Openbox/lightdm bisa menjalankan autostart lebih dari sekali (restart sesi,
# duplicate loop sisa debug) -> dua loop chromium untuk user-data-dir SAMA akan
# saling rebut & restart berkala. flock memastikan hanya SATU kiosk-main.sh aktif;
# instance berikutnya keluar dengan bersih.
exec 9>/tmp/kiosk-main.lock
flock -n 9 || { log "instance kiosk-main.sh lain sudah berjalan — keluar"; exit 0; }

xset s off -dpms
pulseaudio --start --exit-idle-time=-1 2>/dev/null
unclutter -idle 3 &

# --- Resolusi aman: paksa 1024x768@60 STANDARD (65 MHz DMT — mode XP dulu) ---
# TV LG via VGA MENOLAK 1920x1080 dan mode "1024x768x75 doublescan" (EDID korup,
# 170 MHz) -> layar gelap "no signal". Jangan cuma --mode 1024x768 tanpa --rate!
# Catatan: xrandr return 0 walau output tidak ada (hanya warning) -> cek dulu.
set_mode() { # $1=output $2=mode $3=rate(opsional)
  if [ -n "${3:-}" ]; then
    xrandr --output "$1" --mode "$2" --rate "$3" 2>/dev/null
  else
    xrandr --output "$1" --mode "$2" 2>/dev/null
  fi
}
for out in VGA-1 VGA1 DVI-I-1; do
  xrandr --query 2>/dev/null | grep -qE "^${out}( |$)" || { log "$out tidak ada di xrandr"; continue; }
  for spec in "1024x768_60:" "1024x768:60" "800x600:60" "640x480:60"; do
    m="${spec%%:*}"; r="${spec#*:}"
    if set_mode "$out" "$m" "$r"; then log "resolusi $out -> ${m}@${r:-auto} OK"; break; fi
    log "$out gagal set ${m}@${r:-auto}"
  done
done

# --- Deteksi output yang DIPAKAI (connected + punya mode) ---
# Port HDMI/DVI-I-1 sengaja dipaksa "connected" oleh kernel (video=...D, tanpa
# EDID) karena monitor 2 terpasang via HDMI. Output dengan mode = layak dipakai.
# (EDID dibaca utk info saja; jangan pakai stat/-s — sysfs sering lapor 0.)
has_modes() { # $1=output -> ada baris mode?
  xrandr --query 2>/dev/null | sed -n "/^$1 /,/^[^ ]/p" | grep -qE "^[[:space:]]+[0-9]+x"
}
usable=""
for out in $(xrandr --query 2>/dev/null | awk '/ connected/ {print $1}'); do
  has_modes "$out" && usable="$usable $out"
done
usable="${usable# }"
log "output dipakai (connected+mode):${usable:-tidak ada}"

real_list=""
for sysedid in /sys/class/drm/card*-*/edid; do
  out=$(basename "$(dirname "$sysedid")")
  out=${out#card*-}
  n=$(cat "$sysedid" 2>/dev/null | wc -c)
  [ "$n" -gt 0 ] && real_list="$real_list $out"
done
real_list="${real_list# }"
log "output dgn EDID (asli):${real_list:-tidak ada}"

# Penetapan layar: LG TV (VGA) = OPERATOR, monitor HDMI/DVI = PLAYER.
# Bisa ditimpa dengan env OPERATOR_MONITOR=/PLAYER_MONITOR= (nama output xrandr).
player_out="" ; operator_out=""
if [ -n "${PLAYER_MONITOR:-}" ]; then
  player_out="$PLAYER_MONITOR"
  operator_out="${OPERATOR_MONITOR:-$(echo "$usable" | tr ' ' '\n' | grep -v "^$PLAYER_MONITOR$" | head -1)}"
elif [ -n "${OPERATOR_MONITOR:-}" ]; then
  operator_out="$OPERATOR_MONITOR"
  player_out="$(echo "$usable" | tr ' ' '\n' | grep -v "^$OPERATOR_MONITOR$" | head -1)"
else
  if echo "$usable" | tr ' ' '\n' | grep -qE '^VGA-?1$'; then
    operator_out=$(echo "$usable" | tr ' ' '\n' | grep -oE '^VGA-?1$' | head -1)
    player_out=$(echo "$usable" | tr ' ' '\n' | grep -vE '^VGA-?1$' | head -1)
  else
    operator_out=$(echo "$usable" | tr ' ' '\n' | awk 'NF{print; exit}')
    player_out=$(echo "$usable" | tr ' ' '\n' | awk 'n<2 && NF {n++; if(n==2) print}')
  fi
fi
[ -z "$player_out" ] && player_out="$operator_out"
[ -z "$operator_out" ] && operator_out="$player_out"
log "player_out=$player_out operator_out=$operator_out"

DUAL=0
if [ -n "$player_out" ] && [ -n "$operator_out" ] && [ "$player_out" != "$operator_out" ]; then
  DUAL=1
fi

# Posisi eksplisit supaya window TIDAK menumpuk di satu output (hindari clone).
xrandr --output "$operator_out" --pos 0x0 2>/dev/null
[ "$DUAL" -eq 1 ] && xrandr --output "$player_out" --pos 1024x0 2>/dev/null

geom_of() { # $1 = monitor -> "X,Y WxH" (fallback 0,0 1024x768)
  local g
  g=$(xrandr --query 2>/dev/null | awk -v m="$1" '$0 ~ m && / connected/ { for (i=1;i<=NF;i++) if ($i ~ /^[0-9]+x[0-9]+\+[0-9]+\+[0-9]+$/) print $i }')
  [ -z "$g" ] && { echo "0,0 1024x768"; return; }
  local size=${g%%+*} xy=${g#*+}
  echo "${xy/+/,} $size"
}

op_geom=$(geom_of "$operator_out")
op_pos=${op_geom%% *}; op_size=${op_geom#* }
pl_geom=$(geom_of "$player_out")
pl_pos=${pl_geom%% *}; pl_size=${pl_geom#* }
log "operator pos=$op_pos size=$op_size | player pos=$pl_pos size=$pl_size"

# Amankan: kalau posisi operator == posisi player (clone/gagal atur), fallback SINGLE
if [ "$DUAL" -eq 1 ] && [ "$op_pos" = "$pl_pos" ]; then
  log "posisi operator==player (clone) — fallback SINGLE"
  DUAL=0
fi
log "mode: $([ "$DUAL" -eq 1 ] && echo DUAL || echo SINGLE)"

launch_win() { # $1=nama(log) $2=URL $3=pos $4=size $5=user-data-dir
  local name="$1" url="$2" pos="$3" size="$4" udd="$5"
  ( while true; do
      "$BROWSER" --app="$url" \
        --window-position="$pos" --window-size="$size" \
        --noerrdialogs --disable-infobars --disable-translate \
        --disable-features=TranslateUI \
        --autoplay-policy=no-user-gesture-required \
        --disable-session-crashed-bubble --disable-gpu \
        --user-data-dir="$udd" &
      wait $!
      log "chromium $name exit, restart 3 detik"
      sleep 3
    done ) &
}

if [ "$DUAL" -eq 1 ]; then
  # LG TV (VGA) = OPERATOR · monitor HDMI = PLAYER
  launch_win operator "$OP_URL" "$op_pos" "$op_size" "/home/__KIOSK_USER__/.config/chromium-operator"
  launch_win player "$PL_URL" "$pl_pos" "$pl_size" "/home/__KIOSK_USER__/.config/chromium-player"
else
  # SINGLE: tampilkan window sesuai peran output yang tersedia
  if [ "$player_out" = "VGA-1" ] || [ "$player_out" = "VGA1" ]; then
    launch_win operator "$OP_URL" "$op_pos" "$op_size" "/home/__KIOSK_USER__/.config/chromium-operator"
    log "SINGLE (LG TV/VGA): OPERATOR ditampilkan."
  else
    launch_win player "$PL_URL" "$pl_pos" "$pl_size" "/home/__KIOSK_USER__/.config/chromium-player"
    log "SINGLE (HDMI): PLAYER ditampilkan."
  fi
fi

log "siap"

# Tunggu semua loop chromium (di-subshell background) — sekaligus membuat lockfile
# (fd 9) tetap terbuka selama kiosk-main.sh hidup; kalau skrip utama keluar, lock
# lepas dan instance duplikat bisa masuk lagi.
wait
MAIN_EOF

# Substitusi placeholder (heredoc quoted -> tidak ada masalah escaping $)
sed -i "s|__BROWSER__|$BROWSER_BIN|g; s|__OP_URL__|$OPERATOR_URL|g; s|__PL_URL__|$PLAYER_URL|g; s|__KIOSK_USER__|$KIOSK_USER|g" "/home/$KIOSK_USER/kiosk-main.sh"
chmod +x "/home/$KIOSK_USER/kiosk-main.sh"
say "    autostart POSIX + kiosk-main.sh ditulis (log: /tmp/kiosk-autostart.log)."
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
    --disable-session-crashed-bubble --disable-gpu \\
    --start-fullscreen \\
    "$PLAYER_URL"
  sleep 3
done &
EOF
fi
chown -R "$KIOSK_USER:$KIOSK_USER" "/home/$KIOSK_USER/.config"

# ---------- 5b. Resolusi aman utk TV/monitor jadul (1024x768@60 STANDARD) ----------
# TV via VGA MENOLAK 1920x1080 dan mode "1024x768x75 doublescan" (EDID korup,
# 170 MHz) -> layar gelap "no signal" padahal X jalan. Paksa mode STANDARD
# 65 MHz DMT (sama dengan XP dulu) di Xorg DAN di kernel KMS via GRUB.
say ">>> Resolusi aman 1024x768@60 (xorg.conf + kernel KMS)..."
mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/10-karaoke-resolution.conf <<'CONF'
Section "Monitor"
    Identifier  "VGA-1"
    Modeline    "1024x768_60" 65.00 1024 1048 1184 1344 768 771 777 806 -hsync -vsync
    Option      "PreferredMode" "1024x768_60"
EndSection

Section "Monitor"
    Identifier  "DVI-I-1"
    Modeline    "1024x768_60" 65.00 1024 1048 1184 1344 768 771 777 806 -hsync -vsync
    Option      "PreferredMode" "1024x768_60"
EndSection
CONF
say "    /etc/X11/xorg.conf.d/10-karaoke-resolution.conf ditulis."

if [ -f /etc/default/grub ]; then
  grep -q '^GRUB_GFXMODE=1024x768' /etc/default/grub || \
    sed -i 's|^#\?GRUB_GFXMODE=.*|GRUB_GFXMODE=1024x768|' /etc/default/grub
  if ! grep -q 'video=VGA-1:1024x768@60' /etc/default/grub; then
    sed -i 's|^GRUB_CMDLINE_LINUX_DEFAULT=.*|GRUB_CMDLINE_LINUX_DEFAULT="quiet video=VGA-1:1024x768@60 video=DVI-I-1:1024x768@60D"|' /etc/default/grub
    update-grub >/dev/null 2>&1 && say "    GRUB diperbarui (kernel KMS: VGA-1 1024x768@60; DVI-I-1 dipaksa @60e)." \
      || say "    ⚠️ update-grub gagal — jalankan manual setelah setup."
  fi
fi

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
