"""
Rooms Routes - List, CRUD, Queue Management & Room Sessions (Durasi Pemakaian)
PT BESTPROFIT FUTURES SURABAYA
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import QueueItem, Room, RoomSession
from schemas import RoomCreate, RoomResponse, SessionStart, SessionExtend
from routers.auth import get_admin_user
from sio import sio, request_stop_after_song, clear_room_stop_after
from revision_store import bump_queue_revision

router = APIRouter(tags=["Rooms"])


# ============================================
# HELPERS - SESSION
# ============================================

def _utc_naive(dt: datetime) -> datetime:
    """Normalisasi datetime (aware -> UTC naive) agar konsisten dengan DB."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _serialize_session(s: Optional[RoomSession]) -> Optional[dict]:
    if not s:
        return None
    now = datetime.utcnow()
    remaining = 0
    if s.status == "active" and s.end_time:
        remaining = max(0, int((s.end_time - now).total_seconds()))
    return {
        "id": s.id,
        "room_id": s.room_id,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "end_time": s.end_time.isoformat() if s.end_time else None,
        "duration_minutes": s.duration_minutes,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "status": s.status,
        "remaining_seconds": remaining,
        "created_by": s.created_by,
        "note": s.note,
    }


async def _close_expired_sessions(db) -> None:
    """Auto-complete sesi yang sudah melewati end_time (status: completed).
    Set flag 'berhenti setelah lagu selesai' agar lagu yang sedang diputar
    diselesaikan dulu lalu auto-advance berhenti (bukan di-tengah lagu)."""
    now = datetime.utcnow()
    r = await db.execute(
        select(RoomSession).where(
            RoomSession.status == "active",
            RoomSession.end_time.isnot(None),
            RoomSession.end_time < now,
        )
    )
    expired = r.scalars().all()
    if expired:
        room_ids = list({s.room_id for s in expired})
        r_names = await db.execute(select(Room).where(Room.id.in_(room_ids)))
        name_by_id = {rm.id: rm.name for rm in r_names.scalars().all()}
        for s in expired:
            s.status = "completed"
            s.ended_at = s.end_time
            room_name = name_by_id.get(s.room_id)
            if room_name:
                # Selesai dulu lagu yang diputar, lalu berhenti (jika tidak ada
                # lagu diputar, langsung berhenti sekarang)
                await request_stop_after_song(room_name)
        await db.commit()


async def _get_room_or_404(room_name: str, db) -> Room:
    r = await db.execute(select(Room).where(Room.name == room_name, Room.is_active == True))
    room = r.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    return room


async def _get_active_session(room_id: int, db) -> Optional[RoomSession]:
    r = await db.execute(
        select(RoomSession)
        .where(RoomSession.room_id == room_id, RoomSession.status == "active")
        .order_by(RoomSession.started_at.desc())
        .limit(1)
    )
    return r.scalar_one_or_none()


# ============================================
# ROOM LIST & STATUS
# ============================================

@router.get("/api/rooms/active")
async def get_active_rooms(db=Depends(get_db)):
    """Get rooms + queue count + status sesi pemakaian (publik untuk operator/selector)"""
    await _close_expired_sessions(db)

    # Jumlah antrian waiting per room
    r = await db.execute(
        select(QueueItem.room_id, func.count(QueueItem.id))
        .where(QueueItem.status == "waiting")
        .group_by(QueueItem.room_id)
    )
    active_queues = {row[0]: row[1] for row in r}

    # Sesi aktif per room
    r_sess = await db.execute(
        select(RoomSession).where(RoomSession.status == "active")
    )
    sessions_by_room = {s.room_id: s for s in r_sess.scalars().all()}

    # Semua room
    r2 = await db.execute(select(Room).where(Room.is_active == True).order_by(Room.name))
    rooms = r2.scalars().all()

    result = []
    for room in rooms:
        session = sessions_by_room.get(room.id)
        result.append({
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "capacity": room.capacity,
            "is_active": room.is_active,
            "queue_count": active_queues.get(room.name, 0),
            "is_busy": active_queues.get(room.name, 0) > 0,
            "session_status": session.status if session else "none",
            "session_end_time": session.end_time.isoformat() if session and session.end_time else None,
            "session_remaining_seconds": _serialize_session(session)["remaining_seconds"] if session else 0,
        })

    return {"rooms": result, "total": len(result)}


@router.get("/api/rooms", response_model=List[RoomResponse])
async def get_rooms(db=Depends(get_db)):
    """Get all rooms"""
    r = await db.execute(select(Room).order_by(Room.name))
    return r.scalars().all()


@router.post("/api/rooms")
async def create_room(req: RoomCreate, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Create new room (admin only)"""
    existing = (await db.execute(select(Room).where(Room.name == req.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Room already exists")
    room = Room(name=req.name, description=req.description, capacity=req.capacity)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return RoomResponse.model_validate(room)


@router.put("/api/rooms/{room_id}")
async def update_room(room_id: int, req: RoomCreate, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Update room (admin only)"""
    r = await db.execute(select(Room).where(Room.id == room_id))
    room = r.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    room.name = req.name
    room.description = req.description
    room.capacity = req.capacity
    await db.commit()
    return RoomResponse.model_validate(room)


@router.delete("/api/rooms/{room_id}")
async def delete_room(room_id: int, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Delete room / soft delete (admin only)"""
    r = await db.execute(select(Room).where(Room.id == room_id))
    room = r.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")
    room.is_active = False
    await db.commit()
    return {"ok": True}


@router.get("/api/rooms/{room_name}/queue-count")
async def get_room_queue_count(room_name: str, db=Depends(get_db)):
    """Get jumlah antrian per room (real-time)"""
    count = (await db.execute(
        select(func.count(QueueItem.id))
        .where(QueueItem.room_id == room_name, QueueItem.status == "waiting")
    )).scalar() or 0

    return {"room": room_name, "queue_count": count}


@router.post("/api/rooms/{room_name}/clear-queue")
async def clear_room_queue(room_name: str, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Clear all waiting queue for a room (admin only)"""
    result = await db.execute(
        update(QueueItem)
        .where(QueueItem.room_id == room_name, QueueItem.status == "waiting")
        .values(status="skipped", completed_at=datetime.utcnow())
    )
    await db.commit()

    rev = await bump_queue_revision(room_name)
    await sio.emit("queue_updated", {"room_id": room_name, "revision": rev}, room=room_name)
    await sio.emit("queue_empty", {"room_id": room_name, "message": "Queue dibersihkan oleh admin"}, room=room_name)

    return {"message": f"Queue for room '{room_name}' cleared", "affected": result.rowcount}


# ============================================
# ROOM SESSIONS (Durasi Penggunaan) - Mutasi HANYA admin
# ============================================

@router.get("/api/rooms/{room_name}/session/current")
async def get_current_session(room_name: str, db=Depends(get_db)):
    """Sesi aktif room (publik: operator & player menampilkan timer)"""
    room = await _get_room_or_404(room_name, db)
    await _close_expired_sessions(db)
    s = await _get_active_session(room.id, db)
    if not s:
        return {"active": False, "session": None}
    return {"active": True, "session": _serialize_session(s)}


@router.post("/api/admin/rooms/{room_name}/session/start")
async def start_room_session(
    room_name: str,
    req: SessionStart,
    db=Depends(get_db),
    _admin=Depends(get_admin_user),
):
    """Mulai sesi room. Durasi via menit ATAU waktu selesai absolut (admin only)"""
    room = await _get_room_or_404(room_name, db)
    await _close_expired_sessions(db)

    if await _get_active_session(room.id, db):
        raise HTTPException(400, f"Room '{room_name}' sedang terpakai")

    now = datetime.utcnow()
    if not req.duration_minutes and not req.end_time:
        raise HTTPException(400, "Pilih durasi (menit) atau waktu selesai")

    if req.duration_minutes:
        if req.duration_minutes <= 0:
            raise HTTPException(400, "Durasi harus lebih dari 0 menit")
        end_time = now + timedelta(minutes=req.duration_minutes)
        duration = req.duration_minutes
    else:
        end_time = _utc_naive(req.end_time)
        # Grace 60 detik: toleransi latensi request/input admin
        if end_time <= now - timedelta(seconds=60):
            raise HTTPException(400, "Waktu selesai harus di masa depan")
        duration = max(1, int((end_time - now).total_seconds() // 60))

    s = RoomSession(
        room_id=room.id,
        started_at=now,
        end_time=end_time,
        duration_minutes=duration,
        status="active",
        created_by=_admin,
        note=req.note,
    )
    db.add(s)
    try:
        await db.commit()
    except IntegrityError:
        # Race condition: sesi aktif sudah ada (partial unique index)
        await db.rollback()
        raise HTTPException(400, f"Room '{room_name}' sedang terpakai")
    await db.refresh(s)

    payload = _serialize_session(s)
    await sio.emit("room_session", payload, room=room.name)
    # Sesi baru dimulai -> jangan berhenti setelah lagu (lanjut normal)
    await clear_room_stop_after(room.name)
    return {"active": True, "session": payload}


@router.post("/api/admin/rooms/{room_name}/session/extend")
async def extend_room_session(
    room_name: str,
    req: SessionExtend,
    db=Depends(get_db),
    _admin=Depends(get_admin_user),
):
    """Perpanjang sesi aktif: tambah menit ATAU set waktu selesai baru (admin only)"""
    room = await _get_room_or_404(room_name, db)
    await _close_expired_sessions(db)
    s = await _get_active_session(room.id, db)
    if not s:
        raise HTTPException(400, f"Room '{room_name}' tidak memiliki sesi aktif")

    now = datetime.utcnow()
    base = max(s.end_time or now, now)

    if req.end_time:
        new_end = _utc_naive(req.end_time)
        if new_end <= base - timedelta(seconds=60):
            raise HTTPException(400, "Waktu selesai baru harus setelah waktu selesai saat ini")
        s.end_time = new_end
        s.duration_minutes = (s.duration_minutes or 0) + max(1, int((new_end - base).total_seconds() // 60))
    elif req.minutes:
        if req.minutes <= 0:
            raise HTTPException(400, "Menit tambahan harus lebih dari 0")
        s.end_time = base + timedelta(minutes=req.minutes)
        s.duration_minutes = (s.duration_minutes or 0) + req.minutes
    else:
        raise HTTPException(400, "Pilih menit tambahan atau waktu selesai baru")

    await db.commit()
    await db.refresh(s)

    payload = _serialize_session(s)
    await sio.emit("room_session", payload, room=room.name)
    return {"active": True, "session": payload}


@router.post("/api/admin/rooms/{room_name}/session/end")
async def end_room_session(room_name: str, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Akhiri sesi room (admin only)"""
    room = await _get_room_or_404(room_name, db)
    await _close_expired_sessions(db)
    s = await _get_active_session(room.id, db)
    if not s:
        raise HTTPException(400, f"Room '{room_name}' tidak memiliki sesi aktif")

    s.status = "completed"
    s.ended_at = datetime.utcnow()
    await db.commit()

    payload = _serialize_session(s)
    await sio.emit("room_session", payload, room=room.name)
    # Sesi diakhiri admin: selesaikan lagu yang sedang diputar lalu berhenti
    await request_stop_after_song(room.name)
    return {"active": False, "session": payload}


@router.get("/api/admin/rooms/{room_name}/sessions")
async def room_session_history(
    room_name: str,
    limit: int = Query(50, le=200),
    db=Depends(get_db),
    _admin=Depends(get_admin_user),
):
    """Riwayat sesi pemakaian room (admin only)"""
    room = await _get_room_or_404(room_name, db)
    await _close_expired_sessions(db)  # jangan tampilkan sesi expired sebagai 'active'
    r = await db.execute(
        select(RoomSession)
        .where(RoomSession.room_id == room.id)
        .order_by(RoomSession.started_at.desc())
        .limit(limit)
    )
    return [_serialize_session(s) for s in r.scalars().all()]
