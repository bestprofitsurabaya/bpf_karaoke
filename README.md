# 🎤 BPF Karaoke System

<div align="center">

![BPF Karaoke](https://img.shields.io/badge/BPF-Karaoke-red?style=for-the-badge)
![Version](https://img.shields.io/badge/version-2.0.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12-green?style=for-the-badge&logo=python)
![Vue.js](https://img.shields.io/badge/Vue.js-3.4-brightgreen?style=for-the-badge&logo=vue.js)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)
![License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)

**Sistem Karaoke Modern dengan Dual-Screen, Remote Smartphone, dan AI/ML Features**

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [User Guide](#-user-guide) • [API Docs](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [User Guide](#-user-guide)
- [API Documentation](#-api-documentation)
- [AI/ML Features](#-aiml-features)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**BPF Karaoke System** adalah aplikasi karaoke modern berbasis web yang dirancang untuk menggantikan sistem karaoke tradisional. Dibangun dengan arsitektur **client-server** menggunakan **Docker**, aplikasi ini mendukung:

- **Dual-Screen** (Touchscreen Operator + TV Player)
- **Remote Control via Smartphone** (QR Code based)
- **AI-Powered Recommendations** (Content-Based Filtering)
- **Real-time Communication** (WebSocket/Socket.IO)
- **Progressive Web App** (PWA) support

### 🎬 Demo Screenshots

| Operator Screen | Player Screen | Remote Control |
|:---:|:---:|:---:|
| Touchscreen untuk pilih lagu | Tampilan TV Karaoke | Kontrol dari HP |

---

## ✨ Features

### 🎵 Core Features

| Feature | Description |
|---------|-------------|
| **🎤 Song Management** | Tambah, edit, hapus lagu dengan metadata lengkap |
| **📋 Smart Queue** | Antrian lagu yang bisa diatur ulang, skip, pause |
| **🔍 Search** | Pencarian lagu berdasarkan judul, artis, genre |
| **📺 Dual Screen** | Operator screen + TV player terpisah |
| **📱 Remote Control** | Kontrol dari smartphone via QR Code |
| **🎚️ Vocal Control** | Matikan/hidupkan vokal (Left/Right/Stereo) |
| **📊 Dashboard** | Statistik pemutaran lagu |
| **📂 Media Scanner** | Auto-scan folder untuk lagu baru |

### 🤖 AI/ML Features

| Feature | Technology | Description |
|---------|------------|-------------|
| **🎭 Mood Detection** | Pattern Analysis | Deteksi mood ruangan dari pilihan lagu |
| **🔍 Smart Search** | Fuzzy Matching | Pencarian toleran typo (Levenshtein Distance) |
| **🎵 Auto Playlist** | Rule-based | Generate playlist berdasarkan genre/mood/dekade |
| **🎤 Voice Scoring** | Signal Processing | Deteksi aktivitas vokal & scoring |
| **🔄 Recommendations** | TF-IDF + Cosine Similarity | Rekomendasi lagu serupa |

### 🎨 UI/UX

- **Red-Blue Aesthetic Theme** - Modern, cerah, dan eye-catching
- **Responsive Design** - Bekerja di semua ukuran layar
- **Dark/Light Mode** - Untuk kenyamanan mata
- **Smooth Animations** - Transisi halus antar halaman
- **PWA Support** - Installable di desktop & mobile

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DEBIAN SERVER (Trixie)                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              NGINX REVERSE PROXY                      │  │
│  │         Port 8443 (SSL Let's Encrypt)                 │  │
│  └────────┬─────────────────────────┬───────────────────┘  │
│           │                         │                       │
│  ┌────────▼──────────┐    ┌─────────▼──────────────┐      │
│  │  KARAOKE FRONTEND │    │   KARAOKE BACKEND      │      │
│  │  Vue 3 PWA + Nginx│    │   FastAPI + Socket.IO  │      │
│  │  Port: 3001       │    │   Port: 5002           │      │
│  └───────────────────┘    └─────────┬──────────────┘      │
│                                      │                      │
│                           ┌──────────▼──────────────┐      │
│                           │   POSTGRESQL 16         │      │
│                           │   Port: 5433            │      │
│                           └─────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              MEDIA STORAGE                           │  │
│  │         /media/lagu/ (Video Files)                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐         ┌────▼────┐         ┌─────▼─────┐
    │ ROOM 1  │         │ ROOM 2  │         │  ROOM N   │
    │Mini PC  │         │Mini PC  │         │ Mini PC   │
    │+ Touch  │         │+ Touch  │         │ + Touch   │
    │+ TV HDMI│         │+ TV HDMI│         │ + TV HDMI │
    └─────────┘         └─────────┘         └───────────┘
```

### Network Flow

```
[Smartphone] ──WiFi──┐
                     ├──► [Nginx :8443] ──► [Backend :5002] ──► [PostgreSQL :5433]
[Touchscreen] ──LAN──┘                              │
                                                    ├──► [Media Storage]
                                                    └──► [TV Player Screen]
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.12 | Main programming language |
| **FastAPI** | 0.111 | REST API framework |
| **Socket.IO** | 5.11 | Real-time WebSocket communication |
| **SQLAlchemy** | 2.0 | ORM (Async) |
| **PostgreSQL** | 16 | Database |
| **Uvicorn** | 0.29 | ASGI server |
| **scikit-learn** | 1.5 | Machine Learning |
| **fuzzywuzzy** | 0.18 | Fuzzy string matching |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Vue.js** | 3.4 | Frontend framework |
| **Vite** | 5.0 | Build tool |
| **Pinia** | 2.1 | State management |
| **Socket.IO Client** | 4.7 | WebSocket client |
| **Axios** | 1.6 | HTTP client |
| **Tailwind CSS** | 3.4 | Utility-first CSS |
| **PWA Plugin** | 0.19 | Progressive Web App |

### DevOps
| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **Nginx** | Reverse proxy & static files |
| **Let's Encrypt** | SSL/TLS certificates |
| **Debian Trixie** | Server OS |

---

## 📦 Prerequisites

### Server Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Debian 12/13 (Trixie) | Ubuntu 22.04+ / Debian 13 |
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 20 GB SSD | 50+ GB SSD + HDD for media |
| **Docker** | 24.0+ | Latest |
| **Docker Compose** | 2.0+ | Latest |

### Client Room Requirements (Per Room)

| Component | Specification |
|-----------|---------------|
| **Mini PC** | Intel N95/N100, 4GB RAM |
| **Touchscreen** | 15-21 inch capacitive |
| **TV** | LED 32-50 inch with HDMI |
| **Network** | WiFi/LAN connected |

### Software Dependencies

```bash
# Required packages on Debian/Ubuntu
sudo apt update
sudo apt install -y \
    docker.io \
    docker-compose-plugin \
    git \
    curl \
    nginx
```

---

## 🚀 Installation

### Quick Start (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/bpf-karaoke.git
cd bpf-karaoke

# 2. Create environment file
cp .env.example .env
nano .env  # Edit passwords and settings

# 3. Create media directory
mkdir -p media/lagu

# 4. Build and start all services
docker compose up -d --build

# 5. Check status
docker compose ps
docker compose logs -f
```

### Step-by-Step Installation

<details>
<summary><b>1. Clone & Setup Environment</b></summary>

```bash
# Clone the repository
git clone https://github.com/yourusername/bpf-karaoke.git
cd bpf-karaoke

# Create .env file
cat > .env << 'EOF'
DB_USER=karaoke_admin
DB_PASSWORD=YourSecurePassword123!
DB_NAME=karaoke_db
DB_PORT=5433

JWT_SECRET=YourJWTSecretKeyAtLeast32Characters!
SERVER_HOST=your-domain.com
SERVER_PORT=8443

ADMIN_USER=admin
ADMIN_PASSWORD=YourAdminPassword123!

MEDIA_PATH=/media/lagu
EOF
```
</details>

<details>
<summary><b>2. Configure Nginx Reverse Proxy</b></summary>

```bash
# Copy karaoke config to your existing Nginx
sudo cp nginx/karaoke.conf /etc/nginx/conf.d/

# If using Docker Nginx (like Nextcloud setup)
docker cp nginx/karaoke.conf nextcloud_nginx:/etc/nginx/conf.d/
docker restart nextcloud_nginx
```
</details>

<details>
<summary><b>3. Setup SSL Certificate</b></summary>

```bash
# If you already have certbot certificates
sudo cp -r /etc/letsencrypt ./ssl/

# Or generate new certificates
sudo certbot certonly --standalone -d your-domain.com
sudo cp -r /etc/letsencrypt ./ssl/
```
</details>

<details>
<summary><b>4. Build & Deploy</b></summary>

```bash
# Build all containers
docker compose build --no-cache

# Start services
docker compose up -d

# Check logs
docker compose logs -f

# Verify installation
curl -k https://localhost:8443/api/health
```
</details>

### Post-Installation

```bash
# 1. Add media files
cp your-karaoke-videos/*.mp4 media/lagu/

# 2. Scan media from Admin Panel
# Visit: https://your-domain:8443/admin
# Click "Scan Media Folder"

# 3. Access the application
# Home: https://your-domain:8443
# Operator: https://your-domain:8443/operator?screen=1
# Player: https://your-domain:8443/player?screen=2
# Remote: https://your-domain:8443/remote
# Admin: https://your-domain:8443/admin
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL username | `karaoke_admin` |
| `DB_PASSWORD` | PostgreSQL password | *Required* |
| `DB_NAME` | Database name | `karaoke_db` |
| `DB_PORT` | Database port | `5433` |
| `JWT_SECRET` | JWT signing key | *Required* |
| `SERVER_HOST` | Server hostname | `localhost` |
| `SERVER_PORT` | Server port | `8443` |
| `ADMIN_USER` | Admin username | `admin` |
| `ADMIN_PASSWORD` | Admin password | *Required* |
| `MEDIA_PATH` | Media files path | `/media/lagu` |

### Nginx Configuration

The application uses Nginx as reverse proxy with:
- **SSL/TLS** via Let's Encrypt
- **WebSocket** support for Socket.IO
- **Static file** caching
- **CORS** headers
- **Security** headers (X-Frame-Options, XSS Protection, etc.)

### Database Schema

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    songs     │     │    queue      │     │   users     │
├─────────────┤     ├──────────────┤     ├─────────────┤
│ id          │◄────│ song_id      │     │ id          │
│ title       │     │ room_id      │     │ username    │
│ artist      │     │ status       │     │ password    │
│ genre       │     │ priority     │     │ role        │
│ file_path   │     │ created_at   │     │ is_active   │
│ play_count  │     └──────────────┘     └─────────────┘
└─────────────┘
      │
      │          ┌──────────────┐
      └──────────│  playlists   │
                 ├──────────────┤
                 │ id           │
                 │ name         │
                 │ songs (JSON) │
                 └──────────────┘
```

---

## 📖 User Guide

### 🖥️ Role 1: Operator / Kasir

**URL:** `https://your-domain:8443/operator?screen=1`

Operator bertanggung jawab menjalankan sistem karaoke untuk pelanggan.

#### Cara Menggunakan:

1. **Login (Opsional)**
   - Buka halaman operator
   - Gunakan kredensial: `operator` / `operator123`

2. **Mencari Lagu**
   ```
   ┌─────────────────────────────────────────┐
   │ 🔍 Cari judul lagu atau nama artis...    │
   └─────────────────────────────────────────┘
   ```
   - Gunakan **Search Bar** di bagian atas
   - Filter dengan **Genre Chips** (Pop Indo, Dangdut, dll)
   - Klik **Kategori Cepat** untuk filter instant

3. **Menambah ke Antrian**
   - Klik kartu lagu yang diinginkan
   - Atau klik tombol **+** (merah) di setiap lagu
   - Lagu akan muncul di **Sidebar Antrian** (kiri)

4. **Mengatur Antrian**
   ```
   ┌──────────────────┐
   │ 1. Judul Lagu A  │ ▶ ✕
   │ 2. Judul Lagu B  │ ▶ ✕
   │ 3. Judul Lagu C  │ ▶ ✕
   └──────────────────┘
   ```
   - **▶** = Play Now (langsung putar)
   - **✕** = Hapus dari antrian

5. **Kontrol Pemutaran**
   ```
   ┌──────────────────────────────────────────┐
   │ 🎤 Sedang Diputar                        │
   │ Judul Lagu - Artis                       │
   │ [⏸ Pause] [⏭ Skip] [🔊 ===----]         │
   └──────────────────────────────────────────┘
   ```

6. **Menggunakan AI Panel** (Sidebar Kanan)
   - **Tab Mood** 🎭 : Lihat mood ruangan & saran lagu
   - **Tab Cari** 🔍 : Smart search dengan toleransi typo
   - **Tab Playlist** 🎵 : Generate playlist otomatis
   - **Tab Mirip** 🔄 : Lihat lagu serupa

#### Keyboard Shortcuts:
| Shortcut | Action |
|----------|--------|
| `Space` | Play/Pause |
| `→` | Next song |
| `←` | Previous song |
| `↑/↓` | Volume up/down |
| `F` | Toggle fullscreen |

---

### 📱 Role 2: Pelanggan / Tamu (Remote HP)

**URL:** `https://your-domain:8443/remote`

Pelanggan dapat request lagu langsung dari smartphone mereka.

#### Cara Menggunakan:

1. **Scan QR Code**
   - QR Code muncul di layar TV karaoke
   - Buka kamera HP, arahkan ke QR Code
   - Atau buka langsung URL remote di browser

2. **Mencari Lagu**
   ```
   ┌────────────────────────────────┐
   │ 🔍 Cari lagu favoritmu...      │
   └────────────────────────────────┘
   └─ [🇮🇩 Pop] [🎶 Dangdut] [🌍 Barat]
   ```

3. **Request Lagu**
   - Scroll daftar lagu
   - Klik lagu yang diinginkan
   - Klik tombol **+** untuk request
   - Muncul notifikasi "✅ Ditambahkan ke antrian!"

4. **Lihat Status**
   - **Now Playing**: Lihat lagu yang sedang diputar
   - **Antrian Saya**: Lihat request yang sudah dibuat
   - Bisa hapus request dengan klik **✕**

#### Tips:
- 📶 Pastikan HP terhubung ke WiFi yang sama dengan server
- 🔄 Refresh halaman jika koneksi terputus
- 📱 Tambahkan ke Home Screen untuk akses cepat (PWA)

---

### 📺 Role 3: TV Player Screen

**URL:** `https://your-domain:8443/player?screen=2`

Tampilan yang ditampilkan di TV/proyektor untuk penonton.

#### Mode Tampilan:

**1. Idle Mode** (Tidak ada lagu)
```
┌─────────────────────────────────────┐
│                                     │
│           🎤                        │
│      BPF KARAOKE                    │
│                                     │
│    ┌─────────────┐                  │
│    │  QR CODE    │  ← Scan untuk    │
│    │             │    request lagu  │
│    └─────────────┘                  │
│                                     │
│        Room: Room 1                 │
└─────────────────────────────────────┘
```

**2. Playing Mode** (Lagu diputar)
```
┌─────────────────────────────────────┐
│          NOW PLAYING                │
│                                     │
│         Judul Lagu                  │
│         Nama Artis                  │
│                                     │
│    ═══════════════╺╺╺╺╺╺╺╺╺╺      │
│                                     │
│    NEXT: Judul Lagu Berikutnya      │
└─────────────────────────────────────┘
```

**3. Hidden Controls** (Tap layar)
```
┌─────────────────────────────────────┐
│                                     │
│    [⏸] [⏭] [🎤 stereo] [🔊 ---]   │
│                                     │
└─────────────────────────────────────┘
```

---

### ⚙️ Role 4: Admin / Pengelola

**URL:** `https://your-domain:8443/admin`

**Default Login:** `admin` / `AdminK4r40k3!2024` *(ganti setelah install)*

#### Menu Admin:

**1. Dashboard 📊**
- Total lagu dalam database
- Total pemutaran
- Queue hari ini
- Koneksi aktif
- AI model status

**2. Manajemen Lagu 🎵**
```
┌────┬──────────┬──────────┬───────┬────────┬──────┐
│ ID │ Judul    │ Artis    │ Genre │ Play   │ Aksi │
├────┼──────────┼──────────┼───────┼────────┼──────┤
│ 1  │ Lagu A   │ Artis A  │ Pop   │ 150x   │ ✏️ 🗑️│
│ 2  │ Lagu B   │ Artis B  │ Rock  │ 89x    │ ✏️ 🗑️│
└────┴──────────┴──────────┴───────┴────────┴──────┘
```

**3. Scan Media 📂**
- Letakkan file video di `media/lagu/`
- Format nama: `Artis - Judul Lagu.mp4`
- Klik **🔍 Mulai Scan**
- Sistem otomatis menambah ke database

**4. Manajemen User 👥**
- Tambah/hapus operator
- Reset password
- Atur role (admin/operator)

#### Format File Media yang Didukung:
```
✅ Video: .mp4, .mkv, .avi, .webm, .mov
✅ Audio: .mp3, .wav, .flac (opsional)
❌ Gambar: Tidak didukung
```

---

## 📡 API Documentation

### Base URL
```
https://your-domain:8443/api
```

### Authentication

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}

Response:
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/auth/login` | User login |
| `GET` | `/api/songs` | List songs (with filters) |
| `GET` | `/api/songs/{id}` | Get song detail |
| `GET` | `/api/songs/genres` | List genres |
| `GET` | `/api/songs/popular` | Popular songs |
| `POST` | `/api/queue` | Add to queue |
| `GET` | `/api/queue/{room_id}` | Get queue |
| `DELETE` | `/api/queue/{queue_id}` | Remove from queue |
| `POST` | `/api/playlists` | Create playlist |
| `GET` | `/api/playlists` | List playlists |
| `POST` | `/api/admin/songs/scan` | Scan media folder |
| `GET` | `/api/admin/stats` | Get statistics |

### AI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/ai/mood/{room_id}` | Detect room mood |
| `POST` | `/api/ai/search` | Smart search |
| `GET` | `/api/ai/recommend/{song_id}` | Get recommendations |
| `POST` | `/api/ai/playlist/generate` | Generate playlist |
| `GET` | `/api/ai/playlist/quick` | Quick playlists |
| `GET` | `/api/ai/voice/stats` | Voice scoring stats |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `register` | Client → Server | Register client type |
| `join_room` | Client → Server | Join room channel |
| `play_song` | Client → Server | Play song command |
| `pause_song` | Client → Server | Pause command |
| `skip_song` | Client → Server | Skip command |
| `play_video` | Server → Client | Play video on player |
| `control_video` | Server → Client | Video control commands |
| `queue_updated` | Server → Client | Queue change notification |

Full API documentation available at: `https://your-domain:8443/docs`

---

## 🤖 AI/ML Features

### 1. Smart Song Recommendation

**Algorithm:** Content-Based Filtering with TF-IDF Vectorization

```python
# How it works:
1. Extract features from songs (genre, artist, language)
2. Build TF-IDF matrix
3. Calculate cosine similarity between songs
4. Return top-N similar songs
```

**Accuracy:** ~85% relevance based on genre/artist similarity

### 2. Mood Detection

**Algorithm:** Pattern Analysis from Play History

```
Mood Categories:
🔥 Energetic → Dangdut, Rock, K-Pop
😊 Happy     → Pop Indonesia, Barat
💕 Romantic  → Ballad, Slow Rock
😌 Relaxed   → Jazz, Akustik
😢 Sad       → Ballad, Religi
```

### 3. Smart Search (Fuzzy Matching)

**Algorithm:** Levenshtein Distance + Token-based Search

- **Toleransi Typo:** Mencari "peterpan" tetap menemukan "Peterpan"
- **Partial Match:** "dang" menemukan "Dangdut"
- **Auto-suggest:** Koreksi otomatis untuk typo

### 4. Auto Playlist Generator

```
Playlist Types:
├── By Genre: Pop Indonesia, Dangdut, K-Pop, etc.
├── By Mood: Party, Romantic, Nostalgia, Chill
├── By Decade: 90an, 2000an, 2010an
├── Top Hits: Most played songs
└── Smart Mix: AI-generated based on room mood
```

### 5. Voice Activity Detection

**Algorithm:** Energy-based + Zero Crossing Rate

- Deteksi apakah penyanyi sedang bernyanyi
- Estimasi pitch sederhana
- Scoring 0-100 dengan visualisasi bintang

---

## 🚢 Deployment

### Production Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate strong `JWT_SECRET`
- [ ] Configure SSL certificates
- [ ] Setup firewall (allow port 8443)
- [ ] Configure regular database backups
- [ ] Setup monitoring (logs rotation)
- [ ] Test dual-screen setup
- [ ] Test remote control functionality

### Docker Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f [service_name]

# Restart specific service
docker compose restart karaoke_backend

# Rebuild specific service
docker compose build --no-cache karaoke_backend
docker compose up -d karaoke_backend

# Access container shell
docker exec -it karaoke_backend bash
```

### Backup & Restore

```bash
# Backup database
docker exec karaoke_db pg_dump -U karaoke_admin karaoke_db > backup.sql

# Backup media files
tar -czf media_backup.tar.gz media/lagu/

# Restore database
docker exec -i karaoke_db psql -U karaoke_admin karaoke_db < backup.sql

# Restore media
tar -xzf media_backup.tar.gz
```

### Monitoring

```bash
# Check container status
docker compose ps

# Check resource usage
docker stats

# View application health
curl -k https://localhost:8443/api/health

# Run monitoring script
./monitor.sh
```

---

## 🔧 Troubleshooting

### Common Issues

<details>
<summary><b>1. Backend container keeps restarting</b></summary>

```bash
# Check logs for specific error
docker compose logs karaoke_backend --tail=50

# Common causes:
# - Database connection failed → Check DB credentials in .env
# - Missing Python dependencies → Rebuild with --no-cache
# - Port conflict → Check if port 5002 is in use

# Fix:
docker compose down
docker compose build --no-cache karaoke_backend
docker compose up -d
```
</details>

<details>
<summary><b>2. Cannot connect to database</b></summary>

```bash
# Check if database is healthy
docker compose ps karaoke_db

# Check database logs
docker compose logs karaoke_db

# Verify connection
docker exec karaoke_db psql -U karaoke_admin -d karaoke_db -c "SELECT 1"

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```
</details>

<details>
<summary><b>3. Nginx returns 502 Bad Gateway</b></summary>

```bash
# Check if backend is running
docker compose ps karaoke_backend

# Check Nginx error log
docker exec nextcloud_nginx cat /var/log/nginx/error.log

# Restart services
docker compose restart karaoke_backend karaoke_frontend
docker restart nextcloud_nginx
```
</details>

<details>
<summary><b>4. WebSocket connection failed</b></summary>

```bash
# Verify WebSocket is enabled in Nginx config
# Check for these lines in karaoke.conf:
#   proxy_http_version 1.1;
#   proxy_set_header Upgrade $http_upgrade;
#   proxy_set_header Connection "upgrade";

# Test WebSocket connection
wscat -c wss://your-domain:8443/socket.io/
```
</details>

<details>
<summary><b>5. Media files not found</b></summary>

```bash
# Check media directory permissions
ls -la media/lagu/

# Verify path in docker-compose.yml
# Should be: ./media/lagu:/media/lagu:ro

# Check if files are accessible from container
docker exec karaoke_backend ls /media/lagu/

# Fix permissions
sudo chmod -R 755 media/lagu/
```
</details>

### Log Locations

| Service | Log Location |
|---------|--------------|
| Backend | `docker compose logs karaoke_backend` |
| Frontend | `docker compose logs karaoke_frontend` |
| Database | `docker compose logs karaoke_db` |
| Nginx | `/var/log/nginx/error.log` in container |

---

## 👨‍💻 Development

### Local Setup (Without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 5002

# Frontend
cd frontend
npm install
npm run dev
```

### Project Structure

```
bpf-karaoke/
├── backend/
│   ├── main.py              # FastAPI main application
│   ├── ai_routes.py         # AI/ML API endpoints
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend container
│   └── services/            # AI/ML services
│       ├── song_recommender.py
│       ├── mood_detector.py
│       ├── smart_search.py
│       ├── auto_playlist.py
│       └── voice_analyzer.py
├── frontend/
│   ├── src/
│   │   ├── views/           # Page components
│   │   ├── components/      # Reusable components
│   │   │   └── ai/          # AI components
│   │   ├── stores/          # Pinia stores
│   │   └── router/          # Vue Router
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── database/
│   └── init/                # Database initialization
├── nginx/
│   └── karaoke.conf         # Nginx configuration
├── media/
│   └── lagu/                # Karaoke video files
├── docker-compose.yml       # Docker services
├── .env                     # Environment variables
├── deploy.sh                # Deployment script
└── monitor.sh               # Monitoring script
```

### Code Style

- **Python:** Follow PEP 8
- **JavaScript:** ESLint with Vue 3 recommended rules
- **CSS:** Tailwind CSS utility classes

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test

# API tests
curl -k https://localhost:8443/api/health
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Contribution Guidelines

- Write clean, documented code
- Follow existing code style
- Add tests for new features
- Update documentation
- Test thoroughly before PR

### Feature Requests

Open an issue with:
- Feature description
- Use case
- Expected behavior
- Screenshots/mockups (if applicable)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - The amazing Python web framework
- **Vue.js** - Progressive JavaScript framework
- **Socket.IO** - Real-time bidirectional event-based communication
- **PostgreSQL** - The world's most advanced open source database
- **Docker** - Containerization platform
- **scikit-learn** - Machine learning in Python
- **Let's Encrypt** - Free SSL/TLS certificates

---

## 📞 Support

### Need Help?

- **📖 Documentation:** [Wiki](https://github.com/yourusername/bpf-karaoke/wiki)
- **🐛 Bug Reports:** [Issues](https://github.com/yourusername/bpf-karaoke/issues)
- **💬 Discussion:** [Discussions](https://github.com/yourusername/bpf-karaoke/discussions)
- **📧 Email:** support@bpfkaraoke.com

### Community

- **Telegram:** [@bpfkaraoke](https://t.me/bpfkaraoke)
- **WhatsApp:** [BPF Karaoke Group](https://chat.whatsapp.com/xxx)

---

## 🗺️ Roadmap

### v2.1 (Q3 2026)
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Cloud backup integration

### v2.2 (Q4 2026)
- [ ] Deep learning voice scoring
- [ ] Automatic pitch detection
- [ ] Karaoke competition mode
- [ ] Payment integration

### v3.0 (2027)
- [ ] Cloud-based deployment
- [ ] Multi-tenant support
- [ ] AI-powered song suggestions
- [ ] Real-time collaboration

---

<div align="center">

**Made with ❤️ by BPF Karaoke Team**

[⬆ Back to Top](#-bpf-karaoke-system)

</div>
