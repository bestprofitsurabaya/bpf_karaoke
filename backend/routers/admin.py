"""
Admin Routes - Scan, Stats, Bulk Operations
PT BESTPROFIT FUTURES SURABAYA
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, update, or_

from database import get_db
from models import Song, QueueItem
from routers.auth import get_admin_user
from sio import active

router = APIRouter(tags=["Admin"])

MEDIA_PATH = os.getenv("MEDIA_PATH", "/media/lagu")
TRANSCODED_PATH = Path(os.getenv("TRANSCODED_PATH", "/media/transcoded"))
SYNC_STATE_PATH = Path(os.getenv("SYNC_STATE_PATH", "/srv_media/sync_state.json"))

# --- Pipeline status (publik, untuk panel operator) ---
_MASTER_EXTS = {".mpg", ".mpeg", ".avi", ".mkv", ".wmv", ".flv", ".vob", ".m2v", ".mpv", ".3gp", ".dat"}
_PIPELINE_CACHE = {"ts": 0.0, "data": None}  # cache 15 detik agar refresh panel tidak berat


def _count_media():
    """Hitung file sumber master, MP4 siap, dan .part (aktif/basi). Jalan di thread."""
    sources = mp4s = parts_active = parts_stale = 0
    now = datetime.utcnow().timestamp()
    try:
        for p in Path(MEDIA_PATH).rglob("*"):
            if p.is_file() and p.suffix.lower() in _MASTER_EXTS:
                sources += 1
    except Exception:
        pass
    try:
        for p in Path(TRANSCODED_PATH).rglob("*"):
            if not p.is_file():
                continue
            sfx = p.suffix.lower()
            if sfx == ".mp4":
                mp4s += 1
            elif sfx == ".part":
                try:
                    if now - p.stat().st_mtime > 3600:
                        parts_stale += 1
                    else:
                        parts_active += 1
                except Exception:
                    parts_active += 1
    except Exception:
        pass
    return sources, mp4s, parts_active, parts_stale


def _redis_queues():
    """Ambil antrian transcode (db 1) & penanda pending (db 0) dari Redis. Fail-open."""
    import redis

    queue = pending = None
    try:
        r = redis.from_url(
            os.getenv("REDIS_URL", "redis://karaoke_redis:6379/0"),
            socket_connect_timeout=3, socket_timeout=3,
        )
        pending = int(r.scard("transcode:pending"))
        r.close()
    except Exception:
        pending = None
    try:
        r = redis.from_url(
            os.getenv("CELERY_BROKER_URL", "redis://karaoke_redis:6379/1"),
            socket_connect_timeout=3, socket_timeout=3,
        )
        queue = int(r.llen("transcoding"))
        r.close()
    except Exception:
        queue = None
    return queue, pending


@router.post("/api/admin/songs/bulk-genre")
async def bulk_update_genre(
    song_ids: List[int],
    genre: str = Query(..., min_length=1, max_length=100),
    db=Depends(get_db),
    _admin=Depends(get_admin_user),
):
    """Bulk update genre untuk multiple songs sekaligus (admin only)
    Body: [1, 2, 3, ...]
    Query: ?genre=Pop+Indonesia
    """
    if not song_ids:
        raise HTTPException(400, "No song IDs provided")

    if len(song_ids) > 500:
        raise HTTPException(400, "Maximum 500 songs per bulk operation")

    result = await db.execute(
        update(Song)
        .where(Song.id.in_(song_ids))
        .values(genre=genre, updated_at=datetime.utcnow())
    )
    await db.commit()

    updated_count = result.rowcount

    return {
        'message': f'Genre updated to "{genre}" for {updated_count} songs',
        'genre': genre,
        'updated_count': updated_count,
        'total_requested': len(song_ids),
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/api/admin/songs/auto-genre")
async def auto_detect_genres(
    db=Depends(get_db),
    _admin=Depends(get_admin_user),
    limit: int = Query(100, le=500),
):
    """Auto-detect genre menggunakan AI untuk lagu tanpa genre (admin only)"""
    from services.genre_detector import genre_detector

    r = await db.execute(
        select(Song)
        .where(
            Song.is_active == True,
            or_(Song.genre.is_(None), Song.genre == 'Unknown', Song.genre == '')
        )
        .limit(limit)
    )
    songs = r.scalars().all()

    if not songs:
        return {'message': 'No songs need genre detection', 'processed': 0}

    results = {
        'processed': 0,
        'auto_assigned': 0,
        'set_to_unknown': 0,
        'details': []
    }

    for song in songs:
        prediction = genre_detector.predict_genre(
            artist=song.artist or '',
            title=song.title
        )

        if prediction['confidence'] > 0.8:
            song.genre = prediction['genre']
            results['auto_assigned'] += 1
            results['details'].append({
                'song_id': song.id,
                'title': song.title,
                'artist': song.artist,
                'assigned_genre': prediction['genre'],
                'confidence': prediction['confidence'],
                'method': prediction['method'],
                'status': 'auto_assigned'
            })
        else:
            song.genre = 'Unknown'
            results['set_to_unknown'] += 1
            results['details'].append({
                'song_id': song.id,
                'title': song.title,
                'artist': song.artist,
                'predicted_genre': prediction['genre'],
                'confidence': prediction['confidence'],
                'status': 'set_to_unknown_for_review'
            })

        results['processed'] += 1

    await db.commit()

    return results


@router.get("/api/admin/genre-detector/stats")
async def get_genre_detector_stats(_admin=Depends(get_admin_user)):
    """Get genre detector statistics (admin only)"""
    from services.genre_detector import genre_detector
    return genre_detector.get_stats()


@router.post("/api/admin/genre-detector/add-keyword")
async def add_genre_keyword(genre: str, keyword: str, _admin=Depends(get_admin_user)):
    """Add keyword to genre detector (admin only)"""
    from services.genre_detector import genre_detector
    success = genre_detector.add_keyword(genre, keyword)
    return {
        'success': success,
        'genre': genre,
        'keyword': keyword,
        'message': 'Keyword added' if success else 'Keyword already exists'
    }


@router.post("/api/admin/songs/scan")
async def scan(path: Optional[str] = Query(None), db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Scan media folder untuk lagu baru (admin only)"""
    sp = Path(path) if path else Path(MEDIA_PATH)
    if not sp.exists():
        raise HTTPException(404, "Path not found")
    ext = {".mp4", ".mkv", ".avi", ".webm", ".mov"}
    new_count = 0
    reactivated = 0
    for f in sp.rglob("*"):
        if f.suffix.lower() not in ext:
            continue
        ex = (await db.execute(select(Song).where(Song.file_path == str(f)))).scalar_one_or_none()
        if ex:
            if not ex.is_active:
                ex.is_active = True
                ex.updated_at = datetime.utcnow()
                reactivated += 1
            continue
        nm, art, tit = f.stem, None, f.stem
        if " - " in nm:
            p = nm.split(" - ", 1)
            art = p[0].strip()
            tit = p[1].strip()
        # Auto-detect genre dengan AI
        predicted_genre = 'Unknown'
        try:
            from services.genre_detector import genre_detector
            prediction = genre_detector.predict_genre(artist=art, title=tit)
            predicted_genre = prediction['genre'] if prediction['confidence'] > 0.8 else 'Unknown'
        except Exception:
            pass
        db.add(Song(
            title=tit, artist=art, genre=predicted_genre, file_path=str(f),
            file_format=f.suffix.lower().replace(".", ""), is_active=True
        ))
        new_count += 1
    await db.commit()

    total_active = (await db.execute(
        select(func.count(Song.id)).where(Song.is_active == True)
    )).scalar() or 0
    return {
        "message": f"Scan selesai! {new_count} lagu baru, total {total_active} lagu aktif.",
        "new_songs": new_count,
        "reactivated_songs": reactivated,
        "total_active_songs": total_active
    }


@router.get("/api/admin/sync/status")
async def sync_status(_admin=Depends(get_admin_user)):
    """Status sinkronisasi bank karaoke dari komputer Windows XP (admin only)."""
    try:
        with open(SYNC_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["available"] = True
        return data
    except FileNotFoundError:
        return {
            "available": False,
            "message": "Sync belum berjalan / state file belum ada.",
            "done": False,
        }
    except Exception as e:
        return {"available": False, "error": str(e), "done": False}


@router.get("/api/admin/stats")
async def admin_stats(db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Statistik lengkap (admin only)"""
    ts = (await db.execute(select(func.count(Song.id)).where(Song.is_active == True))).scalar() or 0
    tp = (await db.execute(select(func.sum(Song.play_count)))).scalar() or 0
    qt = (await db.execute(
        select(func.count(QueueItem.id)).where(func.date(QueueItem.created_at) == datetime.utcnow().date())
    )).scalar() or 0
    return {
        "total_songs": ts, "total_plays": int(tp), "queue_today": qt,
        "active_connections": len(active), "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/api/stats")
async def public_stats(db=Depends(get_db)):
    """Statistik ringan untuk operator (publik, tanpa data sensitif)"""
    ts = (await db.execute(select(func.count(Song.id)).where(Song.is_active == True))).scalar() or 0
    tp = (await db.execute(select(func.sum(Song.play_count)))).scalar() or 0
    qt = (await db.execute(
        select(func.count(QueueItem.id)).where(func.date(QueueItem.created_at) == datetime.utcnow().date())
    )).scalar() or 0
    return {
        "total_songs": ts, "total_plays": int(tp), "queue_today": qt,
        "active_connections": len(active), "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/api/pipeline")
async def pipeline_status():
    """Ringkasan pipeline sync → transcode → hapus sumber (publik, untuk panel operator)."""
    import asyncio
    import shutil

    now = datetime.utcnow().timestamp()
    if _PIPELINE_CACHE["data"] is not None and now - _PIPELINE_CACHE["ts"] < 15:
        return _PIPELINE_CACHE["data"]

    sources, mp4s, parts_active, parts_stale = await asyncio.to_thread(_count_media)
    queue_len, pending = await asyncio.to_thread(_redis_queues)

    # State sinkronisasi dari karaoke_sync (file JSON yang ditulis worker)
    sync = {"available": False, "phase": "off", "copied": 0, "total": 0, "errors": 0, "hang_dirs": [], "last_error": ""}
    try:
        with open(SYNC_STATE_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        sync = {
            "available": True,
            "phase": d.get("phase", "off"),
            "copied": d.get("copied_files", 0),
            "total": d.get("total_files", 0),
            "errors": d.get("errors", 0),
            "hang_dirs": d.get("hang_dirs") or [],
            "last_error": d.get("last_error", ""),
            "done": bool(d.get("done")),
        }
    except Exception:
        pass

    # Ruang disk partisi media
    disk = {"total": 0, "used": 0, "free": 0}
    try:
        du = shutil.disk_usage(MEDIA_PATH)
        disk = {"total": du.total, "used": du.used, "free": du.free}
    except Exception:
        pass

    data = {
        "sync": sync,
        "transcode": {
            "sources": sources,
            "mp4_ready": mp4s,
            "queue": queue_len,
            "pending": pending,
            "active_parts": parts_active,
            "stale_parts": parts_stale,
        },
        "disk": disk,
        "youtube": {"configured": bool(os.getenv("YOUTUBE_API_KEY"))},
        "timestamp": datetime.utcnow().isoformat(),
    }
    _PIPELINE_CACHE.update(ts=now, data=data)
    return data


def _dispatch_admin_task(task_name: str, message: str):
    """Kirim task celery dari proses backend (uvicorn). Fail-open dengan pesan
    jelas bila broker Redis tidak tersedia (502, bukan 500 polos)."""
    try:
        from celery_app import app as celery_app

        task = celery_app.send_task(task_name, queue='maintenance')
        return {"task_id": task.id, "message": message}
    except Exception as e:
        raise HTTPException(502, f"Broker task tidak tersedia: {type(e).__name__}")


@router.post("/api/admin/pipeline/scan")
async def trigger_scan(_admin=Depends(get_admin_user)):
    """Picu scan media + antre transcode (celery task, queue maintenance).
    Tidak memblokir request — scan berjalan di background worker."""
    return _dispatch_admin_task(
        'celery_tasks.scan_for_new_media', "Scan media dijadwalkan")


@router.post("/api/admin/pipeline/sweep")
async def trigger_sweep(_admin=Depends(get_admin_user)):
    """Picu sweep .part basi + self-heal penanda antrian (celery task, queue
    maintenance) — mempercepat pemulihan lagu yang terblokir task mati."""
    return _dispatch_admin_task(
        'celery_tasks.sweep_stale_parts', "Sweep .part basi dimulai")
