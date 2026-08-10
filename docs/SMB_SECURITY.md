# 🔐 Keamanan Share Karaoke Bank (SMB1 / Windows XP)

Sinkronisasi dari komputer **Windows XP (192.168.1.108)** memakai protokol
**SMB1** (satu-satunya yang didukung XP) dan default-nya **guest** (tanpa
kredensial) agar bisa langsung berjalan.

> ⚠️ SMB1 secara desain tidak aman untuk internet — jangan pernah
> membuka port 445/139 ke luar LAN. Sistem ini hanya berjalan di jaringan
> internal Anda.

## 1. Buat akun Windows khusus (disarankan untuk produksi)

Sebagai ganti akses guest, buat akun terbatas di komputer XP:

1. Di Windows XP: **Control Panel → User Accounts → Buat akun baru**
   - Nama: `karaoke-sync`
   - Tipe: **Terbatas (Limited)** — bukan Administrator
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

## 2. Notifikasi saat sync selesai / error (webhook opsional)

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

## 3. Cek status kapan saja

```bash
./check_sync.sh
```

Menampilkan: fase sync, jumlah tersalin/terlihat, error, ruang disk,
jumlah MP4 ter-transcode, lagu di database, dan antrian transcode.

## 4. Operasional

- **XP boleh mati** — sync berhenti, lalu **lanjut otomatis** (incremental)
  saat XP menyala kembali. Jangan hapus file di `media/lagu` selama proses.
- **Sumber .mpg/.mpeg DIHAPUS otomatis setelah transcode sukses** — MP4 hasil
  transcode diverifikasi dulu (ffprobe) sebelum sumbernya dihapus. Sync tidak
  akan menyalin ulang file yang sudah punya MP4 (agar tidak loop salin-hapus).
  Nonaktifkan dengan `DELETE_SOURCE_AFTER_TRANSCODE=0` di `.env`; daftar
  format yang dihapus bisa diubah lewat `DELETE_SOURCE_EXTS`.
- **Transcode tahan gagal** — file `.part` basi (>1 jam) dibersihkan otomatis
  dan task diantre ulang oleh scan tiap 10 menit; antrian dideduplikasi via
  Redis agar tidak membengkak saat XP baru menyala.
- **Kecepatan**: paralel 4 koneksi SMB (env `SMB_PARALLEL`). Batas XP = 10
  sesi SMB serentak; jangan set lebih dari 6.
- **Ruang disk**: total bank ±600–800 GB, tersimpan di `/srv` (1,7 TB).
  Dashboard admin menampilkan peringatan bila disk menipis.
- **Penanda selesai**: `SYNC_COMPLETE.txt` di `/srv/karaoke_media/` + badge
  "✅ SEMUA TERSALIN" di dashboard admin.
