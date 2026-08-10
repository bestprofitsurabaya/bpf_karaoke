"""
Media Routes - Video Streaming & Pitch/Key Shift (FFmpeg)
PT BESTPROFIT FUTURES SURABAYA
"""
import os
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from database import get_db
from models import Song

router = APIRouter(tags=["Media"])

MEDIA_PATH = os.getenv("MEDIA_PATH", "/media/lagu")
TRANSCODED_PATH = Path(os.getenv("TRANSCODED_PATH", "/media/transcoded"))
PITCH_CACHE_DIR = TRANSCODED_PATH / "pitch"

# Mencegah dua request menghasilkan file pitch yang sama secara bersamaan
_generation_lock = threading.Lock()


def _generate_pitch_shifted(src: Path, dest: Path, semitones: int) -> None:
    """
    Shift pitch tanpa mengubah tempo menggunakan recipe FFmpeg standar:
      asetrate=<rate*factor>,aresample=<rate>,atempo=1/factor
    Video di-copy tanpa re-encode (cepat); hanya audio yang diproses.
    """
    factor = 2 ** (semitones / 12)
    rate = 44100
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-af", f"asetrate={rate}*{factor:.6f},aresample={rate},atempo={1 / factor:.6f}",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=600)


def _resolve_song_path(song: Song) -> Path:
    fp = Path(song.file_path)
    if not fp.exists():
        fp = Path(MEDIA_PATH) / fp.name
    return fp


@router.get("/api/media/stream/{song_id}")
async def stream_song(
    song_id: int,
    key: int = Query(0),
    db=Depends(get_db),
):
    """
    Stream video lagu. Parameter `key` (semitone) mengaktifkan pitch shift
    via FFmpeg; hasil di-cache di /media/transcoded/pitch.
    Nilai key di-clamp ke -12..12 (bukan 422) agar klien stale tidak
    memutus streaming.
    """
    key = max(-12, min(12, key))

    r = await db.execute(select(Song).where(Song.id == song_id))
    if not (song := r.scalar_one_or_none()):
        raise HTTPException(404, "Not found")
    fp = _resolve_song_path(song)
    if not fp.exists():
        raise HTTPException(404, "File not found")

    # Tanpa pitch shift -> stream file asli
    if key == 0:
        return FileResponse(fp, media_type="video/mp4", headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        })

    # Pitch shift: cek cache, generate jika belum ada
    PITCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    dest = PITCH_CACHE_DIR / f"{fp.stem}_k{key:+d}.mp4"

    if not dest.exists():
        with _generation_lock:
            if not dest.exists():
                try:
                    _generate_pitch_shifted(fp, dest, key)
                except Exception as e:
                    # Fallback: stream original jika generasi gagal,
                    # agar playback tidak terputus.
                    print(f"⚠️ Pitch shift failed ({song_id}, key={key}): {e}")
                    return FileResponse(fp, media_type="video/mp4", headers={
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "public, max-age=3600",
                    })

    return FileResponse(dest, media_type="video/mp4", headers={
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000",  # cache lama: hasil pitch immutable
    })
