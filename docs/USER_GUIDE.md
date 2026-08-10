# 📖 BPF Karaoke System — Panduan Pengguna (User Guide)

Panduan lengkap penggunaan **BPF Karaoke System v3.0** untuk Operator, Pelanggan (Remote), Player (TV), dan Admin.

---

## 📑 Daftar Isi

- [Akses Halaman](#-akses-halaman)
- [1. Halaman Pilih Room (`/rooms`)](#1-halaman-pilih-room)
- [2. Operator Screen (`/operator?screen=1`)](#2-operator-screen)
- [3. Player Screen / TV (`/player?screen=2`)](#3-player-screen--tv)
- [4. Remote Control (`/remote`)](#4-remote-control-smartphone)
- [5. Admin Panel (`/admin`)](#5-admin-panel)
- [6. Sesi Room & Durasi Pemakaian](#6-sesi-room--durasi-pemakaian)
- [7. Pencarian Lagu YouTube](#7-pencarian-lagu-youtube)
- [8. Pipeline Sync → Transcode](#8-pipeline-sync--transcode)
- [9. Pemecahan Masalah (Troubleshooting)](#9-pemecahan-masalah)

---

## 🔗 Akses Halaman

| Halaman | URL |
|---------|-----|
| Beranda | `https://host:8443/` |
| **Pilih Room** | `https://host:8443/rooms` |
| Operator (layar sentuh) | `https://host:8443/operator?screen=1` |
| Player (TV) | `https://host:8443/player?screen=2` |
| Remote (HP pelanggan) | `https://host:8443/remote` |
| Admin | `https://host:8443/admin` |

---

## 🏠 1. Halaman Pilih Room

Halaman `https://host:8443/rooms` menampilkan semua room aktif sebagai kartu:

- 🟢 **Kosong** — room belum dipakai
- 🔴 **Terpakai** — tampil **sisa waktu sesi** real-time
- Setiap kartu menampilkan **kapasitas** (👥) dan **jumlah antrian** (🎵)
- Tombol langsung: **📺 Player** (buka TV room tsb di tab baru), **📱 Remote**, **🖥️ Operator**
- Tersedia tombol **"Buka Operator (Semua Room)"** di bagian bawah
- Status diperbarui otomatis setiap 20 detik

> 💡 Jika baru punya 1 room (mis. `BPFSurabaya`), halaman ini tetap berguna sebagai pintu masuk terpusat ke layar operator/player/remote.

---

## 🖥️ 2. Operator Screen

URL: `https://host:8443/operator?screen=1`

### Pilih Room
Klik nama room di **pojok kiri atas** (▾) → pilih room dari dropdown. Antrian, Now Playing, dan history otomatis berpindah. Room yang sedang dipakai/berantrian ditandai titik merah.

### Mencari & Menambah Lagu
- **🔍 Search Bar** — cari judul/artis, toleran typo (fuzzy)
- **Filter Genre** (chip) & **Filter Bahasa**
- **➕ Tambah Semua hasil** — masukkan semua lagu hasil filter sekaligus
- **☑ Batch** — centang banyak lagu lalu *Tambah ke Antrian* sekali jalan
- Klik **+** pada kartu lagu → masuk antrian

### ⏩ Putar Berikutnya (Play Next)
- Pada **kartu lagu**: tombol **⏩** — tambah lagu baru lalu geser ke posisi 2 (diputar tepat setelah lagu sekarang selesai)
- Pada **item yang sudah di antrian**: tombol **⏩** (biru) — geser item itu ke posisi "berikutnya" tanpa menambah duplikat
- Pada item antrian posisi 1: tombol **▶** hijau = **Putar Sekarang** (langsung memotong lagu yang sedang berjalan)

### Mengatur Antrian
- **⋮⋮ Drag & drop** untuk urut ulang
- **▲ / ▼** naik/turunkan posisi
- **✕** hapus item · **🗑️** kosongkan seluruh antrian
- Lagi diputar: tombol **⏸/▶**, **⏭ Skip** (skip = lanjut ke lagu berikutnya otomatis)

### Kontrol Audio & Visual
| Kontrol | Keterangan |
|---------|-----------|
| **🎹 Pitch/Key** | Naik/turun nada −12 s/d +12 semitone (seluruh room ikut) |
| **🎤 Vocal** | Stereo / Kiri / Kanan / AI Vocal Remove |
| **🔊 Volume** | Slider + mute |
| **🌙 Mode gelap** | Toggle tampilan operator |
| **📺 Launch Player** | Buka TV player di tab baru untuk room aktif |

### Pintasan Keyboard
| Tombol | Aksi |
|--------|------|
| `Space` | Play/Pause |
| `Esc` | Stop |
| `→` | Skip ke lagu berikutnya |
| `F` | Fullscreen |

### Status & Sesi Room
- **⏱️ Bar Sesi** di bawah header: `ROOM TERPAKAI` + sisa waktu, atau `ROOM KOSONG`
- Berubah **merah berkedip** saat sisa ≤ 5 menit

---

## 📺 3. Player Screen (TV)

URL: `https://host:8443/player?screen=2` (biasanya dibuka dari Operator via tombol 📺)

### Saat Ada Lagu Diputar
- Video karaoke fullscreen + **badge NOW PLAYING** dengan equalizer
- **Progress bar** tipis di bawah layar
- **NEXT ticker** di pojok kanan atas: judul lagu berikutnya
- **⏱️ SISA WAKTU** sesi room di atas tengah (merah berkedip jika ≤ 5 menit)

### Layar Idle (Antrian Ada)
- **QR Code** untuk remote HP
- Chip **"🎵 N lagu dalam antrian"**
- Kartu **"LAGU BERIKUTNYA"** — judul & artis lagu yang akan diputar setelah lagu sekarang selesai

### Layar Idle (Antrian Kosong / Welcome)
- Logo animasi + tombol **"Tap to Start"** (wajib ketuk sekali untuk mengaktifkan audio)
- Setelah itu tampil QR Code request lagu

### Layar "Sesi Berakhir" 🎤
- Muncul otomatis saat **durasi sesi room habis**: lagu yang sedang diputar **diselesaikan dulu sampai selesai**, lalu layar menampilkan **"Sesi Berakhir — Terima kasih telah bernyanyi!"**
- Antrian TIDAK dipotong di tengah lagu dan TIDAK lanjut otomatis ke lagu berikutnya
- Saat admin **memulai sesi baru**, player kembali normal (QR + antrian)

### Auto-Recovery (Anti Nyangkut)
- Video gagal dimuat (error fatal) → otomatis lewati ke lagu berikutnya
- Player TV mati/reload di tengah lagu → saat kembali, lagu yang sama **dilanjutkan** (resume)
- Lagu "playing" tanpa progress > 20 menit (player crash) → otomatis di-skip oleh watchdog, antrian tetap berjalan

---

## 📱 4. Remote Control (Smartphone)

URL: `https://host:8443/remote` — buka lewat **scan QR di layar TV**.

- **🔍 Cari lagu** — judul/artis, filter genre, dan tab **▶ YouTube** (lagu yang tidak ada di database)
- **+** untuk request lagu → masuk antrian room (terlihat oleh operator)
- **Antrian Saya** — lihat & batalkan request sendiri (identitas per HP via ID tamu)
- **Now Playing** — lagu yang sedang diputar
- Room otomatis mengikuti parameter `?room=` dari QR (tidak tersesat ke room lain)

---

## ⚙️ 5. Admin Panel

URL: `https://host:8443/admin` (login admin; wajib ganti password saat pertama login)

### Dashboard
- Statistik: total lagu, pemutaran, antrian, koneksi aktif
- **Pipeline Transcode** (auto-refresh 30 detik): antrian, pending, MP4 siap, sumber tersisa, `.part` basi, disk bebas
  - Peringatan merah jika `.part` basi > 0 atau disk < 50 GB
  - Tombol **🔍 Scan** (jadwalkan scan folder media) dan **🧹 Sweep** (bersihkan `.part` yatim) — admin only

### Manajemen
| Menu | Fungsi |
|------|--------|
| **Lagu** | Edit, hapus, bulk update genre, deteksi genre AI |
| **Room** | Tambah/edit/hapus room, kapasitas |
| **Sesi Room** | Mulai / perpanjang / akhiri sesi, riwayat pemakaian |
| **Scanner Media** | Scan folder `media/lagu/` + auto genre |
| **Pengguna** | Kelola operator & admin |

### 🎤 Sesi Room (Durasi Pemakaian)
- **Mulai Sesi**: pilih durasi (menit) **atau** waktu selesai absolut → room terhitung terpakai, timer tampil di Operator & Player
- **Perpanjang**: tambah menit / ubah waktu selesai
- **Akhiri**: sesi ditutup; lagu yang sedang diputar tetap diselesaikan lalu berhenti otomatis
- Sesi **expired otomatis** bila waktu habis — perilaku berhenti yang sama (anti potong di tengah lagu)

---

## ▶️ 7. Pencarian Lagu YouTube

Fitur mencari & memutar lagu **yang tidak tersedia offline** di database:

- Di **Operator** / **Remote**: aktifkan chip **▶ YouTube**, ketik judul → hasil dari YouTube Data API v3
- Klik **+** → lagu masuk antrian sebagai item `▶ YT`
- Di **Player TV**: lagu YouTube diputar via embed player; error 3x beruntun (video privat/dihapus) → otomatis skip
- Batasan: perlu `YOUTUBE_API_KEY` di `.env` (sudah terisi); kuota API harian berlaku

---

## 🔄 8. Pipeline Sync → Transcode

Alur otomatis dari **share SMB (Windows XP)** → database → MP4 siap putar:

```
Share SMB (XP)  →  smb_sync (salin .part + rename)  →  scan media  →  transcode (Celery)  →  MP4 siap
```

- **Monitor**: `./pipeline_monitor.sh` — ringkasan sync, transcode, antrian, disk
- **Cek sync**: `./check_sync.sh`
- File `.mpg/.mpeg` sumber yang sudah berhasil di-transcode **dihapus otomatis** dari penyimpanan
- **File bermasalah** (gagal disalin 3 pass berturut-turut) di-skip otomatis agar tidak memblokir sync; dicoba ulang berkala
- **Laporan mingguan** pipeline dikirim ke webhook (Telegram/Discord/Slack) setiap Senin 07:00 — isi `SMB_WEBHOOK_URL` di `.env` untuk mengaktifkan
- Dokumentasi keamanan: [SMB_SECURITY.md](SMB_SECURITY.md)

---

## 🔧 9. Pemecahan Masalah

| Masalah | Solusi |
|---------|--------|
| **Player TV diam / tidak lanjut lagu** | Pastikan halaman player dibuka; jika TV mati saat lagu berjalan, lagu di-skip otomatis ≤ 20 menit. Reload TV → lagu berlanjut |
| **"Sesi Berakhir" muncul** | Durasi room habis — admin perlu **mulai sesi baru / perpanjang** agar antrian lanjut |
| **Lagu tidak ada suara di TV** | Ketuk layar sekali (autoplay policy browser); tombol **Tap to Start** |
| **Lagu YouTube tidak muncul** | Cek `YOUTUBE_API_KEY` & kuota API; pastikan video tidak privat/dihapus |
| **Sync error `Errno 9` / koneksi putus** | Koneksi SMB ke XP terputus sementara — sync otomatis reconnect & retry; file bermasalah di-skip setelah 3 gagal |
| **Antrian tertahan** | Gunakan tombol **🗑️ Clear Queue** atau skip; watchdog anti-nyangkut bekerja otomatis |
| **Login admin ditolak** | 5x gagal → kunci 15 menit (brute-force protection); hubungi admin lain untuk reset |

---

© 2026 BPF Karaoke System — Best Profit Futures Entertainment
