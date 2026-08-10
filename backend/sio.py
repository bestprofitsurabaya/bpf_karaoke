"""
Socket.IO Server & Real-time Events
PT BESTPROFIT FUTURES SURABAYA
"""
import asyncio
import os
import time as _time
from datetime import datetime
from typing import Dict, Any

import socketio
from sqlalchemy import select, update

from database import async_session
from models import QueueItem, Song, PlaybackHistory
from revision_store import (
    bump_queue_revision,
    get_queue_revision,
    check_and_bump_queue_revision,
)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", logger=False, engineio_logger=False)
active: Dict[str, Any] = {}
# State pitch/key shift per room (semitone) agar sync lintas klien
room_key_shifts: Dict[str, int] = {}

# ============================================================
# Anti-nyangkut: heartbeat progress & watchdog item 'playing'
# ============================================================
# Item berstatus 'playing' yang TIDAK menerima heartbeat playback_progress
# lebih dari batas ini (player mati/crash/event hilang) dianggap macet dan
# di-skip otomatis oleh watchdog (startup backend) agar antrian tidak
# menggantung selamanya. Default 20 menit (lagu maks ~10 mnt + toleransi
# pause lama). Atur via env STUCK_NO_PROGRESS_SEC.
STUCK_NO_PROGRESS_SEC = int(os.getenv("STUCK_NO_PROGRESS_SEC", "1200"))
WATCHDOG_INTERVAL_SEC = 60

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        from redis.asyncio import Redis

        _redis_client = Redis.from_url(
            os.getenv("REDIS_URL", "redis://karaoke_redis:6379/0"),
            decode_responses=True,
        )
    return _redis_client


def _progress_key(room: str) -> str:
    return f"karaoke:room_progress:{room}"


def _paused_key(room: str) -> str:
    return f"karaoke:room_paused:{room}"


def _stop_after_key(room: str) -> str:
    """Flag 'berhenti setelah lagu ini selesai' — dipakai saat sesi room habis.
    Set oleh rooms.py (sesi expired/end), dibaca oleh _auto_advance agar lagu
    yang sedang diputar diselesaikan dulu lalu berhenti (bukan di-tengah)."""
    return f"karaoke:room_stop_after:{room}"


async def set_room_stop_after(room: str) -> None:
    """Tandai room berhenti rapi setelah lagu selesai (TTL 24 jam pengaman)."""
    try:
        await _get_redis().set(_stop_after_key(room), "1", ex=86400)
    except Exception:
        pass


async def clear_room_stop_after(room: str) -> None:
    """Bersihkan flag saat sesi baru dimulai (lanjut normal)."""
    try:
        await _get_redis().delete(_stop_after_key(room))
    except Exception:
        pass


async def is_room_stop_after(room: str) -> bool:
    """Cek apakah room harus berhenti setelah lagu selesai."""
    try:
        return bool(await _get_redis().get(_stop_after_key(room)))
    except Exception:
        return False


async def request_stop_after_song(room: str) -> None:
    """Minta room berhenti rapi: selesaikan lagu yang sedang diputar lalu
    berhenti. Jika TIDAK ada lagu yang diputar saat ini (room idle), langsung
    berhenti sekarang (emit session_ended + queue_empty) — tidak menunggu
    auto_advance yang tidak akan pernah berjalan."""
    await set_room_stop_after(room)
    async with async_session() as s:
        r = await s.execute(
            select(QueueItem)
            .where(QueueItem.room_id == room, QueueItem.status == "playing")
            .limit(1)
        )
        playing = r.scalar_one_or_none()
    if playing is None:
        await clear_room_stop_after(room)
        await sio.emit("session_ended", {
            "room_id": room,
            "message": "Sesi room berakhir",
        }, room=room)
        await sio.emit("queue_empty", {"room_id": room}, room=room)


def _room_players(room: str) -> list:
    """SID klien player yang sedang terhubung di satu room."""
    return [sid for sid, info in active.items()
            if info.get("room") == room
            and info.get("type") in ("player", "player-screen")]


async def _close_playing_items(session, room: str) -> int:
    """Tutup SEMUA item 'playing' di room: status 'played' + catat history.
    Dipakai play_song agar hanya SATU lagu yang 'playing' — jika tidak,
    operator bisa menampilkan lagu lama (item 'playing' pertama) sementara
    player memutar lagu baru (Play Now tidak sinkron dengan player)."""
    r = await session.execute(
        select(QueueItem)
        .where(QueueItem.room_id == room, QueueItem.status == "playing")
    )
    items = r.scalars().all()
    for qi in items:
        qi.status = "played"
        qi.completed_at = datetime.utcnow()
        if qi.song_id:
            sg = (await session.execute(
                select(Song).where(Song.id == qi.song_id))).scalar_one_or_none()
            if sg:
                session.add(PlaybackHistory(
                    song_id=sg.id, room_id=room, title=sg.title, artist=sg.artist))
    return len(items)


async def _auto_advance(room: str, delay: float = 5) -> None:
    """Auto-play lagu berikutnya setelah jeda (anti-nyangkut). Dipakai
    song_ended (5 dtk) & skip_song (2 dtk) — skip = lanjut lagu berikutnya,
    seperti sistem karaoke komersial. Bila antrian kosong -> emit queue_empty.
    Bila sesi room sudah habis (flag stop_after) -> berhenti rapi: lagu yang
    sedang diputar diselesaikan, TIDAK lanjut ke lagu berikutnya."""
    await asyncio.sleep(delay)
    # Sesi room berakhir: hentikan auto-advance, beri tahu semua klien.
    if await is_room_stop_after(room):
        await clear_room_stop_after(room)
        await sio.emit("session_ended", {
            "room_id": room,
            "message": "Sesi room berakhir — lagu berhenti setelah lagu selesai",
        }, room=room)
        await sio.emit("queue_empty", {"room_id": room}, room=room)
        return
    async with async_session() as s2:
        r = await s2.execute(
            select(QueueItem)
            .where(QueueItem.room_id == room, QueueItem.status == "waiting")
            .order_by(QueueItem.priority.desc(), QueueItem.created_at.asc())
            .limit(1)
        )
        nxt = r.scalar_one_or_none()
        if nxt:
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
            rev2 = await bump_queue_revision(room)
            await sio.emit("play", {
                "song_id": nxt.song_id,
                "queue_id": nxt.id,
                "auto_play": True,
            }, room=room)
            await sio.emit("queue_updated", {
                "room_id": room, "revision": rev2}, room=room)
        else:
            await sio.emit("queue_empty", {
                "room_id": room,
                "message": "Antrian kosong, silakan tambah lagu",
            }, room=room)


@sio.event
async def connect(sid, environ):
    active[sid] = {"sid": sid, "type": "unknown", "room": "default"}


@sio.event
async def disconnect(sid):
    active.pop(sid, None)


@sio.event
async def register(sid, data):
    room = data.get("room_id", "default")
    if sid in active:
        active[sid].update({"type": data.get("type", "unknown"), "room": room})
    await sio.enter_room(sid, room)
    await sio.emit("ok", {
        "type": data.get("type"),
        "room_id": room,
        "key_shift": room_key_shifts.get(room, 0),
    }, to=sid)

    # Player yang (re)connect: kirim ulang lagu yang sedang 'playing' agar TV
    # tidak diam — memulihkan kasus 'play' yang hilang saat player offline
    # (atau TV reload di tengah lagu). Video mulai muted, tinggal unmute.
    if data.get("type") in ("player", "player-screen"):
        async with async_session() as s:
            r = await s.execute(
                select(QueueItem)
                .where(QueueItem.room_id == room, QueueItem.status == "playing")
                .limit(1)
            )
            cur = r.scalar_one_or_none()
        if cur:
            await sio.emit("play", {
                "song_id": cur.song_id,
                "queue_id": cur.id,
                "auto_play": True,
            }, to=sid)


@sio.event
async def play_song(sid, data):
    sid_q = data.get("queue_id")
    room = data.get("room_id", "default")
    async with async_session() as s:
        # Tutup lagu 'playing' sebelumnya -> hanya SATU yang playing (Play Now
        # benar-benar memutar lagu yang dipilih, sinkron operator & player).
        await _close_playing_items(s, room)
        if sid_q:
            await s.execute(update(QueueItem).where(QueueItem.id == sid_q).values(status="playing", played_at=datetime.utcnow()))
        await s.execute(update(Song).where(Song.id == data.get("song_id")).values(play_count=Song.play_count + 1))
        await s.commit()
    rev = await bump_queue_revision(room)
    await sio.emit("play", {"song_id": data.get("song_id"), "queue_id": sid_q}, room=room)
    await sio.emit("queue_updated", {"room_id": room, "revision": rev}, room=room)


@sio.event
async def pause_song(sid, data):
    room = data.get("room_id", "default")
    await sio.emit("ctrl", {"action": "pause"}, room=room)
    # Tandai pause: watchdog TIDAK men-skip lagu yang sedang di-pause sah
    # (marker kadaluarsa setelah STUCK_NO_PROGRESS_SEC jika tidak di-resume).
    try:
        await _get_redis().set(_paused_key(room), "1", ex=STUCK_NO_PROGRESS_SEC)
    except Exception:
        pass


@sio.event
async def resume_song(sid, data):
    room = data.get("room_id", "default")
    await sio.emit("ctrl", {"action": "resume"}, room=room)
    try:
        await _get_redis().delete(_paused_key(room))
    except Exception:
        pass


@sio.event
async def skip_song(sid, data):
    room = data.get("room_id", "default")
    async with async_session() as s:
        if data.get("queue_id"):
            await s.execute(update(QueueItem).where(QueueItem.id == data["queue_id"]).values(status="skipped", completed_at=datetime.utcnow()))
            await s.commit()
    rev = await bump_queue_revision(room)
    await sio.emit("ctrl", {"action": "skip"}, room=room)
    await sio.emit("queue_updated", {"room_id": room, "revision": rev}, room=room)
    # Skip = lanjut ke lagu berikutnya (anti-nyangkut), jeda singkat 2 detik
    asyncio.create_task(_auto_advance(room, delay=2))


@sio.event
async def song_ended(sid, data):
    """
    Dipanggil saat video selesai di player.
    - Tandai queue item selesai + catat history
    - Auto-play lagu berikutnya setelah jeda 5 detik
    """
    room = data.get("room_id", "default")
    queue_id = data.get("queue_id")

    # Tandai lagu selesai + record history (query song via queue item,
    # bukan via 'db' yang tidak pernah ada - fix bug auto-play).
    async with async_session() as s:
        if queue_id:
            qi = (await s.execute(select(QueueItem).where(QueueItem.id == queue_id))).scalar_one_or_none()
            if qi:
                qi.status = "played"
                qi.completed_at = datetime.utcnow()
                if qi.song_id:
                    sg = (await s.execute(select(Song).where(Song.id == qi.song_id))).scalar_one_or_none()
                    if sg:
                        s.add(PlaybackHistory(song_id=sg.id, room_id=room, title=sg.title, artist=sg.artist))
            await s.commit()

    # Emit queue update + idle state
    rev = await bump_queue_revision(room)
    await sio.emit("queue_updated", {"room_id": room, "revision": rev}, room=room)
    await sio.emit("ctrl", {"action": "stop"}, room=room)

    # Auto-play lagu berikutnya setelah jeda 5 detik (anti-nyangkut)
    asyncio.create_task(_auto_advance(room, delay=5))


@sio.event
async def set_volume(sid, data):
    await sio.emit("vol", {"volume": data.get("volume", 80)}, room=data.get("room_id", "default"))


@sio.event
async def key_change(sid, data):
    """Terima perubahan pitch/key dari operator, simpan per-room & broadcast ke player"""
    room = data.get("room_id", "default")
    try:
        shift = int(data.get("key_shift", 0))
    except (TypeError, ValueError):
        shift = 0
    shift = max(-12, min(12, shift))  # Batasi range -12 s/d +12 semitone
    room_key_shifts[room] = shift
    await sio.emit("key_change", {"key_shift": shift}, room=room)


@sio.event
async def join_room(sid, data):
    await sio.enter_room(sid, data.get("room_id", "default"))


@sio.event
async def leave_room(sid, data):
    """Keluar dari room lama saat operator ganti room (agar tidak terima event room lama)"""
    await sio.leave_room(sid, data.get("room_id", "default"))


@sio.event
async def toggle_vocal(sid, data):
    await sio.emit("vocal", {"channel": data.get("channel", "stereo")}, room=data.get("room_id", "default"))


@sio.event
async def reorder_queue(sid, data):
    """Drag & drop reorder antrian dengan perlindungan race (revision check).
    Mengembalikan ack {ok, reason, revision} ke client."""
    room = data.get("room_id", "default")
    queue_ids = data.get("queue_ids", [])

    if not queue_ids:
        return {"ok": False, "reason": "empty"}

    # Cek + bump ATOMIS di Redis: reorder lain dengan revisi lama otomatis ditolak
    try:
        rev = int(data.get("revision", -1))
    except (TypeError, ValueError):
        rev = -1

    new_rev = await check_and_bump_queue_revision(room, rev)
    if new_rev == -1:
        current = await get_queue_revision(room)
        await sio.emit("queue_updated", {"room_id": room, "action": "reorder_rejected", "revision": current}, room=room)
        return {"ok": False, "reason": "stale", "revision": current}

    async with async_session() as s:
        for idx, qid in enumerate(queue_ids):
            await s.execute(
                update(QueueItem)
                .where(QueueItem.id == qid, QueueItem.room_id == room)
                .values(priority=len(queue_ids) - idx)
            )
        await s.commit()

    await sio.emit("queue_updated", {"room_id": room, "action": "reordered", "revision": new_rev}, room=room)
    return {"ok": True, "revision": new_rev}


@sio.event
async def clear_queue(sid, data):
    """Kosongkan seluruh antrian"""
    room = data.get("room_id", "default")

    async with async_session() as s:
        await s.execute(
            update(QueueItem)
            .where(QueueItem.room_id == room, QueueItem.status == "waiting")
            .values(status="skipped", completed_at=datetime.utcnow())
        )
        await s.commit()

    rev = await bump_queue_revision(room)
    await sio.emit("queue_updated", {"room_id": room, "action": "cleared", "revision": rev}, room=room)
    await sio.emit("queue_empty", {"room_id": room}, room=room)


@sio.event
async def playback_progress(sid, data):
    """Broadcast progress pemutaran dari player ke operator + heartbeat
    untuk watchdog anti-nyangkut (item 'playing' tanpa progress = macet)."""
    room = data.get("room_id", "default")
    await sio.emit("playback_progress", {
        "current_time": data.get("current_time", 0),
        "duration": data.get("duration", 0),
        "song_id": data.get("song_id"),
        "percentage": data.get("percentage", 0)
    }, room=room)
    try:
        await _get_redis().set(_progress_key(room), str(_time.time()), ex=3600)
    except Exception:
        pass


# ============================================================
# WATCHDOG ANTI-NYANGKUT (dijalankan dari startup backend)
# ============================================================
async def _stuck_watchdog_loop():
    """Tiap menit: cari item 'playing' yang tidak menerima progress heartbeat
    dalam STUCK_NO_PROGRESS_SEC -> tandai 'skipped' + berhentikan pemutaran.
    Jika masih ada klien player terhubung di room, lanjutkan ke lagu
    berikutnya; jika TV mati, antrian menunggu operator (jangan spam ke TV
    yang mati). Ini jaring pengaman terakhir agar antrian TIDAK pernah
    nyangkut selamanya (mis. player crash / event song_ended hilang)."""
    while True:
        try:
            await asyncio.sleep(WATCHDOG_INTERVAL_SEC)
            now = _time.time()
            async with async_session() as s:
                r = await s.execute(
                    select(QueueItem).where(QueueItem.status == "playing"))
                playing_items = r.scalars().all()
                stale_by_room: Dict[str, list] = {}
                for qi in playing_items:
                    room = qi.room_id
                    try:
                        paused = await _get_redis().exists(_paused_key(room))
                        v = await _get_redis().get(_progress_key(room))
                        last = float(v) if v else None
                    except Exception:
                        paused = False
                        last = None
                    if paused:
                        continue  # di-pause sah (break) — jangan diganggu
                    if last is not None and (now - last) <= STUCK_NO_PROGRESS_SEC:
                        continue  # masih aktif diputar
                    stale_by_room.setdefault(room, []).append(qi.id)
                # Update ATOMIK dengan guard status='playing' (anti race dengan
                # song_ended yang menandai 'played' di saat bersamaan).
                for room, ids in stale_by_room.items():
                    await s.execute(
                        update(QueueItem)
                        .where(QueueItem.id.in_(ids),
                               QueueItem.status == "playing")
                        .values(status="skipped", completed_at=datetime.utcnow())
                    )
                await s.commit()
                # Emit SETELAH commit agar klien yang refetch melihat data baru
                for room, ids in stale_by_room.items():
                    rev = await bump_queue_revision(room)
                    await sio.emit("ctrl", {"action": "stop"}, room=room)
                    await sio.emit("queue_updated", {
                        "room_id": room,
                        "action": "stuck_cleared",
                        "revision": rev,
                    }, room=room)
                    if _room_players(room):
                        # TV masih hidup -> langsung lanjut lagu berikutnya
                        asyncio.create_task(_auto_advance(room, delay=1))
        except Exception:
            pass


async def start_stuck_watchdog():
    """Panggil dari startup backend (main.py): mulai watchdog anti-nyangkut."""
    asyncio.create_task(_stuck_watchdog_loop())
