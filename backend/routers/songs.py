"""
Songs Routes - CRUD, Search & Genres
PT BESTPROFIT FUTURES SURABAYA
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, or_

from database import get_db
from models import Song
from schemas import SR, SongUpdate
from routers.auth import get_admin_user

router = APIRouter(tags=["Songs"])


@router.get("/api/songs", response_model=List[SR])
async def get_songs(
    search: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    sort: Optional[str] = Query(None, pattern="^(title|artist|plays|newest)$"),
    limit: int = Query(250, le=1000),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    """Daftar lagu dengan filter & sorting di sisi server agar konsisten dengan pagination."""
    q = select(Song).where(Song.is_active == True)
    if search:
        q = q.where(or_(Song.title.ilike(f"%{search}%"), Song.artist.ilike(f"%{search}%")))
    if genre:
        q = q.where(Song.genre == genre)
    if sort == "artist":
        q = q.order_by(Song.artist, Song.title)
    elif sort == "plays":
        q = q.order_by(Song.play_count.desc(), Song.title)
    elif sort == "newest":
        q = q.order_by(Song.id.desc())
    else:
        q = q.order_by(Song.title)
    return (await db.execute(q.offset(offset).limit(limit))).scalars().all()


@router.get("/api/songs/genres")
async def genres(db=Depends(get_db)):
    r = await db.execute(
        select(Song.genre, func.count(Song.id))
        .where(Song.is_active == True, Song.genre.isnot(None))
        .group_by(Song.genre)
        .order_by(func.count(Song.id).desc())
    )
    return [{"genre": row[0], "count": row[1]} for row in r]


@router.get("/api/songs/{song_id}", response_model=SR)
async def get_song_detail(song_id: int, db=Depends(get_db)):
    """Detail satu lagu (menghindari fetch seluruh koleksi di frontend)"""
    r = await db.execute(select(Song).where(Song.id == song_id, Song.is_active == True))
    song = r.scalar_one_or_none()
    if not song:
        raise HTTPException(404, "Song not found")
    return song


@router.put("/api/songs/{song_id}")
async def update_song(song_id: int, req: SongUpdate, db=Depends(get_db), _admin=Depends(get_admin_user)):
    r = await db.execute(select(Song).where(Song.id == song_id, Song.is_active == True))
    if not (song := r.scalar_one_or_none()):
        raise HTTPException(404, "Not found")
    song.title = req.title
    song.artist = req.artist
    song.genre = req.genre
    await db.commit()
    return {"ok": True}


@router.delete("/api/songs/{song_id}")
async def delete_song(song_id: int, db=Depends(get_db), _admin=Depends(get_admin_user)):
    r = await db.execute(select(Song).where(Song.id == song_id))
    if not (song := r.scalar_one_or_none()):
        raise HTTPException(404, "Not found")
    song.is_active = False
    await db.commit()
    return {"ok": True}
