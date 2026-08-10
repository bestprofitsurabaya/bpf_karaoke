"""
YouTube Routes - Pencarian lagu via YouTube Data API v3 (gratis) & antrean
=======================================================================
Fitur: cari lagu yang TIDAK tersedia di database lokal, lalu putar via
embed player (iframe youtube-nocookie) di PlayerScreen.

Kuota gratis YouTube Data API v3 = 10.000 unit/hari.
- search.list  = 100 unit per panggilan (~100 pencarian/hari)
- videos.list  = 1 unit per panggilan (ambil durasi semua hasil sekaligus)
=> Hasil pencarian di-CACHE 30 menit agar kuota tidak boros.

Konfigurasi: set YOUTUBE_API_KEY di .env (Google Cloud Console -> YouTube
Data API v3 -> API key). Tanpa key, endpoint mengembalikan 503.
"""
import os
import re
import time
from collections import deque
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from sqlalchemy import select

from database import async_session
from models import Song, QueueItem
from sio import sio
from revision_store import bump_queue_revision

router = APIRouter(prefix="/api/youtube", tags=["YouTube"])

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
SEARCH_COST = 100  # unit kuota per search.list

# Cache hasil pencarian di memory (TTL 30 menit) agar kuota hemat
_cache: dict = {}
CACHE_TTL = 1800  # detik

# Rate-limit sederhana per klien (free tier hanya ±100 pencarian unik/hari)
RATE_LIMIT = 20          # max request per jendela
RATE_WINDOW = 60         # detik
_rate: dict = {}         # ip -> deque(timestamp)


class YTQueueRequest(BaseModel):
    youtube_id: str
    title: str
    artist: Optional[str] = None
    room_id: str = "default"
    requester_name: Optional[str] = None


def _parse_duration(iso: str) -> Optional[int]:
    """Konversi 'PT3M45S' -> 225 detik. None bila format tidak dikenal."""
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso or "")
    if not m or not any(m.groups()):
        return None  # format tidak dikenal / durasi kosong
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def _rate_limited(client_ip: str) -> bool:
    """True bila klien ini melebihi batas request per jendela waktu."""
    now = time.time()
    q = _rate.setdefault(client_ip, deque())
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        return True
    q.append(now)
    return False


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(12, le=20),
):
    """Cari lagu di YouTube (hanya video yang bisa di-embed)."""
    if not YOUTUBE_API_KEY:
        raise HTTPException(
            503, "YouTube API key belum dikonfigurasi. Set YOUTUBE_API_KEY di .env "
                 "(YouTube Data API v3, gratis 10.000 unit/hari).")
    if _rate_limited(_client_ip(request)):
        raise HTTPException(
            429, "Terlalu banyak pencarian — coba lagi beberapa saat lagi "
                 "(kuota YouTube gratis terbatas).")

    key = q.strip().lower()
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return {"query": q, "results": hit[1][:limit], "cached": True,
                "quota_note": f"~{SEARCH_COST} unit/pencarian (10.000 unit/hari gratis)"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://www.googleapis.com/youtube/v3/search", params={
                "part": "snippet",
                "q": q,
                "type": "video",
                "maxResults": min(limit, 20),
                "videoEmbeddable": "true",   # wajib: harus bisa diputar via iframe
                "safeSearch": "strict",      # hindari konten dewasa
                "key": YOUTUBE_API_KEY,
            })
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])

            ids = [it["id"]["videoId"] for it in items
                   if it.get("id", {}).get("videoId")]
            durations: dict = {}
            if ids:
                # Satu panggilan videos.list untuk durasi SEMUA hasil (1 unit)
                vr = await client.get("https://www.googleapis.com/youtube/v3/videos", params={
                    "part": "contentDetails",
                    "id": ",".join(ids),
                    "key": YOUTUBE_API_KEY,
                })
                vr.raise_for_status()
                for v in vr.json().get("items", []):
                    durations[v["id"]] = _parse_duration(
                        v.get("contentDetails", {}).get("duration", ""))

        results = []
        for it in items:
            vid = it.get("id", {}).get("videoId")
            sn = it.get("snippet", {})
            if not vid:
                continue
            thumbs = sn.get("thumbnails") or {}
            results.append({
                "youtube_id": vid,
                "title": sn.get("title", ""),
                "artist": sn.get("channelTitle", ""),
                "thumbnail": (thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""),
                "duration": durations.get(vid),
            })

        _cache[key] = (now, results)
        return {"query": q, "results": results[:limit], "cached": False,
                "quota_note": f"~{SEARCH_COST} unit/pencarian (10.000 unit/hari gratis)"}
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"YouTube API error: HTTP {e.response.status_code}")
    except Exception as e:  # noqa: BLE001 - error eksternal, tampilkan pesan
        raise HTTPException(502, f"YouTube API error: {e}")


@router.post("/queue")
async def queue_youtube(req: YTQueueRequest):
    """Daftarkan lagu YouTube sebagai Song (idempotent per youtube_id) lalu
    tambahkan ke antrian room. Song diputar oleh PlayerScreen via iframe embed."""
    yt = req.youtube_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,}", yt):
        raise HTTPException(400, "youtube_id tidak valid")

    file_path = f"yt:{yt}"
    async with async_session() as db:
        sg = (await db.execute(select(Song).where(Song.file_path == file_path))).scalar_one_or_none()
        if not sg:
            sg = Song(
                title=(req.title or "YouTube")[:500],
                artist=(req.artist or "")[:300] or None,
                genre="YouTube",
                file_path=file_path,
                file_format="youtube",
                is_active=True,
            )
            db.add(sg)
            await db.flush()
        qi = QueueItem(song_id=sg.id, room_id=req.room_id,
                       requester_name=req.requester_name)
        db.add(qi)
        await db.commit()
        await db.refresh(sg)

    rev = await bump_queue_revision(req.room_id)
    await sio.emit("queue_updated", {"room_id": req.room_id, "revision": rev},
                   room=req.room_id)

    return {"id": qi.id, "song_id": sg.id, "room_id": req.room_id,
            "title": sg.title, "artist": sg.artist or ""}
