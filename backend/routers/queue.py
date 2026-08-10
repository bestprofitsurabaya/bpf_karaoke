"""
Queue Routes - Add, List, Remove, Batch
PT BESTPROFIT FUTURES SURABAYA
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Response
from sqlalchemy import select, update, or_

from database import get_db
from models import QueueItem, Song
from schemas import QR, QResp, SR
from sio import sio
from revision_store import bump_queue_revision, get_queue_revision

router = APIRouter(tags=["Queue"])


@router.post("/api/queue")
async def add_queue(req: QR, db=Depends(get_db)):
    sg = (await db.execute(select(Song).where(Song.id == req.song_id))).scalar_one_or_none()
    if not sg:
        raise HTTPException(404, "Song not found")
    qi = QueueItem(song_id=req.song_id, room_id=req.room_id, requester_name=req.requester_name)
    db.add(qi)
    await db.commit()
    await db.refresh(qi)
    rev = await bump_queue_revision(req.room_id)
    await sio.emit("queue_updated", {"room_id": req.room_id, "revision": rev}, room=req.room_id)
    return QResp(
        id=qi.id, song_id=qi.song_id, room_id=qi.room_id,
        status=qi.status, priority=qi.priority, created_at=qi.created_at,
        requester_name=qi.requester_name,
        song=SR.model_validate(sg)
    )


@router.get("/api/queue/{room_id}")
async def get_queue(response: Response, room_id: str = "default", db=Depends(get_db)):
    """
    List antrian waiting untuk satu room.

    Fix: urutkan berdasarkan priority DESC dulu (agar drag & drop reorder
    benar-benar mengubah urutan), lalu created_at ASC sebagai tie-breaker.
    Fix: join langsung ke tabel songs (hilangkan N+1 query).
    Header X-Queue-Revision untuk proteksi race pada reorder_queue.
    """
    r = await db.execute(
        select(QueueItem, Song)
        .join(Song, QueueItem.song_id == Song.id, isouter=True)
        .where(QueueItem.room_id == room_id, QueueItem.status == "waiting")
        .order_by(QueueItem.priority.desc(), QueueItem.created_at.asc())
    )
    rows = r.all()
    out = []
    for qi, sg in rows:
        out.append(QResp(
            id=qi.id, song_id=qi.song_id, room_id=qi.room_id,
            status=qi.status, priority=qi.priority, created_at=qi.created_at,
            requester_name=qi.requester_name,
            song=SR.model_validate(sg) if sg else None
        ))
    response.headers["X-Queue-Revision"] = str(await get_queue_revision(room_id))
    return out


@router.delete("/api/queue/{queue_id}")
async def del_queue(queue_id: int, room_id: str = Query("default"), db=Depends(get_db)):
    r = await db.execute(
        update(QueueItem)
        .where(QueueItem.id == queue_id, QueueItem.room_id == room_id)
        .values(status="skipped", completed_at=datetime.utcnow())
    )
    if r.rowcount == 0:
        raise HTTPException(404, "Not found")
    await db.commit()
    rev = await bump_queue_revision(room_id)
    await sio.emit("queue_updated", {"room_id": room_id, "revision": rev}, room=room_id)
    return {"ok": True}


@router.post("/api/queue/batch")
async def batch_add_queue(song_ids: List[int], room_id: str = Query("default"), db=Depends(get_db)):
    """Batch add multiple songs ke antrian"""
    added = 0
    for sid in song_ids:
        sg = (await db.execute(select(Song).where(Song.id == sid, Song.is_active == True))).scalar_one_or_none()
        if sg:
            qi = QueueItem(song_id=sid, room_id=room_id)
            db.add(qi)
            added += 1

    await db.commit()
    rev = await bump_queue_revision(room_id)
    await sio.emit("queue_updated", {"room_id": room_id, "action": "batch_added", "revision": rev}, room=room_id)

    return {"message": f"{added} songs added to queue", "added": added, "total_requested": len(song_ids)}


@router.post("/api/queue/batch-filter")
async def batch_add_filtered(
    room_id: str = Query("default"),
    search: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    limit: int = Query(300, le=500),
    db=Depends(get_db),
):
    """Tambah SEMUA lagu hasil filter (search/genre/language) ke antrian.
    Dedup terhadap lagu yang sudah waiting di room tersebut."""
    q = select(Song.id).where(Song.is_active == True)
    if search:
        q = q.where(or_(Song.title.ilike(f"%{search}%"), Song.artist.ilike(f"%{search}%")))
    if genre:
        q = q.where(Song.genre == genre)
    if language:
        q = q.where(Song.language == language)
    q = q.order_by(Song.title).limit(limit)
    ids = (await db.execute(q)).scalars().all()

    existing = set((await db.execute(
        select(QueueItem.song_id).where(QueueItem.room_id == room_id, QueueItem.status == "waiting")
    )).scalars())

    to_add = [sid for sid in ids if sid not in existing]
    for sid in to_add:
        db.add(QueueItem(song_id=sid, room_id=room_id))
    await db.commit()

    rev = await bump_queue_revision(room_id)
    await sio.emit("queue_updated", {"room_id": room_id, "action": "batch_filter_added", "revision": rev}, room=room_id)

    return {
        "matched": len(ids),
        "added": len(to_add),
        "skipped_duplicates": len(ids) - len(to_add),
        "message": f"{len(to_add)} lagu ditambahkan ke antrian",
    }
