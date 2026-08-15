# 🎤 BPF Karaoke System

<div align="center">

**Sistem Karaoke Modern dengan Dual-Screen, AI/ML, Celery Background Tasks & ISO 27001 Security**

[Features](#-features) • [Architecture](#-architecture) • [Dokumentasi](#-dokumentasi)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Dokumentasi](#-dokumentasi)

---

## 🎯 Overview

**BPF Karaoke System v3.0** adalah aplikasi karaoke enterprise berbasis web dengan:

- **Multi-Room Management** — Queue terpisah per room
- **AI-Powered Genre Detection** — Auto-classify lagu baru
- **Drag & Drop Queue** — Atur ulang antrian dengan mudah
- **Real-time Progress Bar** — Monitor pemutaran lagu
- **ISO 27001 Security** — bcrypt, brute-force protection, audit logging
- **Celery Background Tasks** — AI vocal remove, batch genre detection
- **Keyboard Shortcuts** — Space, Esc, Arrow untuk operator cepat
- **Favorites & History** — Bookmark lagu andalan, lihat riwayat

---

## ✨ Features

### 🎵 Operator Screen (Touchscreen)

| Feature | Description |
|---------|-------------|
| **🔍 Smart Search** | Pencarian dengan fuzzy matching + filter genre |
| **📋 Drag & Drop Queue** | Seret lagu untuk atur ulang antrian |
| **⏩ Play Next** | Kartu lagu & item antrian — geser ke posisi berikutnya |
| **🗑️ Clear Queue** | Kosongkan seluruh antrian satu klik |
| **📋 Batch Add** | Pilih banyak lagu dengan checkbox, tambah sekaligus |
| **⭐ Favorites** | Bookmark lagu favorit untuk akses cepat |
| **🕐 History** | Riwayat lagu yang sudah diputar per room |
| **🎹 Pitch/Key Control** | Naik/turunkan nada -12 s/d +12 semitone |
| **🎤 Vocal Control** | Stereo/Left/Right + AI Vocal Remove |
| **⌨️ Keyboard Shortcuts** | Space=Play/Pause, Esc=Stop, →=Skip |
| **📊 Progress Bar** | Real-time progress di Now Playing card |
| **⏱️ Sesi Room** | Timer durasi pemakaian + peringatan ≤ 5 menit |
| **📺 Launch Player** | Buka player di tab baru dari operator |
| **🏠 Room Selector** | Halaman `/rooms` — pilih room, status sesi & antrian |

### 📺 Player Screen (TV)

| Feature | Description |
|---------|-------------|
| **🎬 Cinematic Display** | Particle background, animated logo |
| **🔄 Auto-Play Next** | Otomatis putar lagu berikutnya (5 detik jeda) |
| **🛡️ Anti-Nyangkut** | Watchdog skip lagu macet, resume TV, video error auto-skip |
| **⏱️ Countdown Timer** | Ring countdown sebelum lagu berikutnya |
| **⏭️ Next Ticker** | Nama lagu berikutnya (saat putar & saat idle) |
| **📊 Progress Bar** | Progress pemutaran tipis di bawah layar |
| **🎤 Sesi Berakhir** | Lagu diselesaikan dulu lalu berhenti rapi saat durasi habis |
| **📱 QR Code** | Real QR code generator untuk remote |
| **🔊 Unmute Prompt** | Solusi autoplay policy browser |

### 📱 Remote Control (Smartphone)

| Feature | Description |
|---------|-------------|
| **🎵 Now Playing Strip** | Lihat lagu sedang diputar |
| **🎉 Mood Chips** | Party, Romantic, Nostalgia, Chill quick filters |
| **▶ YouTube Search** | Cari lagu yang tidak ada di database (YouTube API) |
| **📋 My Queue** | Lihat & hapus request sendiri |
| **📱 QR Share** | QR code modal untuk share ke teman |

### ⚙️ Admin Panel

| Feature | Description |
|---------|-------------|
| **📊 Dashboard** | Statistik + Pipeline Transcode monitor |
| **🎵 Song Management** | Edit, delete, bulk genre update |
| **🏠 Room Management** | CRUD rooms + **Sesi Room** (mulai/perpanjang/akhiri) |
| **📂 Media Scanner** | Auto-scan + AI genre detection |
| **🔍 Pipeline Scan/Sweep** | Trigger scan media & bersihkan `.part` basi (admin) |
| **⏸ Pipeline Pause/Resume** | Hentikan/lanjutkan transcode SEKETIKA dari panel (matikan ffmpeg + kosongkan antrian; master tetap aman, resume mengantre ulang otomatis) |
| **🤖 Auto Genre** | AI predict genre untuk semua lagu |

### 🤖 AI/ML Features

| Feature | Technology | Description |
|---------|------------|-------------|
| **🎭 Mood Detection** | Pattern Analysis | Deteksi mood ruangan |
| **🔍 Smart Search** | Fuzzy Matching | Toleransi typo |
| **🎵 Auto Playlist** | Rule-based | Generate playlist by mood/genre |
| **🏷️ Genre Detector** | Keyword + Fuzzy | Auto-classify lagu baru |
| **🎤 Vocal Remove** | FFmpeg/Spleeter | AI pemisah vokal (Celery task) |
| **🔄 Recommendations** | TF-IDF + Cosine | Rekomendasi lagu serupa |
| **▶ YouTube Search** | YouTube Data API v3 | Cari lagu tidak tersedia offline |

### 🔐 Security (ISO 27001 Level 2)

| Feature | Description |
|---------|-------------|
| **🔒 bcrypt Hashing** | Industry standard password hashing |
| **🛡️ Brute-Force Protection** | 5x gagal → lock 15 menit |
| **🔄 Force Password Change** | Wajib ganti password first login |
| **📝 Audit Logging** | Catat semua login attempt |
| **🔑 Password Policy** | Minimal 8 karakter, uppercase, lowercase, angka, spesial |

---

## 🏗️ Architecture

Sistem berjalan sebagai **stack Docker** di satu server NAS, dengan tiga layar
terpisah (Operator touchscreen, Player TV, dan Remote HP) yang berkomunikasi
secara real-time lewat WebSocket:

```
┌───────────────┐     HTTPS/WSS      ┌──────────────────────────────┐
│  Operator      │ ◄───────────────► │  Nginx (8443, SSL)           │
│  Player (TV)   │                   │  ├─ Frontend Vue 3 (SPA)     │
│  Remote (HP)   │                   │  └─ API FastAPI (backend)    │
└───────────────┘                    │     ├─ Socket.IO (realtime)  │
       kiosk / browser               │     ├─ Celery (transcode,    │
                                     │     │   AI genre, vocal)     │
                                     │     ├─ Redis (antrian, cache)│
                                     │     └─ PostgreSQL (database) │
                                     └──────────────────────────────┘
                                            ▲
                                            │ SMB / local disk
                                     ┌──────┴───────────┐
                                     │ Media bank (lagu  │
                                     │  & transcoded MP4)│
                                     └──────────────────┘
```

Komponen inti:

- **`backend/`** — FastAPI + Socket.IO: manajemen room, antrian, pemutaran,
  sesi, media streaming, dan endpoint AI.
- **`frontend/`** — Vue 3 (Vite): Operator, Player, Remote, dan Admin screens.
- **`karaoke_sync`** — sinkronisasi lagu dari share SMB (atau HDD lokal bank)
  ke folder media, disalin incremental + resume.
- **`karaoke_celery*`** — task background: transcode video, deteksi genre AI,
  vocal remove, dan laporan berkala.
- **AI/ML** — model ter-train dari puluhan ribu lagu untuk mood, rekomendasi,
  smart search, dan generator playlist (endpoint `/api/ai/*`).

## Dokumentasi

- **📖 [Panduan Pengguna (User Guide)](docs/USER_GUIDE.md)** — cara pakai Operator, Player, Remote, Admin, Sesi Room, YouTube, dan Troubleshooting
- [Keamanan Share SMB & Operasional](docs/SMB_SECURITY.md)
- Cek status: `./check_sync.sh` · Monitor pipeline: `./pipeline_monitor.sh`
