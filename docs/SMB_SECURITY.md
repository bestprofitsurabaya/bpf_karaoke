# 🔐 Keamanan Share Karaoke Bank (SMB1)

Sinkronisasi lagu dari mesin **kiosk karaoke (192.168.100.140 — Debian Linux,
pengganti Windows XP)** memakai protokol **SMB1** dan default-nya **guest**
(tanpa kredensial) agar bisa langsung berjalan. Bagian 1–3 di bawah tetap
berlaku sebagai panduan bila ingin memperketat dengan akun khusus; sekarang
XP sudah tidak ada, mesin kiosk menjalankan share Samba dengan cara serupa.

> ⚠️ SMB1 secara desain tidak aman untuk internet — jangan pernah
> membuka port 445/139 ke luar LAN. Sistem ini hanya berjalan di jaringan
> internal Anda.

## 1. Buat akun Windows khusus (disarankan untuk produksi)

Sebagai ganti akses guest, buat akun terbatas di komputer XP:

1. Di mesin sumber (dulu Windows XP, kini kiosk Linux / Samba): buat akun terbatas
   - Nama: `karaoke-sync`
   - Tipe: **bukan Administrator** — hanya hak baca share
   - Beri password kuat (contoh: `K4r4okeSync!2024`)
2. Klik kanan folder share (**karaoke bank 1** dan **karaoke bank 2**) →
   **Sharing and Security** → beri hak **Read** (bukan Full Control) untuk
   akun `karaoke-sync` (dan/atau hapus akses guest/Everyone).
3. Isi kredensial di file `.env` server:

   ```env
   SMB_USER=karaoke-sync
   SMB_PASSWORD=K4r4okeSync!2024
   ```

4. Terapkan dengan menyalakan ulang service sync:

   ```bash
   docker compose up -d karaoke_sync
   docker compose logs karaoke_sync --tail 20   # verifikasi koneksi
   ```

> Kredensial **tidak pernah keluar dari LAN** — hanya dipakai oleh container
> `karaoke_sync` untuk menyalin file.

## 2. IP otomatis (auto-detect) — IP mesin sumber berubah-ubah

Bila mesin sumber memakai DHCP, IP-nya bisa berubah sewaktu-waktu. Sync
mendukung **auto-detect**: jika `SMB_HOST` yang dikonfigurasi tidak merespons,
sync otomatis mencari mesin sumber via NetBIOS (scan subnet `/24` + reverse
query nama `SMB_REMOTE_NAME`, default `KARAOKE`) lalu lanjut sinkronisasi
tanpa perlu mengubah `.env`.

```env
SMB_AUTO_DETECT=1   # aktif (default). 0 untuk menonaktifkan
```

> Catatan: pencarian otomatis hanya berlaku di subnet yang sama dengan
> `SMB_HOST` (scan `/24`). Jika mesin sumber pindah ke subnet berbeda,
> perbarui `SMB_HOST` di `.env`.

## 3. Notifikasi saat sync selesai / error (webhook opsional)

Bila ingin diberi tahu otomatis saat **semua lagu tersalin** atau ada **error**,
isi `SMB_WEBHOOK_URL` di `.env` dengan webhook yang menerima POST JSON:

- **Telegram Bot API**: `https://api.telegram.org/bot<TOKEN>/sendMessage`
  (perlu tambah `chat_id` pada payload — lihat kode `notify()` di
  `backend/services/smb_sync.py` bila ingin menyesuaikan)
- **Discord**: `https://discord.com/api/webhooks/...`
- **Slack**: `https://hooks.slack.com/services/...`

Payload yang dikirim berisi `text`, `content`, `status`, `done`,
`copied_files`, `total_files`, `errors`, `disk_free_gb`.

```env
SMB_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/yyyy
```

## 4. Cek status kapan saja

```bash
./check_sync.sh
```

Menampilkan: fase sync, jumlah tersalin/terlihat, error, ruang disk,
jumlah MP4 ter-transcode, lagu di database, dan antrian transcode.

## 5. Kontrol manual (start / pause)

Proses pemindahan file dari XP bisa **dijeda & dilanjutkan** kapan saja
tanpa kehilangan progres (setiap file disalin ke `.part` lalu di-rename
atomik; progres disimpan ke `sync_state.json` tiap ±5 detik):

```bash
./sync_control.sh status   # status proses + progress
./sync_control.sh start    # MULAI / lanjutkan (resume incremental)
./sync_control.sh pause    # JEDA (SIGTERM aman, lanjut dari titik henti)
```

> Saat di-*pause*, proses berhenti bersih — file `.part` yang tertinggal
> ditimpa saat lanjut, tidak ada file korup. `docker compose stop` dipakai
> (bukan `pause` SIGSTOP) agar koneksi SMB ditutup rapi.

## 6. Operasional

- **Mesin sumber boleh mati** — sync berhenti, lalu **lanjut otomatis**
  (incremental) saat mesin menyala kembali. Jangan hapus file di
  `media/lagu` selama proses.
- **Sumber .mpg/.mpeg DIHAPUS otomatis setelah transcode sukses** — MP4 hasil
  transcode diverifikasi dulu (ffprobe) sebelum sumbernya dihapus. Sync tidak
  akan menyalin ulang file yang sudah punya MP4 (agar tidak loop salin-hapus).
  Nonaktifkan dengan `DELETE_SOURCE_AFTER_TRANSCODE=0` di `.env`; daftar
  format yang dihapus bisa diubah lewat `DELETE_SOURCE_EXTS`.
- **Transcode tahan gagal** — file `.part` basi (>1 jam) dibersihkan otomatis
  dan task diantre ulang oleh scan tiap 10 menit; antrian dideduplikasi via
  Redis agar tidak membengkak saat XP baru menyala.
- **Kecepatan**: paralel 4 koneksi SMB (env `SMB_PARALLEL`). Batas mesin
  sumber = 10 sesi SMB serentak; jangan set lebih dari 6.
- **HDD bank di server**: bila bank karaoke dipasang langsung di server,
  gunakan `./setup_karaoke_bank.sh` untuk mount NTFS (default read-only,
  aman untuk data 2 TB) ke `/mnt/karaoke_bank1|2` — lihat README.
- **Ruang disk**: total bank ±600–800 GB, tersimpan di `/srv` (1,7 TB).
  Dashboard admin menampilkan peringatan bila disk menipis.
- **Penanda selesai**: `SYNC_COMPLETE.txt` di `/srv/karaoke_media/` + badge
  "✅ SEMUA TERSALIN" di dashboard admin.
