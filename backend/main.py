"""
BPF Karaoke System - Backend API v2.0 (Fixed)
"""
import asyncio, os, json, hashlib, secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, ForeignKey,
    select, update, delete, func, or_, inspect
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from jose import jwt
import socketio

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://karaoke_admin:K4r40k3S3cur3P4ss!2024@karaoke_db:5432/karaoke_db"
    jwt_secret: str = "K4r40k3JWTS3cr3tK3yV3ryL0ngStr1ng2024!@#$"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 1440
    admin_user: str = "admin"
    admin_password: str = "AdminK4r40k3!2024"
    media_path: str = "/media/lagu"
    cors_origins: str = "*"
    class Config:
        env_file = ".env"

settings = Settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

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
    room_id = mapped_column(String(50), nullable=False, index=True)
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

class LoginRequest(BaseModel):
    username: str
    password: str

def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${h}"

def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, h = hashed.split("$", 1)
        return hashlib.sha256(f"{salt}{plain}".encode()).hexdigest() == h
    except:
        return False

def create_access_token(data: dict, exp: Optional[timedelta] = None) -> str:
    d = data.copy()
    d["exp"] = datetime.utcnow() + (exp or timedelta(minutes=settings.jwt_expiration))
    return jwt.encode(d, settings.jwt_secret, algorithm=settings.jwt_algorithm)

app = FastAPI(title="BPF Karaoke", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

mp = Path(settings.media_path)
mp.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(mp)), name="media")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", logger=False, engineio_logger=False)
active: Dict[str, Any] = {}

@sio.event
async def connect(sid, environ):
    active[sid] = {"sid": sid, "type": "unknown", "room": "default"}

@sio.event
async def disconnect(sid):
    active.pop(sid, None)

@sio.event
async def register(sid, data):
    if sid in active:
        active[sid].update({"type": data.get("type", "unknown"), "room": data.get("room_id", "default")})
    await sio.emit("ok", {"type": data.get("type")}, to=sid)

@sio.event
async def play_song(sid, data):
    sid_q, rid = data.get("queue_id"), data.get("room_id", "default")
    async with async_session() as s:
        if sid_q:
            await s.execute(update(QueueItem).where(QueueItem.id == sid_q).values(status="playing", played_at=datetime.utcnow()))
        await s.execute(update(Song).where(Song.id == data.get("song_id")).values(play_count=Song.play_count + 1))
        await s.commit()
    await sio.emit("play", {"song_id": data.get("song_id"), "queue_id": sid_q})

@sio.event
async def pause_song(sid, data):
    await sio.emit("ctrl", {"action": "pause"})

@sio.event
async def resume_song(sid, data):
    await sio.emit("ctrl", {"action": "resume"})

@sio.event
async def skip_song(sid, data):
    async with async_session() as s:
        if data.get("queue_id"):
            await s.execute(update(QueueItem).where(QueueItem.id == data["queue_id"]).values(status="skipped", completed_at=datetime.utcnow()))
            await s.commit()
    await sio.emit("ctrl", {"action": "skip"})

@sio.event
async def set_volume(sid, data):
    await sio.emit("vol", {"volume": data.get("volume", 80)})

@sio.event
async def join_room(sid, data):
    sio.enter_room(sid, f"{data.get('type','operator')}-{data.get('room_id','default')}")

@sio.event
async def toggle_vocal(sid, data):
    await sio.emit("vocal", {"channel": data.get("channel", "stereo")})

socket_app = socketio.ASGIApp(sio, app)

async def get_db():
    async with async_session() as s:
        try:
            yield s
        finally:
            await s.close()

class SR(BaseModel):
    id: int; title: str; artist: Optional[str] = None; genre: Optional[str] = None
    file_path: str; play_count: int = 0; is_active: bool = True
    class Config: from_attributes = True

@app.get("/api/health")
async def health():
    return {"status": "ok", "conns": len(active), "ts": datetime.utcnow().isoformat()}

@app.post("/api/auth/login")
async def login(req: LoginRequest, db=Depends(get_db)):
    r = await db.execute(select(User).where(User.username == req.username, User.is_active == True))
    u = r.scalar_one_or_none()
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_access_token({"sub": u.username, "role": u.role}), "user": {"username": u.username, "role": u.role}}

@app.get("/api/songs")
async def get_songs(search: Optional[str] = Query(None), genre: Optional[str] = Query(None),
                    limit: int = Query(50, le=200), offset: int = Query(0), db=Depends(get_db)):
    q = select(Song).where(Song.is_active == True)
    if search: q = q.where(or_(Song.title.ilike(f"%{search}%"), Song.artist.ilike(f"%{search}%")))
    if genre: q = q.where(Song.genre == genre)
    r = await db.execute(q.order_by(Song.title).offset(offset).limit(limit))
    return r.scalars().all()

@app.get("/api/songs/genres")
async def genres(db=Depends(get_db)):
    r = await db.execute(select(Song.genre, func.count(Song.id)).where(Song.is_active == True, Song.genre.isnot(None)).group_by(Song.genre).order_by(func.count(Song.id).desc()))
    return [{"genre": row[0], "count": row[1]} for row in r]

@app.get("/api/songs/popular")
async def popular(limit: int = Query(20, le=100), db=Depends(get_db)):
    r = await db.execute(select(Song).where(Song.is_active == True).order_by(Song.play_count.desc()).limit(limit))
    return r.scalars().all()

class QR(BaseModel):
    song_id: int; room_id: str = "default"; requester_name: Optional[str] = None

class QResp(BaseModel):
    id: int; song_id: int; room_id: str; status: str; priority: int; created_at: datetime; song: Optional[SR] = None
    class Config: from_attributes = True

@app.post("/api/queue")
async def add_queue(req: QR, db=Depends(get_db)):
    sg = (await db.execute(select(Song).where(Song.id == req.song_id))).scalar_one_or_none()
    if not sg: raise HTTPException(404, "Song not found")
    qi = QueueItem(song_id=req.song_id, room_id=req.room_id, requester_name=req.requester_name)
    db.add(qi); await db.commit(); await db.refresh(qi)
    return QResp(id=qi.id, song_id=qi.song_id, room_id=qi.room_id, status=qi.status, priority=qi.priority, created_at=qi.created_at, song=SR.model_validate(sg))

@app.get("/api/queue/{room_id}")
async def get_queue(room_id: str = "default", db=Depends(get_db)):
    items = (await db.execute(select(QueueItem).where(QueueItem.room_id == room_id).order_by(QueueItem.created_at))).scalars().all()
    out = []
    for i in items:
        sg = (await db.execute(select(Song).where(Song.id == i.song_id))).scalar_one_or_none()
        out.append(QResp(id=i.id, song_id=i.song_id, room_id=i.room_id, status=i.status, priority=i.priority, created_at=i.created_at, song=SR.model_validate(sg) if sg else None))
    return out

@app.delete("/api/queue/{queue_id}")
async def del_queue(queue_id: int, room_id: str = Query("default"), db=Depends(get_db)):
    r = await db.execute(update(QueueItem).where(QueueItem.id == queue_id, QueueItem.room_id == room_id).values(status="skipped", completed_at=datetime.utcnow()))
    if r.rowcount == 0: raise HTTPException(404, "Not found")
    await db.commit()
    return {"ok": True}

@app.post("/api/admin/songs/scan")
async def scan(path: Optional[str] = Query(None), db=Depends(get_db)):
    sp = Path(path) if path else mp
    if not sp.exists(): raise HTTPException(404, "Path not found")
    ext = {".mp4", ".mkv", ".avi", ".webm", ".mov"}
    n = 0
    for f in sp.rglob("*"):
        if f.suffix.lower() not in ext: continue
        if (await db.execute(select(Song).where(Song.file_path == str(f)))).scalar_one_or_none(): continue
        nm = f.stem; art = None; tit = nm
        if " - " in nm: p = nm.split(" - ", 1); art = p[0].strip(); tit = p[1].strip()
        db.add(Song(title=tit, artist=art, file_path=str(f), file_format=f.suffix.lower().replace(".", ""), is_active=True))
        n += 1
    await db.commit()
    return {"message": f"{n} new songs added", "new_songs": n}

@app.get("/api/admin/stats")
async def stats(db=Depends(get_db)):
    ts = (await db.execute(select(func.count(Song.id)).where(Song.is_active == True))).scalar() or 0
    tp = (await db.execute(select(func.sum(Song.play_count)))).scalar() or 0
    tdy = datetime.utcnow().date()
    qt = (await db.execute(select(func.count(QueueItem.id)).where(func.date(QueueItem.created_at) == tdy))).scalar() or 0
    return {"total_songs": ts, "total_plays": int(tp), "queue_today": qt, "active_connections": len(active), "timestamp": datetime.utcnow().isoformat()}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for user_data in [
            {"username": settings.admin_user, "password_hash": get_password_hash(settings.admin_password), "role": "admin", "is_active": True},
            {"username": "operator", "password_hash": get_password_hash("operator123"), "role": "operator", "is_active": True}
        ]:
            stmt = pg_insert(User).values(**user_data).on_conflict_do_nothing(index_elements=["username"])
            await session.execute(stmt)
        await session.commit()
    print("  BPF KARAOKE BACKEND READY!")
