"""
History & Favorites Routes
PT BESTPROFIT FUTURES SURABAYA
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select

from database import get_db
from models import PlaybackHistory, OperatorFavorite, Song
from schemas import SR

router = APIRouter(tags=["History & Favorites"])


@router.get("/api/history/{room_id}")
async def get_history(room_id: str = "default", limit: int = Query(50, le=200), db=Depends(get_db)):
    """Get playback history untuk room tertentu"""
    r = await db.execute(
        select(PlaybackHistory)
        .where(PlaybackHistory.room_id == room_id)
        .order_by(PlaybackHistory.played_at.desc())
        .limit(limit)
    )
    return r.scalars().all()


@router.post("/api/history")
async def add_history(song_id: int, room_id: str = "default", db=Depends(get_db)):
    """Record lagu ke history (dipanggil saat lagu selesai)"""
    sg = (await db.execute(select(Song).where(Song.id == song_id))).scalar_one_or_none()
    if not sg:
        raise HTTPException(404, "Song not found")

    h = PlaybackHistory(song_id=song_id, room_id=room_id, title=sg.title, artist=sg.artist)
    db.add(h)
    await db.commit()
    return {"ok": True}


@router.get("/api/favorites")
async def get_favorites(db=Depends(get_db)):
    """Get semua lagu favorit"""
    r = await db.execute(
        select(OperatorFavorite, Song)
        .join(Song, OperatorFavorite.song_id == Song.id, isouter=True)
        .order_by(OperatorFavorite.created_at.desc())
    )
    results = []
    for fav, song in r:
        results.append({
            "id": fav.id,
            "song_id": fav.song_id,
            "created_at": fav.created_at,
            "song": SR.model_validate(song) if song else None
        })
    return results


@router.post("/api/favorites/{song_id}")
async def toggle_favorite(song_id: int, db=Depends(get_db)):
    """Toggle favorite (add/remove)"""
    existing = (await db.execute(
        select(OperatorFavorite).where(OperatorFavorite.song_id == song_id)
    )).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return {"status": "removed", "song_id": song_id}
    else:
        fav = OperatorFavorite(song_id=song_id)
        db.add(fav)
        await db.commit()
        return {"status": "added", "song_id": song_id}
