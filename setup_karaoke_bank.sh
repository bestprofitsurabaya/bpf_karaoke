#!/usr/bin/env bash
# ============================================================
# setup_karaoke_bank.sh — Pasang HDD bank karaoke (NTFS 2×2TB) di SERVER
# ============================================================
# Bank karaoke (2 HDD 2TB NTFS dari mesin XP lama) ditancapkan LANGSUNG
# ke server ini (bukan di kiosk). HDD berisi DATA 2TB — JANGAN diformat!
#
# Yang dilakukan skrip (AMAN & idempoten):
#   1. Install ntfs-3g bila belum ada (wajib utk NTFS di Linux)
#   2. Deteksi HDD bank: ukuran ~2TB + filesystem NTFS + label berisi
#      "Karaoke" (bank 1 = "Karaoke Ban[k]", bank 2 = "Karaoke 2")
#      ⚠️  TIDAK pernah menyentuh disk sistem (sda) / disk lain
#   3. Mount ke /mnt/karaoke_bank1 & /mnt/karaoke_bank2
#      (rw via ntfs-3g, opsi aman: big_writes, windows_names)
#   4. fstab (UUID + nofail + ro untuk bank — data aman dari tulis tak sengaja)
#   5. Verifikasi + ringkasan isi (folder lagu/transcoded?)
#
# Penggunaan:
#   sudo ./setup_karaoke_bank.sh            # deteksi & mount otomatis
#   sudo ./setup_karaoke_bank.sh --rw       # mount read-write (default: read-only)
#   sudo ./setup_karaoke_bank.sh --status   # cek status saja
#
# KEAMANAN:
#   - Format: TIDAK PERNAH. Skrip ini hanya MOUNT.
#   - Menolak disk sistem (sda) dan disk tanpa label karaoke.
#   - Default read-only (mount ro) → data 2TB aman dari modifikasi tak sengaja.
#     Pipeline server BISA streaming dari NTFS read-only. Untuk menulis balik
#     (mis. sync/transcode lanjutan) gunakan --rw secara sadar.
# ============================================================
set -u

MNT1="/mnt/karaoke_bank1"
MNT2="/mnt/karaoke_bank2"
RW=0
STATUS_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --rw) RW=1; shift ;;
    --status) STATUS_ONLY=1; shift ;;
    --help|-h) sed -n '1,40p' "$0" | grep '^#'; exit 0 ;;
    *) echo "Argumen tidak dikenal: $1 (coba --help)"; exit 1 ;;
  esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say() { echo -e "$1"; }

say "${YELLOW}==================================================${NC}"
say "${YELLOW}  PASANG HDD BANK KARAOKE (NTFS 2×2TB) DI SERVER${NC}"
say "${YELLOW}==================================================${NC}"

# ---------- 0. Status saja (boleh non-root) ----------
if [ "$STATUS_ONLY" -eq 1 ]; then
  say "\nDisk terpasang saat ini:"
  lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL | grep -vE 'loop|sr0'
  say ""
  for m in "$MNT1" "$MNT2"; do
    if mountpoint -q "$m"; then
      say "${GREEN}✓ $m ter-mount: $(df -h "$m" | tail -1 | awk '{print $2 " total, " $4 " free"}')${NC}"
    else
      say "✗ $m belum ter-mount"
    fi
  done
  exit 0
fi

[ "$(id -u)" -eq 0 ] || { say "${RED}Jalankan sebagai root (sudo).${NC}"; exit 1; }

# ---------- 1. Install ntfs-3g ----------
if ! command -v ntfs-3g >/dev/null 2>&1; then
  say "\n>>> ntfs-3g belum ada — menginstall..."
  if command -v apt-get >/dev/null 2>&1; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y ntfs-3g || { say "${RED}❌ Gagal install ntfs-3g.${NC}"; exit 1; }
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y ntfs-3g || { say "${RED}❌ Gagal install ntfs-3g.${NC}"; exit 1; }
  else
    say "${RED}❌ Package manager tidak dikenal — install ntfs-3g manual.${NC}"
    exit 1
  fi
  say "${GREEN}   ntfs-3g terpasang.${NC}"
else
  say "\n✓ ntfs-3g sudah ada: $(ntfs-3g --version 2>/dev/null | head -1)"
fi

# ---------- 2. Deteksi disk bank ----------
# Identifikasi: ukuran >= 1.5TB, NTFS, label mengandung "Karaoke"
say "\n>>> Mencari HDD bank karaoke (NTFS ~2TB, label 'Karaoke')..."
BANKS=()
while read -r dev; do
  [ -n "$dev" ] || continue
  info=$(lsblk -dno SIZE,FSTYPE,LABEL,MODEL "$dev" 2>/dev/null)
  size=$(echo "$info" | awk '{print $1}')
  fstype=$(echo "$info" | awk '{print $2}')
  label=$(echo "$info" | awk '{print $3}')
  model=$(echo "$info" | awk '{print $4}')
  # Ukuran ~2TB (1.5–2.2TB) + NTFS + label Karaoke
  case "$size" in
    1.[5-9]T|2.*T) ;; *) continue ;;
  esac
  [ "$fstype" = "ntfs" ] || continue
  echo "$label" | grep -qi "karaoke" || continue
  # Tolak disk sistem
  echo "$dev" | grep -qE 'sda$|nvme0n1$|vda$' && { say "${RED}⚠️  ${dev} = disk sistem — dilewati!${NC}"; continue; }
  BANKS+=("$dev")
  say "  ${GREEN}✓ BANK DITEMUKAN: $dev  $size  NTFS  label='$label'  ($model)${NC}"
done < <(lsblk -dn -o NAME | sed 's|^|/dev/|')

if [ "${#BANKS[@]}" -eq 0 ]; then
  say "${YELLOW}  HDD bank belum terdeteksi. Yang terpasang sekarang:${NC}"
  lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL | grep -vE 'loop|sr0'
  say ""
  say "${RED}❌ Tidak ada HDD NTFS berlabel 'Karaoke' (~2TB) yang terdeteksi.${NC}"
  say "   Periksa: kabel SATA/power, BIOS, dan `lsblk` setelah disk muncul."
  say "   Catatan: mount ini default READ-ONLY — data 2TB tidak akan disentuh."
  exit 1
fi

# ---------- 3. Mount ----------
MOPTS="big_writes,windows_names,streams_interface=none"
[ "$RW" -eq 1 ] && MOPTS="$MOPTS,rw" || MOPTS="$MOPTS,ro"

mount_bank() { # $1=dev $2=mountpoint $3=urutan(1/2)
  local dev="$1" mp="$2" order="$3" label
  label=$(lsblk -dno LABEL "$dev")
  say "\n>>> Mount $dev (label '$label') → $mp ..."
  mkdir -p "$mp"
  if mountpoint -q "$mp"; then
    say "    ⏭  $mp sudah ter-mount."
    return 0
  fi
  # Mount langsung dulu (coba rw; bila gagal karena NTFS dirty, pakai ro)
  if ! mount -t ntfs-3g -o "$MOPTS" "$dev" "$mp" 2>/dev/null; then
    say "    ⚠️  Mount $MOPTS gagal — coba read-only paksa..."
    mount -t ntfs-3g -o ro "$dev" "$mp" || { say "${RED}❌ Gagal mount $dev.${NC}"; return 1; }
  fi
  say "    ${GREEN}✓ Ter-mount. Isi: $(ls "$mp" 2>/dev/null | head -8 | tr '\n' ' ')${NC}"
  # fstab (UUID + nofail — boot tidak menggantung bila HDD lepas)
  local uuid
  uuid=$(blkid -s UUID -o value "$dev")
  local fstype_opt="ntfs-3g"
  local fstab_mode="ro"
  [ "$RW" -eq 1 ] && fstab_mode="rw"
  local fstab_opt="defaults,nofail,big_writes,windows_names,streams_interface=none,$fstab_mode"
  if [ -n "$uuid" ] && ! grep -q "$uuid" /etc/fstab; then
    cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"
    echo "# HDD Bank Karaoke $order (dari XP, dipasang setup_karaoke_bank.sh)" >> /etc/fstab
    echo "UUID=$uuid $mp $fstype_opt $fstab_opt 0 0" >> /etc/fstab
    say "    fstab diperbarui (UUID=$uuid, nofail, ${MOPTS})."
  else
    say "    fstab sudah memuat UUID ini / dilewati."
  fi
}

FAIL=0
mount_bank "${BANKS[0]}" "$MNT1" 1 || FAIL=1
if [ "${#BANKS[@]}" -gt 1 ]; then
  mount_bank "${BANKS[1]}" "$MNT2" 2 || FAIL=1
else
  say "${YELLOW}  ⚠️  Hanya 1 disk bank terdeteksi — yang kedua belum terpasang/terdeteksi.${NC}"
fi

# ---------- 4. Verifikasi ----------
say ""
say "${GREEN}==================================================${NC}"
say "${GREEN}  HASIL PEMASANGAN HDD BANK${NC}"
say "${GREEN}==================================================${NC}"
for m in "$MNT1" "$MNT2"; do
  if mountpoint -q "$m"; then
    say "  ${GREEN}✓ $m${NC}"
    df -h "$m" | tail -1 | sed 's/^/      /'
    say "    Isi (top): $(ls "$m" 2>/dev/null | head -6 | tr '\n' ' ')"
    say "    Mode: $([ "$RW" -eq 1 ] && echo 'read-write' || echo 'READ-ONLY (aman)')"
  else
    say "  ${RED}✗ $m belum ter-mount${NC}"
  fi
done
say ""
say "  Langkah lanjutan (setelah mount OK):"
say "    - Arahkan pipeline media ke bank: symlink /srv/karaoke_media/{lagu,transcoded}"
say "      → /mnt/karaoke_bank1|2/... (sesuaikan struktur folder di bank)."
say "    - atau resume sync dari panel admin (SMB kiosk .140) bila bank tetap di kiosk."
say "    - Cek:  sudo ./setup_karaoke_bank.sh --status"
[ "$FAIL" -eq 1 ] && exit 1
exit 0
