"""
BPF Karaoke System - Backend API v3.1 (Production)
PT BESTPROFIT FUTURES SURABAYA

Refactored architecture:
  - database.py  : engine, session, Base
  - models.py    : SQLAlchemy models
  - schemas.py   : Pydantic schemas
  - sio.py       : Socket.IO server & real-time events
  - routers/     : endpoint modules (auth, ai, songs, queue, rooms, ...)
"""
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.dialects.postgresql import insert as pg_insert
import socketio

from database import engine, async_session, Base
from models import User
from security import hash_password
from sio import sio, active, start_stuck_watchdog

from routers.auth import router as auth_router
from routers.ai import router as ai_router
from routers.songs import router as songs_router
from routers.media import router as media_router
from routers.queue import router as queue_router
from routers.rooms import router as rooms_router
from routers.history import router as history_router
from routers.genres import router as genres_router
from routers.admin import router as admin_router
from routers.tasks import router as tasks_router
from routers.youtube import router as youtube_router

# ============================================
# APP & MIDDLEWARE
# ============================================
app = FastAPI(title="BPF Karaoke", version="3.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# STATIC MEDIA MOUNT
# ============================================
MEDIA_PATH = os.getenv("MEDIA_PATH", "/media/lagu")
mp = Path(MEDIA_PATH)
mp.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(mp)), name="media")

# ============================================
# ROUTERS
# ============================================
for _r in [
    auth_router, ai_router, songs_router, media_router, queue_router,
    rooms_router, history_router, genres_router, admin_router, tasks_router,
    youtube_router,
]:
    app.include_router(_r)

# ============================================
# HEALTH CHECK
# ============================================
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "conns": len(active),
        "ts": datetime.utcnow().isoformat(),
    }


# ============================================
# SOCKET.IO WRAPPER
# ============================================
socket_app = socketio.ASGIApp(sio, app)

# ============================================
# STARTUP
# ============================================
@app.on_event("startup")
async def startup():
    # Inisialisasi tabel (fallback idempotent; sumber kebenaran skema:
    # alembic migrations di backend/migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    async with async_session() as session:
        seeds = []
        # Hanya seed admin jika ADMIN_PASSWORD di-set (fail-safe, tanpa default insecure)
        if admin_password:
            seeds.append({
                "username": admin_user,
                "password_hash": hash_password(admin_password),
                "role": "admin",
                "is_active": True,
                "requires_password_change": True,  # ISO 27001: force change on first login
                "last_password_change": datetime.utcnow(),
            })
        seeds.append({
            "username": "operator",
            "password_hash": hash_password("operator123"),
            "role": "operator",
            "is_active": True,
        })
        for ud in seeds:
            await session.execute(
                pg_insert(User).values(**ud).on_conflict_do_nothing(index_elements=["username"])
            )
        await session.commit()

    # Watchdog anti-nyangkut: item 'playing' tanpa progress (player mati /
    # event hilang) otomatis di-skip agar antrian tidak menggantung selamanya.
    await start_stuck_watchdog()

    print("  BPF KARAOKE BACKEND READY!")
