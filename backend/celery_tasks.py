"""
Celery Background Tasks - AI & Heavy Processing
PT BESTPROFIT FUTURES SURABAYA
"""

import os, sys, subprocess, json, time, shutil, traceback
import asyncio
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Bootstrap: pastikan /app selalu di sys.path (worker Celery prefork bisa
# kehilangan entri CWD sehingga import 'database' gagal saat runtime)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery_app import app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Import level modul (di-load saat worker start, BUKAN saat task jalan)
from database import async_session
from models import Song
from sqlalchemy import select

# ---------------------------------------------------------------------------
# Helper: satu event loop persisten per proses untuk operasi DB async.
# Penting: asyncio.run() membuat loop BARU setiap dipanggil, sedangkan pool
# asyncpg engine terikat ke loop pertama -> task kedua di proses sama gagal
# dengan 'attached to a different loop'. Loop thread-persisten menyelesaikannya.
# ---------------------------------------------------------------------------
_db_loop = None
_db_loop_lock = threading.Lock()


def _get_db_loop():
    global _db_loop
    if _db_loop is None or not _db_loop.is_running():
        with _db_loop_lock:
            if _db_loop is None or not _db_loop.is_running():
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, daemon=True).start()
                _db_loop = loop
    return _db_loop


def run_async(coro):
    """Jalankan coroutine pada loop persisten proses ini."""
    loop = _get_db_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result(timeout=300)


# ---------------------------------------------------------------------------
# Dedupe antrian transcode (Redis set).
# Masalah nyata: scan_for_new_media jalan tiap 10 menit; file yang sudah
# diantre tapi belum diproses worker (antrian panjang) TIDAK punya penanda,
# sehingga diantre ulang berkali-kali -> antrian membengkak (ribuan duplikat).
# Solusi: simpan path di SET Redis saat diantre, hapus saat task selesai.
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv('REDIS_URL', 'redis://karaoke_redis:6379/0')
PENDING_KEY = 'transcode:pending'
_redis_client = None
_redis_lock = threading.Lock()


def _get_redis():
    global _redis_client
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                import redis
                c = redis.from_url(REDIS_URL, socket_connect_timeout=3,
                                   socket_timeout=3)
                c.ping()
                _redis_client = c
    return _redis_client


def _pending_contains(path: str) -> bool:
    try:
        return bool(_get_redis().sismember(PENDING_KEY, path))
    except Exception:
        return False  # redis bermasalah: jangan blokir antrean


def _pending_add(path: str) -> bool:
    """True jika path baru & berhasil ditandai (berarti perlu diantre)."""
    try:
        return bool(_get_redis().sadd(PENDING_KEY, path))
    except Exception:
        return True  # redis bermasalah: tetap antre (perilaku scan lama)


def _pending_remove(path: str) -> None:
    try:
        _get_redis().srem(PENDING_KEY, path)
    except Exception:
        pass

MEDIA_PATH = Path(os.getenv('MEDIA_PATH', '/media/lagu'))
TRANSCODED_PATH = Path('/media/transcoded')
# Master yang perlu transcode -> MP4 (collision-safe: struktur folder dipertahankan)
MASTER_EXTENSIONS = {'.mpg', '.mpeg', '.avi', '.mkv', '.wmv', '.flv', '.vob', '.m2v', '.mpv', '.3gp', '.dat'}
# Format yang langsung bisa diputar browser (tanpa transcode)
PLAYABLE_EXTENSIONS = {'.mp4', '.mov', '.webm'}

# ---------------------------------------------------------------------------
# Hapus sumber setelah transcode SUKSES (default: .mpg/.mpeg).
# - Hanya file yang output MP4-nya sudah TERVERIFIKASI yang dihapus.
# - Atur DELETE_SOURCE_AFTER_TRANSCODE=0 untuk menonaktifkan.
# ---------------------------------------------------------------------------
DELETE_SOURCE_AFTER_TRANSCODE = os.getenv(
    'DELETE_SOURCE_AFTER_TRANSCODE', '1').lower() in ('1', 'true', 'yes', 'on')
# Semua format master yang di-transcode ke MP4 dihapus setelah sukses
# (default: seluruh MASTER_EXTENSIONS). Persempit via env DELETE_SOURCE_EXTS.
DELETE_SOURCE_EXTS = {e.strip().lower() for e in
                      os.getenv('DELETE_SOURCE_EXTS',
                                '.mpg,.mpeg,.avi,.mkv,.wmv,.flv,.vob,.m2v,.mpv,.3gp,.dat')
                      .split(',') if e.strip()}
# Transcode tidak dimulai bila ruang kosong < nilai ini (atau < 2x ukuran sumber)
MIN_FREE_GB_FOR_TRANSCODE = float(os.getenv('MIN_FREE_GB_FOR_TRANSCODE', '5'))
# Sub-folder TRANSCODED_PATH yang BUKAN hasil transcode master (vocal_removed,
# pitch, dll) — jangan didaftarkan sebagai lagu saat heal MP4 yatim.
NON_SONG_DIRS = {'vocal_removed', 'vocals_removed', 'pitch', 'demucs'}


def transcoded_path_for(input_file: Path) -> Path:
    """Output transcode: /media/transcoded/<rel-path-dari-MEDIA_PATH>.mp4
    Mempertahankan struktur folder agar nama yang sama di folder berbeda
    tidak saling menimpa (masalah nyata di bank ribuan lagu)."""
    try:
        rel = input_file.resolve().relative_to(MEDIA_PATH.resolve())
    except ValueError:
        rel = Path(input_file.name)
    return TRANSCODED_PATH / rel.with_suffix('.mp4')


def parse_title_artist(stem: str):
    """Nama file 'Artis - Judul' -> (artis, judul)."""
    if ' - ' in stem:
        p = stem.split(' - ', 1)
        return p[0].strip(), p[1].strip()
    return None, stem.strip()


# ---------------------------------------------------------------------------
# Katalog karaoke bank (dari backup SQL2000 BackupFebruari2025.BAK)
# Dipakai untuk memperkaya metadata lagu yang nama filenya cuma kode angka
# (mis. '109589.mp4' -> artist 'Timi Yuro', title 'Im Sorry').
# ---------------------------------------------------------------------------
CATALOG_PATH = Path(os.getenv('CATALOG_PATH', '/srv_media/catalog.json'))
_catalog_lock = threading.Lock()
_catalog_by_kode = {}   # (bank:int, kode:str) -> {artist, title}
_catalog_by_rel = {}    # (bank:int, rel:str lower) -> {artist, title}


def _load_catalog():
    """Load katalog ke memory (lazy, sekali per proses)."""
    global _catalog_by_kode, _catalog_by_rel
    if _catalog_by_kode or _catalog_by_rel:
        return True
    if not CATALOG_PATH.exists():
        return False
    with _catalog_lock:
        if _catalog_by_kode or _catalog_by_rel:
            return True
        try:
            recs = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
            kode, rel = {}, {}
            BS = chr(92)  # backslash, hindari escaping ambigu
            for r in recs:
                path = (r.get('path') or '').replace(BS, '/')
                m = re.match(r'/BANK (\d+)/', path, re.I)
                if not m:
                    continue
                bank = int(m.group(1))
                parts = path.split('/')
                rest = '/'.join(parts[2:]) if len(parts) > 2 else ''
                mm = re.match(r'(\d+)\.', rest)
                if mm:
                    kode[(bank, mm.group(1))] = r
                else:
                    # relative path tanpa ekstensi, lowercase
                    base = re.sub(r'\.\w+$', '', rest).lower()
                    if base:
                        rel[(bank, base)] = r
            _catalog_by_kode = kode
            _catalog_by_rel = rel
            logger.info(f"Katalog loaded: {len(kode)} kode + {len(rel)} rel")
            return True
        except Exception:
            logger.warning(f"Katalog gagal dimuat: {traceback.format_exc()}")
            return False


def _catalog_lookup(file_path: str):
    """Cari (artist, title) dari katalog berdasar file_path.
    Greedy '.*' memastikan mengambil 'Bank N/' TERAKHIR (bukan prefix
    'karaoke bank N/' di path). Mengembalikan dict katalog atau None."""
    if not _load_catalog():
        return None
    fp = file_path.replace('\\', '/')
    # pola 1: /Bank N/<kode>.<ext>
    m = re.search(r'.*Bank (\d+)/(\d+)\.', fp, re.I)
    if m:
        rec = _catalog_by_kode.get((int(m.group(1)), m.group(2)))
        if rec:
            return rec
    # pola 2: /Bank N/<relative path tanpa kode>
    m = re.search(r'.*Bank (\d+)/(.+)$', fp, re.I)
    if m:
        rel = re.sub(r'\.\w+$', '', m.group(2)).lower()
        rec = _catalog_by_rel.get((int(m.group(1)), rel))
        if rec:
            return rec
    return None


async def _upsert_song(file_path: str, title: str, artist, file_format: str = 'mp4'):
    """Daftarkan lagu ke DB (idempotent berdasarkan file_path)."""
    # Perkaya metadata dari katalog bank bila tersedia
    cat = _catalog_lookup(file_path)
    cat_title = (cat.get('title') or '').strip() if cat else ''
    cat_artist = (cat.get('artist') or '').strip() if cat else ''
    if cat_title and (not title or title.strip().isdigit()):
        title = cat_title
    if cat_artist:
        artist = cat_artist

    async with async_session() as session:
        ex = (await session.execute(
            select(Song).where(Song.file_path == file_path))).scalar_one_or_none()
        if ex:
            # Update metadata yang masih kosong/angka bila katalog menyediakan
            changed = False
            if not ex.is_active:
                ex.is_active = True
                changed = True
            if cat_title and (not ex.title or str(ex.title).strip().isdigit()):
                ex.title = cat_title
                changed = True
            if cat_artist and not ex.artist:
                ex.artist = cat_artist
                changed = True
            if changed:
                await session.commit()
            return ex.id

        genre = 'Unknown'
        try:
            from services.genre_detector import genre_detector
            pred = genre_detector.predict_genre(artist=artist, title=title)
            if pred['confidence'] > 0.8:
                genre = pred['genre']
        except Exception:
            pass
        song = Song(title=title, artist=artist, genre=genre,
                    file_path=file_path, file_format=file_format, is_active=True)
        session.add(song)
        await session.commit()
        await session.refresh(song)
        return song.id

# ============================================
# TASK 1: SCAN MEDIA & AUTO-TRANSCODE
# ============================================

@app.task(name='celery_tasks.scan_for_new_media')
def scan_for_new_media():
    """Scan folder media: daftarkan file playable & antrekan transcode master baru"""
    logger.info(f"Scanning {MEDIA_PATH} ...")

    if not MEDIA_PATH.exists():
        return {"error": "Media path not found"}

    queued = 0
    registered = 0
    skipped = 0

    # Path MP4 terdaftar di DB (satu query) — dipakai agar sumber hanya dihapus
    # bila MP4-nya benar-benar terdaftar (fail-closed: jika query gagal, set
    # kosong -> TIDAK ada sumber yang dihapus di scan ini).
    registered_paths = set()
    if DELETE_SOURCE_AFTER_TRANSCODE:
        try:
            async def fetch_registered():
                async with async_session() as session:
                    rows = await session.execute(select(Song.file_path))
                    return {str(p) for p in rows.scalars() if p}
            registered_paths = run_async(fetch_registered())
        except Exception:
            logger.warning("Gagal memuat daftar lagu terdaftar; "
                           "penghapusan sumber dinonaktifkan scan ini")

    for file_path in MEDIA_PATH.rglob('*'):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()

        if ext in PLAYABLE_EXTENSIONS:
            # Langsung bisa diputar -> daftarkan ke DB (idempotent)
            art, tit = parse_title_artist(file_path.stem)
            try:
                run_async(_upsert_song(str(file_path), tit, art, file_format=ext.lstrip('.')))
                registered += 1
            except Exception:
                logger.error(f"Register {file_path.name} gagal:\n{traceback.format_exc()}")
            continue

        if ext in MASTER_EXTENSIONS:
            try:
                src_ok = file_path.stat().st_size > 0
            except OSError:
                src_ok = False
            if not src_ok:
                continue  # sumber sedang ditulis sync / kosong

            transcoded = transcoded_path_for(file_path)
            # Sumber yang sudah punya MP4 TERDAFTAR di DB -> hapus (sesuai
            # DELETE_SOURCE_*) & tidak perlu diantre. Gate terdaftar penting:
            # jangan hapus sumber yang MP4-nya yatim (registrasi DB gagal),
            # karena scan tidak menjangkau /media/transcoded.
            if (DELETE_SOURCE_AFTER_TRANSCODE and ext in DELETE_SOURCE_EXTS
                    and transcoded.exists() and transcoded.stat().st_size > 0
                    and str(transcoded) in registered_paths):
                try:
                    file_path.unlink()
                    logger.info(f"🧹 Sumber dihapus (sudah punya MP4 terdaftar): "
                                f"{file_path.name}")
                except OSError as e:
                    logger.warning(f"Gagal hapus {file_path.name}: {e}")
                continue

            if transcoded.exists() and transcoded.stat().st_size > 0:
                skipped += 1
            elif transcoded.with_name(transcoded.name + ".part").exists():
                # Sedang di-transcode oleh task lain -> jangan antre ulang
                skipped += 1
            elif _pending_contains(str(file_path)):
                # Sudah diantre & belum selesai -> jangan antre ulang (dedupe)
                skipped += 1
            elif _pending_add(str(file_path)):
                queued += 1
                transcode_video.delay(str(file_path))
                logger.info(f"Queued: {file_path.name}")

    return {"scanned": True, "queued": queued, "registered": registered,
            "skipped_transcoded": skipped,
            "timestamp": datetime.now().isoformat()}

@app.task(name='celery_tasks.transcode_video', bind=True)
def transcode_video(self, input_path: str):
    """Transcode video master ke H.264 MP4 + daftarkan lagu ke DB.

    Antisipasi kegagalan:
    - Klaim .part ATOMIK (O_EXCL): dua task duplikat tidak memproses file sama.
    - .part basi (>1 jam, sisa task yang mati) langsung dibersihkan & diklaim
      ulang, sehingga scan berikutnya bisa memproses lagi (tanpa menunggu
      cleanup harian jam 03:00).
    - Cek ruang disk sebelum mulai.
    - ffmpeg memakai flag toleran untuk MPEG/VOB lama (genpts, ignore_err).
    - Output DIVERIFIKASI (ffprobe: ada video stream & bukan 0 byte) sebelum
      dianggap sukses; sumber .mpg/.mpeg hanya dihapus bila verifikasi LULUS.
    - Semua kegagalan menghapus .part agar task bisa dicoba ulang oleh scan
      berikutnya (retry otomatis tiap 10 menit).
    """
    input_file = Path(input_path)
    try:
        src_size = input_file.stat().st_size
    except OSError:
        return {"error": "File not found", "status": "failed"}
    if src_size == 0:
        return {"error": "Source file empty", "status": "failed"}

    output_file = transcoded_path_for(input_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    part_file = output_file.with_name(output_file.name + ".part")

    if output_file.exists() and output_file.stat().st_size > 0:
        logger.info(f"Already transcoded: {output_file.name}")
        return {"status": "skipped", "output": str(output_file)}

    # Klaim atomik: hanya SATU task yang boleh memproses file ini.
    try:
        fd = os.open(part_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        try:
            if time.time() - part_file.stat().st_mtime > 3600:
                part_file.unlink()  # basi (task sebelumnya mati) -> klaim ulang
                try:
                    fd = os.open(part_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                except FileExistsError:
                    return {"status": "in_progress", "output": str(output_file)}
            else:
                logger.info(f"Sedang diproses task lain: {output_file.name}")
                return {"status": "in_progress", "output": str(output_file)}
        except OSError:
            return {"status": "in_progress", "output": str(output_file)}

    # Cek ruang disk sebelum mulai (hindari gagal di tengah jalan)
    try:
        free = shutil.disk_usage(output_file.parent).free
        need = max(src_size * 2, MIN_FREE_GB_FOR_TRANSCODE * 1024 ** 3)
        if free < need:
            part_file.unlink(missing_ok=True)
            _pending_remove(input_path)  # biar scan mencoba lagi nanti
            return {"error": f"Disk space insufficient "
                             f"({free/1024**3:.1f} GB free)", "status": "failed"}
    except OSError:
        pass

    self.update_state(state='PROGRESS', meta={'stage': 'transcoding', 'file': input_file.name})

    try:
        cmd = [
            'ffmpeg', '-y',
            # Toleran terhadap MPEG/VOB lama dengan timestamp rusak
            '-fflags', '+genpts',
            '-err_detect', 'ignore_err',
            '-avoid_negative_ts', 'make_zero',
            '-i', str(input_file),
            '-map', '0:v:0', '-map', '0:a?',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2',
            '-movflags', '+faststart',
            '-f', 'mp4',              # wajib: ekstensi .part tidak dikenali ffmpeg
            str(part_file)
        ]
        subprocess.run(cmd, check=True, timeout=900, capture_output=True)

        # Verifikasi output: bukan 0 byte & punya video stream
        if part_file.stat().st_size == 0:
            raise RuntimeError("output file is empty")
        probe = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
             '-show_entries', 'stream=codec_name', '-of', 'csv=p=0',
             str(part_file)],
            capture_output=True, text=True, timeout=30)
        if probe.returncode != 0 or not probe.stdout.strip():
            raise RuntimeError("output has no video stream")
        os.replace(part_file, output_file)

        # Daftarkan lagu ke database (file_path -> MP4 hasil transcode)
        art, tit = parse_title_artist(input_file.stem)
        sid = None
        try:
            sid = run_async(_upsert_song(str(output_file), tit, art, file_format='mp4'))
        except Exception:
            logger.error(f"DB register gagal utk {output_file.name}:\n{traceback.format_exc()}")

        # Hapus sumber bila sukses & formatnya termasuk daftar hapus
        # (default .mpg/.mpeg). Hanya bila: output LULUS verifikasi DAN lagu
        # BERHASIL terdaftar di DB (sid) — jika DB sempat gagal, MP4 jadi yatim
        # (scan tidak menjangkau /media/transcoded) sehingga sumber dipertahankan.
        deleted_source = False
        if (DELETE_SOURCE_AFTER_TRANSCODE and sid is not None
                and input_file.suffix.lower() in DELETE_SOURCE_EXTS):
            try:
                input_file.unlink(missing_ok=True)
                deleted_source = True
            except OSError as e:
                logger.warning(f"Gagal hapus master {input_file.name}: {e}")

        logger.info(f"✅ Transcoded: {output_file.name} (song_id={sid}, "
                    f"delete_source={deleted_source})")
        return {"status": "completed", "output": str(output_file),
                "song_id": sid, "deleted_source": deleted_source}
    except subprocess.TimeoutExpired:
        logger.error(f"Transcode timeout (900s): {input_file.name}")
        part_file.unlink(missing_ok=True)  # biar bisa dicoba ulang
        return {"error": "timeout", "status": "failed"}
    except Exception as e:
        logger.error(f"Transcode failed: {e}")
        part_file.unlink(missing_ok=True)  # biar bisa dicoba ulang
        return {"error": str(e), "status": "failed"}
    finally:
        _pending_remove(input_path)

# ============================================
# TASK 2: AI VOCAL REMOVER
# ============================================

@app.task(name='celery_tasks.vocal_remove', bind=True)
def vocal_remove(self, song_id: int, file_path: str, method: str = "ffmpeg"):
    """
    AI Vocal Removal - Dijalankan sebagai background task Celery.
    Methods: ffmpeg (cepat), demucs (akurat, perlu GPU/CPU kuat), spleeter (balanced)
    """
    self.update_state(state='PROGRESS', meta={'stage': 'starting', 'song_id': song_id})
    
    input_file = Path(file_path)
    if not input_file.exists():
        return {"error": "File not found", "status": "failed"}
    
    output_dir = TRANSCODED_PATH / "vocals_removed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_file.stem}_instrumental.mp4"
    
    if output_file.exists():
        return {"status": "completed", "output": str(output_file), "cached": True}
    
    try:
        if method == "ffmpeg":
            # Phase cancellation + EQ filtering (instant)
            cmd = [
                'ffmpeg', '-y', '-i', str(input_file),
                '-af', 'pan=stereo|c0=c0-c1|c1=c1-c0,highpass=f=200,lowpass=f=8000',
                '-c:v', 'copy', '-q:a', '2', str(output_file)
            ]
            subprocess.run(cmd, check=True, timeout=300, capture_output=True)
            
        elif method == "spleeter":
            # AI separation (akurat, ~30-60 detik per lagu)
            cmd = [
                'spleeter', 'separate',
                '-p', 'spleeter:2stems',
                '-o', str(output_dir),
                str(input_file)
            ]
            subprocess.run(cmd, check=True, timeout=600, capture_output=True)
            # Rename output
            spleeter_out = output_dir / input_file.stem / "accompaniment.wav"
            if spleeter_out.exists():
                shutil.move(str(spleeter_out), str(output_file))
        
        elif method == "demucs":
            # Facebook Demucs (paling akurat)
            cmd = ['demucs', '--two-stems=vocals', '-o', str(output_dir), str(input_file)]
            subprocess.run(cmd, check=True, timeout=900, capture_output=True)
        
        logger.info(f"✅ Vocal removed: {output_file.name} (method: {method})")
        
        # Update database
        from sqlalchemy import update

        async def update_db():
            async with async_session() as session:
                await session.execute(
                    update(Song).where(Song.id == song_id).values(
                        has_vocal_track=True, vocal_channel='instrumental'
                    )
                )
                await session.commit()

        run_async(update_db())
        
        return {"status": "completed", "output": str(output_file), "method": method}
        
    except FileNotFoundError as e:
        return {"error": f"Tool not installed: {e}", "status": "failed"}
    except Exception as e:
        logger.error(f"Vocal remove failed: {e}")
        return {"error": str(e), "status": "failed"}

# ============================================
# TASK 3: BATCH AUTO-GENRE DETECTION
# ============================================

@app.task(name='celery_tasks.batch_auto_genre', bind=True)
def batch_auto_genre(self, limit: int = 100):
    """
    Batch genre detection menggunakan AI - Background task.
    Memproses lagu tanpa genre dalam jumlah besar.
    """
    from sqlalchemy import update, or_

    self.update_state(state='PROGRESS', meta={'stage': 'loading_songs'})
    
    async def process():
        from services.genre_detector import genre_detector
        
        async with async_session() as session:
            result = await session.execute(
                select(Song).where(
                    Song.is_active == True,
                    or_(Song.genre.is_(None), Song.genre == '', Song.genre == 'Unknown')
                ).limit(limit)
            )
            songs = result.scalars().all()
            
            processed = 0
            auto_assigned = 0
            
            for song in songs:
                prediction = genre_detector.predict_genre(
                    artist=song.artist or '',
                    title=song.title
                )
                
                if prediction['confidence'] > 0.8:
                    song.genre = prediction['genre']
                    auto_assigned += 1
                elif prediction['confidence'] > 0.4:
                    song.genre = 'Unknown'
                
                processed += 1
                
                # Update progress setiap 10 lagu
                if processed % 10 == 0:
                    self.update_state(state='PROGRESS', meta={
                        'stage': 'processing',
                        'processed': processed,
                        'total': len(songs),
                        'auto_assigned': auto_assigned
                    })
            
            await session.commit()
            
            return {
                'status': 'completed',
                'processed': processed,
                'auto_assigned': auto_assigned,
                'total': len(songs)
            }

    return run_async(process())

# ============================================
# TASK 4: CLEANUP
# ============================================

def _sweep_stale_parts() -> dict:
    """Sweep ringan: hapus file 0-byte & .part basi (>1 jam) + self-heal
    penanda antrian Redis (task pemilik mati keras: OOM/kill/restart).

    Ringan (tanpa query DB) sehingga bisa dijadwalkan sering (tiap 15 menit) —
    tanpa ini, .part yatim dari restart worker memblokir lagu sampai cleanup
    harian jam 03:00 (bisa 24 jam).
    """
    if not TRANSCODED_PATH.exists():
        return {"cleaned": 0}

    cleaned = 0
    now = time.time()
    stale_parts = set()  # path .part basi yang DIHAPUS loop ini (lihat self-heal)
    for f in TRANSCODED_PATH.rglob('*'):
        if not f.is_file():
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_size == 0:
            f.unlink(missing_ok=True)
            cleaned += 1
        elif f.suffix == '.part' and now - st.st_mtime > 3600:
            f.unlink(missing_ok=True)
            stale_parts.add(f.resolve())
            cleaned += 1

    if cleaned:
        logger.info(f"🧹 Sweep: {cleaned} failed/stale transcode dibersihkan")

    # Self-heal penanda antrian Redis: hapus entri yang sudah selesai (MP4
    # sudah ada) atau .part-nya BASI (task pemilik mati keras: OOM/kill) agar
    # scan bisa mengantre ulang (cegah deadlock permanen).
    # PENTING: .part basi sudah dihapus oleh loop di atas, jadi pengecekan
    # memakai stale_parts (direkam SAAT penghapusan), bukan part.exists() —
    # jika tidak, penanda tidak akan pernah dihapus (deadlock tetap terjadi).
    # Kasus TANPA .part sama sekali (task antri, belum mulai) DIPERTAHANKAN
    # agar dedupe tetap bekerja untuk backlog besar.
    try:
        r = _get_redis()
        for p in (r.smembers(PENDING_KEY) or []):
            p = p.decode() if isinstance(p, bytes) else p
            src = Path(p)
            if not src.exists():
                r.srem(PENDING_KEY, p)
                continue
            out = transcoded_path_for(src)
            if out.exists() and out.stat().st_size > 0:
                r.srem(PENDING_KEY, p)
                continue
            part = out.with_name(out.name + ".part")
            try:
                part_stale = part.resolve() in stale_parts
                if not part_stale and part.exists():
                    part_stale = now - part.stat().st_mtime > 3600
            except OSError:
                part_stale = False
            if part_stale:
                r.srem(PENDING_KEY, p)
    except Exception:
        pass

    return {"cleaned": cleaned}


@app.task(name='celery_tasks.sweep_stale_parts')
def sweep_stale_parts():
    """Sweep periodik (tiap 15 mnt): bersihkan .part basi dari worker yang mati
    agar lagu bisa diantre ulang tanpa menunggu cleanup harian jam 03:00."""
    return _sweep_stale_parts()


@app.task(name='celery_tasks.cleanup_transcodes')
def cleanup_transcodes():
    """Cleanup harian: sweep .part basi + heal MP4 yatim ke DB (tidak menjangkau
    /media/transcoded oleh scan sehingga hanya bisa dipulihkan di sini)."""
    result = _sweep_stale_parts()
    cleaned = result["cleaned"]
    logger.info(f"Cleanup harian: {cleaned} transcode dibersihkan")

    # Heal: daftarkan MP4 hasil transcode yang belum terdaftar di DB (mis.
    # registrasi DB sempat gagal saat transcode). Tanpa ini MP4 yatim
    # menggantung selamanya — scan tidak menjangkau /media/transcoded — dan
    # lagu tidak muncul di aplikasi.
    try:
        async def fetch_registered():
            async with async_session() as session:
                rows = await session.execute(select(Song.file_path))
                return {str(pp) for pp in rows.scalars() if pp}

        existing = run_async(fetch_registered())
        healed = 0
        for f in TRANSCODED_PATH.rglob('*.mp4'):
            rel_parts = f.relative_to(TRANSCODED_PATH).parts
            if rel_parts and rel_parts[0].lower() in NON_SONG_DIRS:
                continue  # vocal_removed / pitch / demucs: bukan lagu master
            if str(f) in existing:
                continue
            try:
                if f.stat().st_size == 0:
                    continue
                art, tit = parse_title_artist(f.stem)
                run_async(_upsert_song(str(f), tit, art, file_format='mp4'))
                existing.add(str(f))
                healed += 1
            except Exception:
                continue
        if healed:
            logger.info(f"🧩 Heal: {healed} MP4 yatim terdaftar ke DB")
    except Exception:
        pass

    return {"cleaned": cleaned, "timestamp": datetime.now().isoformat()}


# ============================================
# TASK 5: LAPORAN MINGGUAN PIPELINE (webhook)
# ============================================

@app.task(name='celery_tasks.weekly_pipeline_report')
def weekly_pipeline_report():
    """Laporan mingguan pipeline sync → transcode → hapus sumber, dikirim ke
    webhook (SMB_WEBHOOK_URL). Dijadwalkan tiap Senin 07:00 (Asia/Jakarta)."""
    import shutil
    import urllib.request

    try:
        # ---- MP4 & transcode rate 7 hari ----
        mp4_total = mp4_7d = 0
        now = time.time()
        if TRANSCODED_PATH.exists():
            for f in TRANSCODED_PATH.rglob('*.mp4'):
                if not f.is_file():
                    continue
                # Konsisten dengan heal: folder non-lagu (vocal_removed/pitch/
                # demucs) tidak dihitung sebagai lagu master.
                rel_parts = f.relative_to(TRANSCODED_PATH).parts
                if rel_parts and rel_parts[0].lower() in NON_SONG_DIRS:
                    continue
                mp4_total += 1
                try:
                    if now - f.stat().st_mtime <= 7 * 86400:
                        mp4_7d += 1
                except OSError:
                    pass

        # ---- Sumber master tersisa ----
        sources = 0
        if MEDIA_PATH.exists():
            for f in MEDIA_PATH.rglob('*'):
                if f.is_file() and f.suffix.lower() in MASTER_EXTENSIONS:
                    sources += 1

        # ---- Antrian & pending (Redis) ----
        queue = pending = None
        try:
            pending = int(_get_redis().scard(PENDING_KEY))
        except Exception:
            pass
        try:
            import redis as _redis
            r1 = _redis.from_url(
                os.getenv('CELERY_BROKER_URL', 'redis://karaoke_redis:6379/1'),
                socket_connect_timeout=3, socket_timeout=3)
            queue = int(r1.llen('transcoding'))
            r1.close()
        except Exception:
            pass

        # ---- Disk ----
        disk = {}
        try:
            du = shutil.disk_usage(MEDIA_PATH)
            disk = {
                'free_gb': round(du.free / 1024 ** 3, 1),
                'used_gb': round(du.used / 1024 ** 3, 1),
                'total_gb': round(du.total / 1024 ** 3, 1),
            }
        except Exception:
            pass

        # ---- Lagu aktif di DB ----
        db_songs = None
        try:
            from sqlalchemy import func as _func

            async def _count():
                async with async_session() as s:
                    return (await s.execute(
                        select(_func.count()).select_from(Song)
                        .where(Song.is_active == True))).scalar() or 0

            db_songs = int(run_async(_count()))
        except Exception:
            pass

        # ---- State sinkronisasi ----
        sync = {}
        try:
            sp = Path(os.getenv('SYNC_STATE_PATH', '/srv_media/sync_state.json'))
            if sp.exists():
                sync = json.loads(sp.read_text(encoding='utf-8'))
        except Exception:
            pass

        text = (
            "📊 LAPORAN MINGGUAN PIPELINE KARAOKE\n"
            f"🎞️ MP4 siap: {mp4_total} (+{mp4_7d} minggu ini)\n"
            f"💿 Sumber tersisa: {sources}\n"
            f"🔄 Antrian transcode: {queue if queue is not None else '?'} "
            f"| pending: {pending if pending is not None else '?'}\n"
            f"🎵 Lagu aktif di DB: {db_songs if db_songs is not None else '?'}\n"
            f"📥 Sync: {sync.get('copied_files', '?')}/{sync.get('total_files', '?')} "
            f"file, {sync.get('errors', '?')} error "
            f"({sync.get('phase', '?')})\n"
            f"💾 Disk: bebas {disk.get('free_gb', '?')} GB "
            f"dari {disk.get('total_gb', '?')} GB\n"
        )

        url = os.getenv('SMB_WEBHOOK_URL', '').strip()
        if not url:
            logger.info("📊 Laporan mingguan siap, tapi SMB_WEBHOOK_URL kosong")
            return {"sent": False, "reason": "no webhook", "mp4_7d": mp4_7d}

        payload = {
            "text": text,
            "content": text,
            "type": "weekly_report",
            "mp4_total": mp4_total,
            "mp4_7d": mp4_7d,
            "sources": sources,
            "queue": queue,
            "pending": pending,
            "db_songs": db_songs,
            "disk": disk,
            "sync": {
                "copied": sync.get("copied_files"),
                "total": sync.get("total_files"),
                "errors": sync.get("errors"),
                "phase": sync.get("phase"),
                "failed_files": sync.get("failed_files") or [],
            },
            "timestamp": datetime.now().isoformat(),
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST')
        urllib.request.urlopen(req, timeout=10)
        logger.info("📊 Laporan mingguan terkirim")
        return {"sent": True, "mp4_7d": mp4_7d, "mp4_total": mp4_total}
    except Exception as e:
        logger.error(f"Laporan mingguan gagal: {e}")
        return {"sent": False, "error": str(e)}
