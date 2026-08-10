"""
Konfigurasi test integrasi realtime BPF Karaoke.

Test ini adalah INTEGRATION test yang berjalan terhadap backend yang sedang
berjalan (default http://localhost:5000, bisa di-override dengan env
KARAOKE_TEST_BASE_URL). Akun admin test dibuat sementara di database
(menggunakan modul backend langsung, jadi test ini dijalankan di dalam
container backend, mis. `docker exec karaoke_backend pytest /app/tests`),
lalu dibersihkan setelah selesai. Room test dibuat dan dihapus per test.
"""
import asyncio
import os
import sys
import threading
import time
import uuid

import bcrypt
import httpx
import pytest
import socketio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.getenv("KARAOKE_TEST_BASE_URL", "http://localhost:5000")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


# Satu event loop khusus di thread background untuk SEMUA operasi DB.
# Penting: asyncpg mengikat koneksi ke event loop tempat ia dibuat; memakai
# asyncio.run() berulang (loop baru tiap kali) akan memicu error
# "attached to a different loop" / "another operation is in progress".
_db_loop = asyncio.new_event_loop()
_loop_thread = threading.Thread(target=_db_loop.run_forever, daemon=True)
_loop_thread.start()


def _run(coro):
    """Jalankan coroutine DB pada loop khusus (thread-safe)."""
    fut = asyncio.run_coroutine_threadsafe(coro, _db_loop)
    return fut.result(timeout=30)


@pytest.fixture(scope="session")
def admin(base_url):
    """Buat akun admin test sementara di DB, kembalikan token, hapus setelah selesai."""
    from database import async_session
    from models import User
    from sqlalchemy import delete, select

    username = "testadmin_" + uuid.uuid4().hex[:8]
    password = "TestPass!2024xyz"

    async def _create():
        async with async_session() as s:
            u = User(username=username, role="admin", is_active=True,
                     password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                     requires_password_change=False, failed_login_attempts=0)
            s.add(u)
            await s.commit()
    _run(_create())

    login = httpx.post(f"{base_url}/api/auth/login",
                       json={"username": username, "password": password}, timeout=10)
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    yield {"username": username, "token": token, "headers": {"Authorization": f"Bearer {token}"}}

    async def _clean():
        async with async_session() as s:
            await s.execute(delete(User).where(User.username == username))
            await s.commit()
    _run(_clean())


@pytest.fixture
def room(base_url, admin):
    """Room test terisolasi per test; di-HARD-DELETE beserta data terkait setelahnya."""
    from database import async_session
    from models import QueueItem, PlaybackHistory, Room, RoomSession
    from revision_store import clear_queue_revision
    from sqlalchemy import delete, select

    name = "TEST-" + uuid.uuid4().hex[:8]
    r = httpx.post(f"{base_url}/api/rooms",
                   json={"name": name, "description": "pytest room", "capacity": 5},
                   headers=admin["headers"], timeout=10)
    assert r.status_code == 200, r.text
    room_id = r.json()["id"]

    yield {"name": name, "id": room_id}

    async def _clean():
        async with async_session() as s:
            await s.execute(delete(RoomSession).where(RoomSession.room_id == room_id))
            await s.execute(delete(QueueItem).where(QueueItem.room_id == name))
            await s.execute(delete(PlaybackHistory).where(PlaybackHistory.room_id == name))
            await s.execute(delete(Room).where(Room.id == room_id))
            await s.commit()
        await clear_queue_revision(name)
    _run(_clean())


def make_client(base_url, room_name):
    """Buat socket.io client yang terdaftar di room, beserta buffer event-nya."""
    events = {
        "queue_updated": [], "play": [], "ctrl": [], "vol": [], "vocal": [],
        "key_change": [], "room_session": [], "queue_empty": [], "ok": [],
        "playback_progress": [],
    }
    c = socketio.Client(reconnection=False)
    for name in events:
        def make_h(nm):
            def h(data):
                events[nm].append(data)
            return h
        c.on(name, make_h(name))
    ws = base_url.replace("http://", "ws://").replace("https://", "wss://") + "/socket.io"
    c.connect(ws, transports=["websocket"], wait_timeout=10)
    c.emit("register", {"type": "test", "room_id": room_name})
    c.emit("join_room", {"type": "test", "room_id": room_name})
    return c, events


def wait_until(events, name, count=1, timeout=6.0):
    """Tunggu hingga `count` event `name` terkumpul di buffer, atau timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(events[name]) >= count:
            return True
        time.sleep(0.2)
    return len(events[name]) >= count
