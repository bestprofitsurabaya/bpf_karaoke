"""
Queue Revision Store (Redis-backed)
====================================
Revisi antrian per room disimpan di Redis agar:
  - Konsisten setelah restart backend (tidak hilang dari memori)
  - Konsisten jika backend dijalankan dengan banyak worker/process

check_and_bump_queue_revision() menggunakan skrip Lua ATOMik di Redis
sehingga cek "revisi masih sama" + kenaikan revisi tidak bisa disisipi
reorder lain (perlindungan race yang benar).

Jika Redis tidak tersedia, otomatis fallback ke dict in-memory
(dengan asyncio.Lock) agar layanan tetap berjalan.
"""
import os
import asyncio
from typing import Optional

from redis.asyncio import Redis

_client: Optional[Redis] = None
_fallback: dict = {}
_fallback_lock: Optional[asyncio.Lock] = None

_CHECK_BUMP_LUA = """
local cur = tonumber(redis.call('GET', KEYS[1]) or '0')
local expected = tonumber(ARGV[1])
if expected >= 0 and expected ~= cur then
    return -1
end
return redis.call('INCR', KEYS[1])
"""


def _key(room: str) -> str:
    return f"karaoke:queue_rev:{room}"


def _get_client() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(
            os.getenv("REDIS_URL", "redis://karaoke_redis:6379/0"),
            decode_responses=True,
        )
    return _client


async def get_queue_revision(room: str) -> int:
    """Revisi saat ini untuk satu room (0 jika belum pernah di-bump)."""
    try:
        v = await _get_client().get(_key(room))
        return int(v) if v else 0
    except Exception:
        return _fallback.get(room, 0)


async def bump_queue_revision(room: str) -> int:
    """Naikkan revisi satu room dan kembalikan nilai baru (untuk event queue_updated)."""
    try:
        return int(await _get_client().incr(_key(room)))
    except Exception:
        global _fallback_lock
        if _fallback_lock is None:
            _fallback_lock = asyncio.Lock()
        async with _fallback_lock:
            _fallback[room] = _fallback.get(room, 0) + 1
            return _fallback[room]


async def clear_queue_revision(room: str) -> None:
    """Hapus revisi satu room (dipakai cleanup test; opsional di produksi)."""
    try:
        await _get_client().delete(_key(room))
    except Exception:
        _fallback.pop(room, None)


async def check_and_bump_queue_revision(room: str, expected: int) -> int:
    """
    Atomik: tolak bila `expected` != revisi saat ini (kembalikan -1),
    selain itu naikkan revisi dan kembalikan nilai baru.
    `expected == -1` berarti klien lama tanpa proteksi -> selalu diterima.
    """
    try:
        res = await _get_client().eval(_CHECK_BUMP_LUA, 1, _key(room), str(expected))
        return int(res)
    except Exception:
        global _fallback_lock
        if _fallback_lock is None:
            _fallback_lock = asyncio.Lock()
        async with _fallback_lock:
            cur = _fallback.get(room, 0)
            if expected >= 0 and expected != cur:
                return -1
            _fallback[room] = cur + 1
            return _fallback[room]
