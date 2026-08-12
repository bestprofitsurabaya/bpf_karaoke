#!/usr/bin/env bash
# ============================================================
# Integrasi HDD Baru ke Pipeline Karaoke (v2 — optimal utk 2TB)
# ============================================================
# Tujuan: memindahkan folder media karaoke dari /srv
# (/srv/karaoke_media/transcoded, dan opsional lagu) ke HDD baru,
# lalu /srv meninggalkan symlink — TANPA mengubah jalur yang
# dipakai pipeline.
#
# ⚠️  WAJIB dijalankan setelah HDD terpasang & TERDETEKSI
#     (cek dulu: lsblk). Skrip akan MENGHENTIKAN stack karaoke
#     selama pemindahan (agar tidak ada ffmpeg/sync yang menulis).
#
# Optimasi v2 untuk HDD besar:
#   - mkfs.ext4 -m 0        → 0% reserved block (default 5% = ~92 GB
#                             hilang di HDD 2TB; reserved hanya perlu
#                             untuk disk sistem, bukan data media).
#   - mount noatime         → kurangi tulis metadata (awet & cepat).
#   - --move-all            → pindahkan lagu SEKALIGUS transcoded
#                             (1.3 TB muat di 2TB; /srv jadi lega total).
#   - --force-recreate      → container dibuat ulang agar bind mount
#                             mengikuti symlink baru (fix bug v1: stop+up
#                             tidak me-resolve symlink pada container lama).
#
# Penggunaan:
#   sudo ./setup_hdd.sh                 # interaktif, pilih device
#   sudo ./setup_hdd.sh --device=/dev/sdb
#   sudo ./setup_hdd.sh --move-all      # pindah transcoded + lagu
#   sudo ./setup_hdd.sh --skip-rsync    # folder sudah dipindah manual
#
# IDEMPOTEN: aman dijalankan ulang — bila HDD sudah terpasang/label
# media_hdd & symlink sudah ada, skrip TIDAK memformat ulang.
#
# KEAMANAN:
#   - TIDAK pernah menyentuh disk sistem (tolak device yang memuat
#     mountpoint sistem: / /var /srv /home /boot /usr /etc).
#   - Format hanya ke device yang dipilih USER secara eksplisit.
#   - rsync --info=progress2; sumber dihapus hanya setelah terverifikasi.
# ============================================================
set -u

MOUNT_POINT="/mnt/media_hdd"
MEDIA_BASE="/srv/karaoke_media"
SRC_TRANSCODED="${MEDIA_BASE}/transcoded"
SRC_LAGU="${MEDIA_BASE}/lagu"
TARGET_BASE="${MOUNT_POINT}/karaoke_media"
COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
SKIP_RSYNC=0
MOVE_ALL=0
DEVICE=""
LABEL="media_hdd"

while [ $# -gt 0 ]; do
  case "$1" in
    --device=*) DEVICE="${1#--device=}"; shift ;;
    --device) DEVICE="${2:-}"; shift 2 ;;
    --move-all) MOVE_ALL=1; shift ;;
    --skip-rsync) SKIP_RSYNC=1; shift ;;
    --help|-h) sed -n '1,60p' "$0" | grep '^#'; exit 0 ;;
    *) echo "Argumen tidak dikenal: $1 (coba --help)"; exit 1 ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say() { echo -e "$1"; }

say "${YELLOW}==================================================${NC}"
say "${YELLOW}  INTEGRASI HDD BARU — KARAOKE MEDIA (v2)${NC}"
say "${YELLOW}==================================================${NC}"

# ---------- Prasyarat ----------
[ "$(id -u)" -eq 0 ] || { say "${RED}Jalankan sebagai root (sudo).${NC}"; exit 1; }
command -v mkfs.ext4 >/dev/null || { say "${RED}mkfs.ext4 tidak ada.${NC}"; exit 1; }
command -v rsync >/dev/null || { say "${RED}rsync tidak ada.${NC}"; exit 1; }

# ---------- 0. Cek status sudah terpasang (idempotensi) ----------
LINKED_TRANSCODED=0; LINKED_LAGU=0
[ -L "$SRC_TRANSCODED" ] && LINKED_TRANSCODED=1
[ -L "$SRC_LAGU" ] && LINKED_LAGU=1

if [ "$LINKED_TRANSCODED" -eq 1 ] || [ "$LINKED_LAGU" -eq 1 ]; then
  for s in "$SRC_TRANSCODED" "$SRC_LAGU"; do
    if [ -L "$s" ]; then
      say "${GREEN}➡️  $s SUDAH symlink → $(readlink -f "$s")${NC}"
    fi
  done
  # Semua target yang direncanakan sudah symlink? → selesai (idempoten).
  ALL_DONE=1
  [ "$LINKED_TRANSCODED" -eq 0 ] && ALL_DONE=0
  if [ "$MOVE_ALL" -eq 1 ] && [ "$LINKED_LAGU" -eq 0 ]; then ALL_DONE=0; fi
  if [ "$ALL_DONE" -eq 1 ]; then
    if mountpoint -q "$MOUNT_POINT"; then
      say "${GREEN}   HDD ter-mount di $MOUNT_POINT. Tidak ada yang perlu dilakukan.${NC}"
      df -h "$MOUNT_POINT"
      exit 0
    else
      say "${RED}⚠️  Symlink ada tapi $MOUNT_POINT BELUM ter-mount.${NC}"
      say "    Mount dulu: sudo mount -a   (atau reboot bila fstab sudah berisi UUID)"
      exit 1
    fi
  fi
  say "${YELLOW}   Sebagian sudah symlink — lanjut untuk folder yang tersisa.${NC}"
fi
if mountpoint -q "$MOUNT_POINT"; then
  say "${YELLOW}⚠️  $MOUNT_POINT sudah ter-mount tapi folder belum symlink.${NC}"
  say "    Lanjut untuk memindahkan folder (tanpa format ulang)."
fi

# ---------- 1. Deteksi disk (auto-saran bila --device kosong) ----------
if [ -z "$DEVICE" ]; then
  SYSTEM_DEV=$(findmnt -no SOURCE /srv 2>/dev/null | sed 's/[0-9]*$//')
  say ""
  say "Disk yang terdeteksi:"
  lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL | grep -vE 'loop|sr0' || true
  say ""
  SUGGEST=""
  for d in /sys/block/sd*; do
    [ -e "$d" ] || continue
    dev="/dev/$(basename "$d")"
    [ "$dev" = "$SYSTEM_DEV" ] && continue
    SUGGEST="$dev"
    break
  done
  if [ -z "$SUGGEST" ]; then
    say "${RED}❌ TIDAK ADA disk kedua yang terdeteksi.${NC}"
    say ""
    say "  HDD baru belum terlihat oleh OS. Periksa:"
    say "   1. Kabel data SATA & power terpasang benar (kedua ujung)."
    say "   2. Masuk BIOS (Del/F2 saat boot) — apakah HDD muncul di daftar storage?"
    say "   3. Coba port SATA lain (motherboard ini punya 6 port, hanya port 1 terpakai)."
    say "   4. Setelah muncul di lsblk, jalankan ulang skrip ini."
    exit 1
  fi
  read -rp "Ketik device HDD baru [default: $SUGGEST]: " DEVICE
  DEVICE="${DEVICE:-$SUGGEST}"
fi

if [ ! -b "$DEVICE" ]; then
  say "${RED}❌ Device $DEVICE tidak ada / bukan block device.${NC}"
  exit 1
fi

# Keamanan: tolak disk sistem (mountpoint penting mana pun di device ini)
SYS_MOUNTS="/ /var /srv /home /boot /usr /etc"
DISK_MOUNTS=$(lsblk -nr -o MOUNTPOINTS "$DEVICE" 2>/dev/null)
for mp in $DISK_MOUNTS; do
  case " $SYS_MOUNTS " in
    *" $mp "*) say "${RED}❌ MENOLAK: $DEVICE berisi mountpoint sistem '$mp'!${NC}"; exit 1 ;;
  esac
done
if echo "$DEVICE" | grep -qE 'sda$|nvme0n1$|vda$|mmcblk0$'; then
  say "${RED}❌ MENOLAK: $DEVICE adalah disk utama sistem.${NC}"
  exit 1
fi

# ---------- 2. Info device & pilihan folder ----------
HAS_LABEL=$(blkid -s LABEL -o value "$DEVICE" 2>/dev/null)
HAS_MOUNT=$(lsblk -no MOUNTPOINTS "$DEVICE" 2>/dev/null | grep -v '^$' | head -1)
MODEL=$(lsblk -dno MODEL "$DEVICE" 2>/dev/null)

say ""
say "${GREEN}➡️  Device dipilih: $DEVICE  ($MODEL)${NC}"
say "    Ukuran   : $(lsblk -dno SIZE "$DEVICE")"
[ -n "$HAS_LABEL" ] && say "    Label    : $HAS_LABEL"
[ -n "$HAS_MOUNT" ] && say "    Mounted  : $HAS_MOUNT"
say ""

if [ "$HAS_LABEL" = "$LABEL" ]; then
  say "${GREEN}✓ Device sudah berlabel $LABEL (HDD ini pernah diproses). Format dilewati.${NC}"
  NEED_FORMAT=0
elif mountpoint -q "$MOUNT_POINT"; then
  say "${GREEN}✓ $MOUNT_POINT sudah ter-mount. Format dilewati (folder tinggal dipindah).${NC}"
  NEED_FORMAT=0
else
  say "    Isi $DEVICE saat ini:"
  lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$DEVICE" | tail -n +2 | sed 's/^/      /'
  if [ "$(lsblk -no NAME "$DEVICE" 2>/dev/null | wc -l)" -gt 1 ] || [ -n "$HAS_MOUNT" ]; then
    say "${RED}⚠️  $DEVICE memiliki partisi/mount yang ada — pastikan ini benar-benar HDD baru.${NC}"
  fi
  read -rp "FORMAT $DEVICE sebagai ext4 (seluruh isi HILANG)? [y/N] " CONF
  if [ "$CONF" != "y" ] && [ "$CONF" != "Y" ]; then
    say "Batal."; exit 0
  fi
  NEED_FORMAT=1
fi

if [ "$SKIP_RSYNC" -eq 0 ] && [ "$MOVE_ALL" -eq 0 ]; then
  read -rp "Pindahkan JUGA folder 'lagu' (sumber XP, ±760 GB) ke HDD? [y/N] (default: hanya transcoded) " MA
  case "$MA" in y|Y) MOVE_ALL=1 ;; *) MOVE_ALL=0 ;; esac
fi
if [ "$MOVE_ALL" -eq 1 ]; then
  say "    Rencana: pindahkan lagu + transcoded  (total ±1.3 TB → HDD 2TB)"
else
  say "    Rencana: pindahkan transcoded saja  (±555 GB)"
fi

# ---------- 3. Hentikan stack (wajib — hindari tulis saat pindah) ----------
say ""
say ">>> Menghentikan stack karaoke (agar tidak ada proses menulis)..."
if ! cd "$COMPOSE_DIR" || ! docker compose stop --time 180; then
  say "${RED}❌ Gagal menghentikan stack — batalkan agar tidak ada tulis selama migrasi.${NC}"
  exit 1
fi
say "    Stack dihentikan."

# ---------- 4. Format & mount ----------
if [ "$NEED_FORMAT" -eq 1 ]; then
  say ""
  say ">>> Memformat $DEVICE → ext4 (label $LABEL, reserved 0% agar 2TB terpakai penuh)..."
  mkfs.ext4 -F -m 0 -L "$LABEL" "$DEVICE" || { say "${RED}❌ Format gagal.${NC}"; exit 1; }
fi

say ">>> Memastikan mount point & mounting (noatime)..."
mkdir -p "$MOUNT_POINT"
if ! mountpoint -q "$MOUNT_POINT"; then
  mount -o noatime "$DEVICE" "$MOUNT_POINT" || { say "${RED}❌ Mount gagal.${NC}"; exit 1; }
else
  mount -o remount,noatime "$MOUNT_POINT" 2>/dev/null || true
fi

# fstab (UUID + nofail + noatime agar tidak menggantung boot bila HDD lepas)
UUID=$(blkid -s UUID -o value "$DEVICE")
if [ -n "$UUID" ] && ! grep -q "$UUID" /etc/fstab; then
  cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"
  echo "# HDD Karaoke Media (ditambahkan setup_hdd.sh)" >> /etc/fstab
  echo "UUID=$UUID $MOUNT_POINT ext4 defaults,nofail,noatime 0 2" >> /etc/fstab
  say "    fstab diperbarui (UUID=$UUID, nofail,noatime)."
else
  say "    fstab sudah memuat UUID ini / dilewati."
fi
mkdir -p "$TARGET_BASE"

# ---------- 5. Cek ruang & pindahkan folder ----------
AVAIL_B=$(df -B1 --output=avail "$MOUNT_POINT" | tail -1)
say ""
say ">>> Cek ruang: HDD tersedia $((AVAIL_B / 1024 / 1024 / 1024)) GB"

move_dir() {
  local src="$1" dst="$2" name="$3"
  # Pengaman: bila src sudah symlink, jangan rsync (rsync --remove-source-files
  # pada sumber symlink bisa menghapus file di HDD itu sendiri!).
  if [ -L "$src" ]; then
    say "    ⏭  $src sudah symlink — dilewati."
    return 0
  fi
  say ""
  say ">>> Menyalin ${src} → ${dst} (${name})..."
  rsync -a --info=progress2 --remove-source-files "$src/" "$dst/"
  local rc=$?
  find "$src" -type d -empty -delete 2>/dev/null || true
  local n_src; n_src=$(find "$src" -type f 2>/dev/null | wc -l)
  local n_dst; n_dst=$(find "$dst" -type f 2>/dev/null | wc -l)
  say "    rsync exit=$rc | sisa di sumber: $n_src | file di HDD: $n_dst"
  if [ "$rc" -ne 0 ] || [ "$n_src" -ne 0 ]; then
    say "${RED}❌ Pemindahan $name belum tuntas ($n_src file tersisa).${NC}"
    say "    HDD mungkin penuh. Periksa: df -h $MOUNT_POINT"
    say "    Setelah cukup ruang, jalankan ulang skrip (aman, idempoten)."
    exit 1
  fi
  if [ -d "$src" ] && [ ! -L "$src" ]; then
    # Pastikan benar-benar kosong (termasuk file tersembunyi/entri lain)
    # sebelum symlink — hindari ln -sfn membuat symlink BERSARANG di dalam
    # folder yang tidak kosong.
    if [ -n "$(ls -A "$src" 2>/dev/null)" ]; then
      say "${RED}⚠️  $src masih berisi entri tersisa — periksa manual, hentikan.${NC}"
      exit 1
    fi
    rmdir "$src" || { say "${RED}❌ Gagal menghapus folder kosong $src.${NC}"; exit 1; }
  fi
  ln -sfn "$dst" "$src"
  say "    Symlink dibuat: $src → $dst"
}

mkdir -p "$TARGET_BASE/lagu" "$TARGET_BASE/transcoded"

if [ "$SKIP_RSYNC" -eq 1 ]; then
  say ">>> (--skip-rsync) memakai folder yang sudah dipindah manual."
  for pair in "lagu:$SRC_LAGU:$TARGET_BASE/lagu" "transcoded:$SRC_TRANSCODED:$TARGET_BASE/transcoded"; do
    name="${pair%%:*}"; rest="${pair#*:}"
    src="${rest%%:*}"; dst="${rest#*:}"
    [ "$name" = "lagu" ] && [ "$MOVE_ALL" -eq 0 ] && continue
    if [ -L "$src" ]; then
      say "    ⏭  $src sudah symlink — dilewati."
      continue
    fi
    [ -d "$src" ] || continue
    left=$(find "$src" -type f 2>/dev/null | wc -l)
    [ "$left" -gt 0 ] && { say "${RED}⚠️  $src masih berisi $left file — hentikan.${NC}"; exit 1; }
    rmdir "$src" 2>/dev/null || true
    ln -sfn "$dst" "$src"
    say "    Symlink: $src → $dst"
  done
else
  if [ -L "$SRC_TRANSCODED" ]; then
    say "    ⏭  transcoded sudah symlink — dilewati."
  else
    move_dir "$SRC_TRANSCODED" "$TARGET_BASE/transcoded" "transcoded"
  fi
  if [ "$MOVE_ALL" -eq 1 ] && [ ! -L "$SRC_LAGU" ]; then
    move_dir "$SRC_LAGU" "$TARGET_BASE/lagu" "lagu"
  fi
fi

# ---------- 6. Passthrough mount utk karaoke_sync ----------
# PENTING: karaoke_sync me-mount /srv/karaoke_media:/srv_media:rw. Symlink
# /srv_media/transcoded (dan /srv_media/lagu) → /mnt/media_hdd/... akan PUTUS
# di dalam container (HDD tidak ter-mount di sana) sehingga transcoded_exists_for()
# gagal dan sync menyalin ulang semua sumber yang sudah punya MP4 (loop isi disk!).
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
if ! grep -q '/mnt/media_hdd' "$COMPOSE_FILE" 2>/dev/null; then
  cp "$COMPOSE_FILE" "$COMPOSE_FILE.bak.$(date +%Y%m%d%H%M%S)"
  python3 - "$COMPOSE_FILE" <<'PY'
import sys
p = sys.argv[1]
text = open(p, encoding="utf-8").read()
old = "      - /srv/karaoke_media:/srv_media:rw\n"
new = old + "      - /mnt/media_hdd:/mnt/media_hdd:rw\n"
if old in text and new not in text:
    text = text.replace(old, new, 1)
    open(p, "w", encoding="utf-8").write(text)
    print("docker-compose.yml: mount /mnt/media_hdd ditambahkan ke karaoke_sync")
else:
    print("docker-compose.yml: sudah ada / skip")
PY
else
  say "    (mount /mnt/media_hdd sudah ada di docker-compose.yml)"
fi

# ---------- 7. Start stack & verifikasi ----------
# --force-recreate PENTING: bind mount container dibuat saat container
# DIBUAT. Stop+up biasa tidak me-resolve symlink host yang baru; container
# lama akan tetap menunjuk folder lama yang sudah kosong.
say ""
say ">>> Menyalakan kembali stack karaoke (force-recreate agar bind mount mengikuti symlink)..."
if ! cd "$COMPOSE_DIR" || ! docker compose up -d --force-recreate; then
  say "${RED}❌ Gagal menyalakan stack — jalankan manual: docker compose up -d${NC}"
  exit 1
fi
say "    Stack dinyalakan."

say ""
say ">>> Verifikasi mount di dalam container (symlink harus ter-resolve)..."
sleep 8
docker exec karaoke_backend sh -c 'echo "transcoded: $(ls /media/transcoded/ 2>/dev/null | wc -l) file"; df -h /media/transcoded 2>/dev/null | tail -1' \
  || say "${RED}⚠️  Tidak bisa verifikasi karaoke_backend.${NC}"
[ "$MOVE_ALL" -eq 1 ] && \
  docker exec karaoke_backend sh -c 'echo "lagu: $(ls /media/lagu/ 2>/dev/null | wc -l) entri"; df -h /media/lagu 2>/dev/null | tail -1' \
  || true
docker exec karaoke_sync sh -c 'readlink -f /srv_media/transcoded 2>/dev/null; readlink -f /srv_media/lagu 2>/dev/null' \
  || say "${RED}⚠️  Tidak bisa verifikasi karaoke_sync.${NC}"

say ""
say "${GREEN}==================================================${NC}"
say "${GREEN} SELESAI! /srv kini lega.${NC}"
say "${GREEN}==================================================${NC}"
df -h /srv "$MOUNT_POINT"
