"""
BPF Karaoke System - Backend API v3.0 (Production)
PT BESTPROFIT FUTURES SURABAYA
"""
import asyncio, os, json, hashlib, secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, ForeignKey,
    select, update, delete, func, or_
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from jose import jwt
import socketio

# ============================================
# SETTINGS
# ============================================
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://karaoke_admin:K4r40k3S3cur3P4ss!2024@karaoke_db:5432/karaoke_db"
    jwt_secret: str = "K4r40k3JWTS3cr3tK3yV3ryL0ngStr1ng2024!@#$"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 1440
    admin_user: str = "admin"
    admin_password: str = "AdminK4r40k3!2024"
    media_path: str = "/media/lagu"
    cors_origins: str = "*"
    class Config: env_file = ".env"

settings = Settings()

# ============================================
# DATABASE
# ============================================
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Song(Base):
    __tablename__ = "songs"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    title = mapped_column(String(500), nullable=False, index=True)
    artist = mapped_column(String(300), nullable=True, index=True)
    genre = mapped_column(String(100), nullable=True, index=True)
    album = mapped_column(String(300), nullable=True)
    year = mapped_column(Integer, nullable=True)
    language = mapped_column(String(50), nullable=True)
    file_path = mapped_column(String(1000), nullable=False)
    file_format = mapped_column(String(10), nullable=True)
    duration = mapped_column(Integer, nullable=True)
    has_vocal_track = mapped_column(Boolean, default=False)
    vocal_channel = mapped_column(String(20), nullable=True)
    play_count = mapped_column(Integer, default=0)
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QueueItem(Base):
    __tablename__ = "queue"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id = mapped_column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    room_id = mapped_column(String(100), nullable=False, default="KARAOKE BPF SBY", index=True)
    requester_name = mapped_column(String(100), nullable=True)
    status = mapped_column(String(20), default="waiting")
    priority = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    played_at = mapped_column(DateTime, nullable=True)
    completed_at = mapped_column(DateTime, nullable=True)

class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    username = mapped_column(String(100), unique=True, nullable=False)
    password_hash = mapped_column(String(200), nullable=False)
    role = mapped_column(String(20), default="operator")
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class Room(Base):
    __tablename__ = "rooms"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String(100), nullable=False, unique=True)
    description = mapped_column(String(500), nullable=True)
    capacity = mapped_column(Integer, default=10)
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# MODELS
# ============================================
class LoginRequest(BaseModel): username: str; password: str
class SongUpdate(BaseModel): title: str; artist: Optional[str] = None; genre: Optional[str] = None

class SR(BaseModel):
    id: int; title: str; artist: Optional[str] = None; genre: Optional[str] = None
    file_path: str; play_count: int = 0; is_active: bool = True
    class Config: from_attributes = True

class QR(BaseModel): song_id: int; room_id: str = "KARAOKE BPF SBY"; requester_name: Optional[str] = None

class QResp(BaseModel):
    id: int; song_id: int; room_id: str; status: str; priority: int; created_at: datetime
    song: Optional[SR] = None
    class Config: from_attributes = True


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: int = 10

class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    capacity: int
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True

# ============================================
# HELPERS
# ============================================
def get_password_hash(p: str) -> str:
    s = secrets.token_hex(16); h = hashlib.sha256(f"{s}{p}".encode()).hexdigest(); return f"{s}${h}"

def verify_password(plain: str, hashed: str) -> bool:
    try:
        s, h = hashed.split("$", 1)
        return hashlib.sha256(f"{s}{plain}".encode()).hexdigest() == h
    except: return False

def create_access_token(data: dict, exp: Optional[timedelta] = None) -> str:
    d = data.copy(); d["exp"] = datetime.utcnow() + (exp or timedelta(minutes=settings.jwt_expiration))
    return jwt.encode(d, settings.jwt_secret, algorithm=settings.jwt_algorithm)

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(title="BPF Karaoke", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

mp = Path(settings.media_path); mp.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(mp)), name="media")

# ============================================
# SOCKET.IO
# ============================================
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", logger=False, engineio_logger=False)
active: Dict[str, Any] = {}

@sio.event
async def connect(sid, environ):
    active[sid] = {"sid": sid, "type": "unknown", "room": "KARAOKE BPF SBY"}
@sio.event
async def disconnect(sid):
    active.pop(sid, None)

@sio.event
async def register(sid, data):
    room = data.get("room_id", "KARAOKE BPF SBY")
    if sid in active: active[sid].update({"type": data.get("type", "unknown"), "room": room})
    await sio.enter_room(sid, room)
    await sio.emit("ok", {"type": data.get("type"), "room_id": room}, to=sid)

@sio.event
async def play_song(sid, data):
    sid_q = data.get("queue_id"); room = data.get("room_id", "KARAOKE BPF SBY")
    async with async_session() as s:
        if sid_q: await s.execute(update(QueueItem).where(QueueItem.id == sid_q).values(status="playing", played_at=datetime.utcnow()))
        await s.execute(update(Song).where(Song.id == data.get("song_id")).values(play_count=Song.play_count + 1))
        await s.commit()
    await sio.emit("play", {"song_id": data.get("song_id"), "queue_id": sid_q}, room=room)
    await sio.emit("queue_updated", {"room_id": room}, room=room)

@sio.event
async def pause_song(sid, data):
    await sio.emit("ctrl", {"action": "pause"}, room=data.get("room_id", "KARAOKE BPF SBY"))
@sio.event
async def resume_song(sid, data):
    await sio.emit("ctrl", {"action": "resume"}, room=data.get("room_id", "KARAOKE BPF SBY"))

@sio.event
async def skip_song(sid, data):
    room = data.get("room_id", "KARAOKE BPF SBY")
    async with async_session() as s:
        if data.get("queue_id"): await s.execute(update(QueueItem).where(QueueItem.id == data["queue_id"]).values(status="skipped", completed_at=datetime.utcnow())); await s.commit()
    await sio.emit("ctrl", {"action": "skip"}, room=room)
    await sio.emit("queue_updated", {"room_id": room}, room=room)

@sio.event
async def song_ended(sid, data):
    """Dipanggil saat video selesai. Auto-play lagu berikutnya setelah jeda."""
    room = data.get("room_id", "KARAOKE BPF SBY")
    queue_id = data.get("queue_id")
    
    # Tandai lagu selesai
    async with async_session() as s:
        if queue_id:
            await s.execute(
                update(QueueItem)
                .where(QueueItem.id == queue_id)
                .values(status="played", completed_at=datetime.utcnow())
            )
            await s.commit()
    
    # Emit queue update + idle state
    await sio.emit("queue_updated", {"room_id": room}, room=room)
    await sio.emit("ctrl", {"action": "stop"}, room=room)
    
    # Auto-play next setelah 5 detik
    async def delayed_play():
        import asyncio as aio
        await aio.sleep(5)
        
        async with async_session() as s2:
            r = await s2.execute(
                select(QueueItem)
                .where(QueueItem.room_id == room, QueueItem.status == "waiting")
                .order_by(QueueItem.priority.desc(), QueueItem.created_at.asc())
                .limit(1)
            )
            nxt = r.scalar_one_or_none()
            
            if nxt:
                # Update status
                await s2.execute(
                    update(QueueItem)
                    .where(QueueItem.id == nxt.id)
                    .values(status="playing", played_at=datetime.utcnow())
                )
                await s2.execute(
                    update(Song)
                    .where(Song.id == nxt.song_id)
                    .values(play_count=Song.play_count + 1)
                )
                await s2.commit()
                
                # Emit play event ke player
                await sio.emit("play", {
                    "song_id": nxt.song_id,
                    "queue_id": nxt.id,
                    "auto_play": True
                }, room=room)
                await sio.emit("queue_updated", {"room_id": room}, room=room)
            else:
                # Queue kosong - kirim event idle
                await sio.emit("queue_empty", {
                    "room_id": room,
                    "message": "Antrian kosong, silakan tambah lagu"
                }, room=room)
    
    import asyncio as aio
    aio.create_task(delayed_play())

@sio.event
async def set_volume(sid, data):
    await sio.emit("vol", {"volume": data.get("volume", 80)}, room=data.get("room_id", "KARAOKE BPF SBY"))
@sio.event
async def join_room(sid, data):
    await sio.enter_room(sid, data.get("room_id", "KARAOKE BPF SBY"))
@sio.event
async def toggle_vocal(sid, data):
    await sio.emit("vocal", {"channel": data.get("channel", "stereo")}, room=data.get("room_id", "KARAOKE BPF SBY"))

# ============================================
# DB DEPENDENCY
# ============================================
async def get_db():
    async with async_session() as s:
        try: yield s
        finally: await s.close()

# ============================================
# CORE API ENDPOINTS
# ============================================
@app.get("/api/health")
async def health(): return {"status": "ok", "conns": len(active), "ts": datetime.utcnow().isoformat()}

@app.post("/api/auth/login")
async def login(req: LoginRequest, db=Depends(get_db)):
    r = await db.execute(select(User).where(User.username == req.username, User.is_active == True))
    u = r.scalar_one_or_none()
    if not u or not verify_password(req.password, u.password_hash): raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_access_token({"sub": u.username, "role": u.role}), "token_type": "bearer", "user": {"username": u.username, "role": u.role}}

@app.get("/api/songs", response_model=List[SR])
async def get_songs(search: Optional[str] = Query(None), genre: Optional[str] = Query(None), limit: int = Query(250), offset: int = Query(0), db=Depends(get_db)):
    q = select(Song).where(Song.is_active == True)
    if search: q = q.where(or_(Song.title.ilike(f"%{search}%"), Song.artist.ilike(f"%{search}%")))
    if genre: q = q.where(Song.genre == genre)
    return (await db.execute(q.order_by(Song.title).offset(offset).limit(limit))).scalars().all()

@app.put("/api/songs/{song_id}")
async def update_song(song_id: int, req: SongUpdate, db=Depends(get_db)):
    r = await db.execute(select(Song).where(Song.id == song_id, Song.is_active == True))
    if not (song := r.scalar_one_or_none()): raise HTTPException(404, "Not found")
    song.title = req.title; song.artist = req.artist; song.genre = req.genre; await db.commit(); return {"ok": True}

@app.delete("/api/songs/{song_id}")
async def delete_song(song_id: int, db=Depends(get_db)):
    r = await db.execute(select(Song).where(Song.id == song_id))
    if not (song := r.scalar_one_or_none()): raise HTTPException(404, "Not found")
    song.is_active = False; await db.commit(); return {"ok": True}

@app.get("/api/songs/genres")
async def genres(db=Depends(get_db)):
    r = await db.execute(select(Song.genre, func.count(Song.id)).where(Song.is_active == True, Song.genre.isnot(None)).group_by(Song.genre).order_by(func.count(Song.id).desc()))
    return [{"genre": row[0], "count": row[1]} for row in r]

@app.get("/api/media/stream/{song_id}")
async def stream_song(song_id: int, db=Depends(get_db)):
    r = await db.execute(select(Song).where(Song.id == song_id))
    if not (song := r.scalar_one_or_none()): raise HTTPException(404, "Not found")
    fp = Path(song.file_path)
    if not fp.exists(): fp = mp / fp.name
    if not fp.exists(): raise HTTPException(404, "File not found")
    return FileResponse(fp, media_type="video/mp4", headers={"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=3600"})

@app.post("/api/queue")
async def add_queue(req: QR, db=Depends(get_db)):
    sg = (await db.execute(select(Song).where(Song.id == req.song_id))).scalar_one_or_none()
    if not sg: raise HTTPException(404, "Song not found")
    qi = QueueItem(song_id=req.song_id, room_id=req.room_id, requester_name=req.requester_name)
    db.add(qi); await db.commit(); await db.refresh(qi)
    await sio.emit("queue_updated", {"room_id": req.room_id}, room=req.room_id)
    return QResp(id=qi.id, song_id=qi.song_id, room_id=qi.room_id, status=qi.status, priority=qi.priority, created_at=qi.created_at, song=SR.model_validate(sg))

@app.get("/api/queue/{room_id}")
async def get_queue(room_id: str = "KARAOKE BPF SBY", db=Depends(get_db)):
    items = (await db.execute(select(QueueItem).where(QueueItem.room_id == room_id, QueueItem.status == "waiting").order_by(QueueItem.created_at))).scalars().all()
    out = []
    for i in items:
        sg = (await db.execute(select(Song).where(Song.id == i.song_id))).scalar_one_or_none()
        out.append(QResp(id=i.id, song_id=i.song_id, room_id=i.room_id, status=i.status, priority=i.priority, created_at=i.created_at, song=SR.model_validate(sg) if sg else None))
    return out

@app.delete("/api/queue/{queue_id}")
async def del_queue(queue_id: int, room_id: str = Query("KARAOKE BPF SBY"), db=Depends(get_db)):
    r = await db.execute(update(QueueItem).where(QueueItem.id == queue_id, QueueItem.room_id == room_id).values(status="skipped", completed_at=datetime.utcnow()))
    if r.rowcount == 0: raise HTTPException(404, "Not found")
    await db.commit(); await sio.emit("queue_updated", {"room_id": room_id}, room=room_id); return {"ok": True}



@app.get("/api/rooms/active")
async def get_active_rooms(db=Depends(get_db)):
    """Get rooms with active queues"""
    # Get distinct room_ids from queue
    r = await db.execute(
        select(QueueItem.room_id, func.count(QueueItem.id))
        .where(QueueItem.status == "waiting")
        .group_by(QueueItem.room_id)
    )
    active_queues = {row[0]: row[1] for row in r}
    
    # Get all rooms
    r2 = await db.execute(select(Room).where(Room.is_active == True).order_by(Room.name))
    rooms = r2.scalars().all()
    
    result = []
    for room in rooms:
        result.append({
            "id": room.id,
            "name": room.name,
            "description": room.description,
            "capacity": room.capacity,
            "is_active": room.is_active,
            "queue_count": active_queues.get(room.name, 0),
            "is_busy": active_queues.get(room.name, 0) > 0
        })
    
    return {"rooms": result, "total": len(result)}


# ============================================
# ROOM MANAGEMENT ENDPOINTS
# ============================================

@app.get("/api/rooms", response_model=List[RoomResponse])
async def get_rooms(db=Depends(get_db)):
    """Get all rooms"""
    r = await db.execute(select(Room).order_by(Room.name))
    return r.scalars().all()

@app.post("/api/rooms")
async def create_room(req: RoomCreate, db=Depends(get_db)):
    """Create new room"""
    existing = (await db.execute(select(Room).where(Room.name == req.name))).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Room already exists")
    room = Room(name=req.name, description=req.description, capacity=req.capacity)
    db.add(room); await db.commit(); await db.refresh(room)
    return RoomResponse.model_validate(room)

@app.put("/api/rooms/{room_id}")
async def update_room(room_id: int, req: RoomCreate, db=Depends(get_db)):
    """Update room"""
    r = await db.execute(select(Room).where(Room.id == room_id))
    room = r.scalar_one_or_none()
    if not room: raise HTTPException(404, "Room not found")
    room.name = req.name; room.description = req.description; room.capacity = req.capacity
    await db.commit()
    return RoomResponse.model_validate(room)

@app.delete("/api/rooms/{room_id}")
async def delete_room(room_id: int, db=Depends(get_db)):
    """Delete room (soft delete)"""
    r = await db.execute(select(Room).where(Room.id == room_id))
    room = r.scalar_one_or_none()
    if not room: raise HTTPException(404, "Room not found")
    room.is_active = False; await db.commit()
    return {"ok": True}



# ============================================
# GENRE MANAGEMENT ENDPOINTS (AI + Dynamic)
# ============================================

@app.get("/api/genres")
async def get_genres(db=Depends(get_db)):
    """
    Get dynamic genre list dari database (SELECT DISTINCT)
    Genre list tumbuh otomatis tanpa hardcode
    """
    r = await db.execute(
        select(Song.genre, func.count(Song.id))
        .where(Song.is_active == True, Song.genre.isnot(None), Song.genre != 'Unknown')
        .group_by(Song.genre)
        .order_by(func.count(Song.id).desc())
    )
    
    genres = []
    for row in r:
        genres.append({
            'genre': row[0],
            'count': row[1],
            'is_custom': True  # Semua genre dari DB adalah dynamic
        })
    
    # Tambahkan genre defaults jika belum ada di DB
    default_genres = [
        'Pop Indonesia', 'Dangdut', 'K-Pop', 'Barat', 'Rock',
        'Mandarin', 'Anak', 'Religi', 'Daerah', 'Jazz', 'EDM', 'Hip Hop'
    ]
    
    existing_genres = {g['genre'] for g in genres}
    for dg in default_genres:
        if dg not in existing_genres:
            genres.append({
                'genre': dg,
                'count': 0,
                'is_custom': False
            })
    
    return {
        'genres': sorted(genres, key=lambda x: x['count'], reverse=True),
        'total': len(genres),
        'message': 'Genre list diambil secara dinamis dari database'
    }

@app.post("/api/admin/songs/bulk-genre")
async def bulk_update_genre(
    song_ids: List[int],
    genre: str = Query(..., min_length=1, max_length=100),
    db=Depends(get_db)
):
    """
    Bulk update genre untuk multiple songs sekaligus
    Body: [1, 2, 3, ...]
    Query: ?genre=Pop+Indonesia
    """
    if not song_ids:
        raise HTTPException(400, "No song IDs provided")
    
    if len(song_ids) > 500:
        raise HTTPException(400, "Maximum 500 songs per bulk operation")
    
    # Update all songs in one query
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

@app.post("/api/admin/songs/auto-genre")
async def auto_detect_genres(
    db=Depends(get_db),
    limit: int = Query(100, le=500)
):
    """
    Auto-detect genre menggunakan AI untuk lagu-lagu yang belum bergenre
    """
    from services.genre_detector import genre_detector
    
    # Ambil lagu dengan genre None atau Unknown
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
            # Auto-assign dengan confidence tinggi
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
            # Set ke Unknown untuk review manual
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

@app.get("/api/admin/genre-detector/stats")
async def get_genre_detector_stats():
    """Get genre detector statistics"""
    from services.genre_detector import genre_detector
    return genre_detector.get_stats()

@app.post("/api/admin/genre-detector/add-keyword")
async def add_genre_keyword(genre: str, keyword: str):
    """Add keyword to genre detector"""
    from services.genre_detector import genre_detector
    success = genre_detector.add_keyword(genre, keyword)
    return {
        'success': success,
        'genre': genre,
        'keyword': keyword,
        'message': 'Keyword added' if success else 'Keyword already exists'
    }


# ============================================
# ADMIN ENDPOINTS
# ============================================


@app.post("/api/rooms/{room_name}/clear-queue")
async def clear_room_queue(room_name: str, db=Depends(get_db)):
    """Clear all waiting queue for a room"""
    result = await db.execute(
        update(QueueItem)
        .where(QueueItem.room_id == room_name, QueueItem.status == "waiting")
        .values(status="skipped", completed_at=datetime.utcnow())
    )
    await db.commit()
    
    await sio.emit("queue_updated", {"room_id": room_name}, room=room_name)
    await sio.emit("queue_empty", {"room_id": room_name, "message": "Queue dibersihkan oleh admin"}, room=room_name)
    
    return {"message": f"Queue for room '{room_name}' cleared", "affected": result.rowcount}

@app.post("/api/admin/songs/scan")
async def scan(path: Optional[str] = Query(None), db=Depends(get_db)):
    sp = Path(path) if path else mp
    if not sp.exists(): raise HTTPException(404, "Path not found")
    ext, n = {".mp4", ".mkv", ".avi", ".webm", ".mov"}, 0
    for f in sp.rglob("*"):
        if f.suffix.lower() not in ext: continue
        ex = (await db.execute(select(Song).where(Song.file_path == str(f)))).scalar_one_or_none()
        if ex:
            if not ex.is_active: ex.is_active = True; ex.updated_at = datetime.utcnow(); n += 1
            continue
        nm, art, tit = f.stem, None, f.stem
        if " - " in nm: p = nm.split(" - ", 1); art = p[0].strip(); tit = p[1].strip()
        # Auto-detect genre dengan AI
        # Auto-detect genre with AI
        predicted_genre = 'Unknown'
        try:
            from services.genre_detector import genre_detector
            prediction = genre_detector.predict_genre(artist=art, title=tit)
            predicted_genre = prediction['genre'] if prediction['confidence'] > 0.8 else 'Unknown'
        except:
            pass
        db.add(Song(title=tit, artist=art, genre=predicted_genre, file_path=str(f), file_format=f.suffix.lower().replace(".", ""), is_active=True))
    await db.commit(); return {"message": f"{n} new songs added", "new_songs": n}

@app.get("/api/admin/stats")
async def stats(db=Depends(get_db)):
    ts = (await db.execute(select(func.count(Song.id)).where(Song.is_active == True))).scalar() or 0
    tp = (await db.execute(select(func.sum(Song.play_count)))).scalar() or 0
    qt = (await db.execute(select(func.count(QueueItem.id)).where(func.date(QueueItem.created_at) == datetime.utcnow().date()))).scalar() or 0
    return {"total_songs": ts, "total_plays": int(tp), "queue_today": qt, "active_connections": len(active), "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/admin/minio/stats")
async def minio_stats():
    try: from services.minio_client import minio_client; return minio_client.get_stats()
    except Exception as e: return {"available": False, "error": str(e)}

# ============================================
# INCLUDE ROUTERS (SEBELUM socket_app!)
# ============================================
try:
    from ai_routes import router as ai_router
    app.include_router(ai_router); print("✅ AI routes loaded")
except Exception as e: print(f"⚠️ AI routes: {e}")

try:
    from auth_routes import router as auth_router
    app.include_router(auth_router); print("✅ Auth routes loaded")
except Exception as e: print(f"⚠️ Auth routes: {e}")


# ============================================
# GENRE MANAGEMENT ENDPOINTS
# ============================================

@app.get("/api/genres/list")
async def list_all_genres(db=Depends(get_db)):
    """Get all unique genres with song count"""
    r = await db.execute(
        select(Song.genre, func.count(Song.id))
        .where(Song.is_active == True, Song.genre.isnot(None), Song.genre != '')
        .group_by(Song.genre)
        .order_by(func.count(Song.id).desc())
    )
    genres = [{"name": row[0], "count": row[1]} for row in r]
    return {"genres": genres, "total": len(genres)}

@app.post("/api/genres/detect")
async def auto_detect_genres(db=Depends(get_db)):
    """Auto-detect genre for songs without genre using keyword matching"""
    
    # Genre keyword mapping
    genre_keywords = {
        "Pop Indonesia": ["pop", "indonesia", "cinta", "hati", "rindu", "sayang"],
        "Dangdut": ["dangdut", "koplo", "jaran", "goyang"],
        "Rock": ["rock", "metal", "punk", "gitar", "band"],
        "K-Pop": ["k-pop", "kpop", "korea", "bts", "blackpink", "exo"],
        "Barat": ["west", "english", "love", "you", "baby", "night", "dream"],
        "Mandarin": ["mandarin", "chinese", "cina", "tiongkok"],
        "Anak": ["anak", "kids", "child", "balita", "tk"],
        "Religi": ["religi", "islam", "sholawat", "quran", "rohani", "gereja"],
        "Daerah": ["daerah", "jawa", "sunda", "batak", "minang"],
        "Akustik": ["akustik", "acoustic", "unplugged"],
        "Ballad": ["ballad", "slow", "mellow"],
        "Jazz": ["jazz", "blues", "swing"],
        "EDM": ["edm", "dj", "remix", "electronic", "dance"],
        "Hip Hop": ["hip hop", "hiphop", "rap", "trap"],
    }
    
    # Get songs without genre
    r = await db.execute(
        select(Song).where(
            Song.is_active == True,
            or_(Song.genre.is_(None), Song.genre == '')
        )
    )
    songs = r.scalars().all()
    
    updated = 0
    for song in songs:
        title_lower = (song.title or '').lower()
        artist_lower = (song.artist or '').lower()
        combined = f"{title_lower} {artist_lower}"
        
        for genre, keywords in genre_keywords.items():
            if any(kw in combined for kw in keywords):
                song.genre = genre
                updated += 1
                break
    
    await db.commit()
    
    return {
        "message": f"Auto-detected genre for {updated} songs",
        "total_scanned": len(songs),
        "updated": updated
    }

@app.post("/api/songs/batch-genre")
async def batch_update_genre(req: dict, db=Depends(get_db)):
    """Batch update genre for multiple songs"""
    song_ids = req.get("song_ids", [])
    genre = req.get("genre", "")
    
    if not song_ids or not genre:
        raise HTTPException(400, "song_ids and genre required")
    
    await db.execute(
        update(Song)
        .where(Song.id.in_(song_ids))
        .values(genre=genre, updated_at=datetime.utcnow())
    )
    await db.commit()
    
    return {"message": f"Updated genre to '{genre}' for {len(song_ids)} songs"}


# ============================================
# SOCKET.IO WRAPPER
# ============================================
socket_app = socketio.ASGIApp(sio, app)

# ============================================
# STARTUP
# ============================================


# ============================================
# ONLINE GENRE DETECTION ENDPOINTS
# ============================================

@app.post("/api/genres/detect-online")
async def detect_genre_online(song_id: int, db=Depends(get_db)):
    """Detect genre for a single song using online APIs"""
    from services.genre_detector import genre_detector
    
    r = await db.execute(select(Song).where(Song.id == song_id))
    song = r.scalar_one_or_none()
    if not song:
        raise HTTPException(404, "Song not found")
    
    result = await genre_detector.detect_genre_online(song.title, song.artist)
    
    if result and result.get('genre'):
        song.genre = result['genre']
        song.updated_at = datetime.utcnow()
        await db.commit()
    
    return {
        "song_id": song_id,
        "title": song.title,
        "artist": song.artist,
        "detected_genre": result.get('genre', 'Unknown'),
        "confidence": result.get('confidence', 0),
        "source": result.get('source', 'unknown'),
        "tags": result.get('tags', [])
    }

@app.post("/api/genres/detect-online-batch")
async def detect_genre_batch_online(limit: int = Query(50, le=200), db=Depends(get_db)):
    """Detect genre for multiple songs without genre using online APIs"""
    from services.genre_detector import genre_detector
    
    # Get songs without genre
    r = await db.execute(
        select(Song)
        .where(
            Song.is_active == True,
            or_(Song.genre.is_(None), Song.genre == '')
        )
        .limit(limit)
    )
    songs = r.scalars().all()
    
    songs_data = [{"id": s.id, "title": s.title, "artist": s.artist} for s in songs]
    
    # Run batch detection
    results = []
    for song_data in songs_data:
        try:
            genre_info = await genre_detector.detect_genre_online(
                song_data['title'],
                song_data.get('artist')
            )
            
            if genre_info.get('genre') and genre_info.get('confidence', 0) > 0.3:
                # Update database
                await db.execute(
                    update(Song)
                    .where(Song.id == song_data['id'])
                    .values(genre=genre_info['genre'], updated_at=datetime.utcnow())
                )
                results.append({
                    "song_id": song_data['id'],
                    "title": song_data['title'],
                    "detected_genre": genre_info['genre'],
                    "confidence": genre_info['confidence']
                })
            
            # Rate limit protection
            await asyncio.sleep(0.5)
            
        except Exception as e:
            results.append({
                "song_id": song_data['id'],
                "error": str(e)
            })
    
    await db.commit()
    
    return {
        "message": f"Detected genre for {len(results)} songs",
        "total_scanned": len(songs_data),
        "detected": len(results),
        "results": results
    }

@app.get("/api/genres/detector-stats")
async def detector_stats():
    """Get genre detector statistics"""
    from services.genre_detector import genre_detector
    return genre_detector.get_stats()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        for ud in [
            {"username": settings.admin_user, "password_hash": get_password_hash(settings.admin_password), "role": "admin", "is_active": True},
            {"username": "operator", "password_hash": get_password_hash("operator123"), "role": "operator", "is_active": True}
        ]:
            await session.execute(pg_insert(User).values(**ud).on_conflict_do_nothing(index_elements=["username"]))
        await session.commit()
    print("  BPF KARAOKE BACKEND READY!")
