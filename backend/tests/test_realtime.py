"""
Test integrasi realtime: sinkronisasi antar operator/remote/player, proteksi
race pada reorder antrian, sesi room, sorting server-side, dan batch-filter.

Jalankan di dalam container backend:
    docker exec karaoke_backend pytest /app/tests -v
"""
import httpx
import pytest

from conftest import make_client, wait_until


def _fetch_song_ids(base_url, limit=3):
    r = httpx.get(f"{base_url}/api/songs", params={"limit": limit}, timeout=10)
    assert r.status_code == 200, r.text
    return [s["id"] for s in r.json()]


def _add_song(base_url, room_name, song_id, requester=None):
    body = {"song_id": song_id, "room_id": room_name}
    if requester:
        body["requester_name"] = requester
    r = httpx.post(f"{base_url}/api/queue", json=body, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()


def test_songs_sort_param(base_url):
    """Sorting server-side konsisten untuk pagination (newest & artist)."""
    r = httpx.get(f"{base_url}/api/songs", params={"limit": 50, "sort": "newest"}, timeout=10)
    assert r.status_code == 200, r.text
    ids = [s["id"] for s in r.json()]
    assert ids == sorted(ids, reverse=True), f"newest order broken: {ids}"

    r2 = httpx.get(f"{base_url}/api/songs", params={"limit": 50, "sort": "artist"}, timeout=10)
    assert r2.status_code == 200, r2.text
    # PostgreSQL menempatkan NULL artist di akhir; bandingkan hanya artis non-kosong
    # agar tidak flaky saat ada lagu tanpa artist.
    artists = [s["artist"] for s in r2.json() if s["artist"]]
    assert artists == sorted(artists, key=lambda a: a.lower()), "artist order broken"

    r3 = httpx.get(f"{base_url}/api/songs", params={"limit": 50, "sort": "plays"}, timeout=10)
    assert r3.status_code == 200, r3.text
    plays = [s["play_count"] for s in r3.json()]
    assert plays == sorted(plays, reverse=True), "plays order broken"


def test_queue_revision_header(base_url, room):
    """GET queue harus menyertakan header X-Queue-Revision."""
    r = httpx.get(f"{base_url}/api/queue/{room['name']}", timeout=10)
    assert r.status_code == 200, r.text
    rev = r.headers.get("x-queue-revision")
    assert rev is not None and rev.isdigit(), f"missing revision header: {r.headers}"


def test_realtime_add_play_controls(base_url, room):
    """Sinkronisasi add/play/pause/resume/skip ke semua klien (operator/remote/player)."""
    song_ids = _fetch_song_ids(base_url)
    if len(song_ids) < 2:
        pytest.skip("Butuh minimal 2 lagu di database")

    clients = [make_client(base_url, room["name"]) for _ in range(3)]
    try:
        ops = [c[1] for c in clients]
        # remote menambah 2 lagu -> semua klien terima queue_updated
        q1 = _add_song(base_url, room["name"], song_ids[0], requester="guest-abc")
        _add_song(base_url, room["name"], song_ids[1])
        assert wait_until(ops[0], "queue_updated") and wait_until(ops[1], "queue_updated") and wait_until(ops[2], "queue_updated")

        # operator play -> semua klien terima play
        clients[0][0].emit("play_song", {"song_id": q1["song_id"], "room_id": room["name"], "queue_id": q1["id"]})
        assert all(wait_until(e, "play") for e in ops)

        # pause / resume / skip -> ctrl ke semua
        clients[0][0].emit("pause_song", {"room_id": room["name"]})
        assert all(wait_until(e, "ctrl") for e in ops)
        clients[0][0].emit("resume_song", {"room_id": room["name"]})
        assert all(wait_until(e, "ctrl", count=2) for e in ops)
        clients[0][0].emit("skip_song", {"room_id": room["name"], "queue_id": q1["id"]})
        assert all(wait_until(e, "ctrl", count=3) for e in ops)
    finally:
        for c, _ in clients:
            try: c.disconnect()
            except Exception: pass


def test_reorder_race_protection(base_url, room):
    """Reorder dengan revisi basi ditolak; revisi valid diterima dan urutan berubah."""
    song_ids = _fetch_song_ids(base_url)
    if len(song_ids) < 2:
        pytest.skip("Butuh minimal 2 lagu di database")

    ids = [_add_song(base_url, room["name"], sid)["id"] for sid in song_ids[:2]]
    c, events = make_client(base_url, room["name"])
    try:
        r = httpx.get(f"{base_url}/api/queue/{room['name']}", timeout=10)
        rev = int(r.headers["x-queue-revision"])
        current = [x["id"] for x in r.json()]
        assert current == ids

        # Revisi basi -> ditolak (ack stale)
        ack_wrong = {}
        c.emit("reorder_queue", {"room_id": room["name"], "queue_ids": list(reversed(current)), "revision": rev + 999},
               callback=lambda res: ack_wrong.update(res or {}))
        assert wait_until(events, "queue_updated", timeout=3)
        assert ack_wrong.get("ok") is False and ack_wrong.get("reason") == "stale", ack_wrong

        # Revisi valid -> diterima, urutan server berubah
        ack_ok = {}
        c.emit("reorder_queue", {"room_id": room["name"], "queue_ids": list(reversed(current)), "revision": rev},
               callback=lambda res: ack_ok.update(res or {}))
        assert wait_until(events, "queue_updated", count=2, timeout=3)
        assert ack_ok.get("ok") is True, ack_ok

        r2 = httpx.get(f"{base_url}/api/queue/{room['name']}", timeout=10)
        order_after = [x["id"] for x in r2.json()]
        assert order_after == list(reversed(current)), f"{order_after} != {list(reversed(current))}"
    finally:
        try: c.disconnect()
        except Exception: pass


def test_room_session_realtime(base_url, admin, room):
    """Start/extend/end sesi oleh admin terkirim realtime ke semua klien room."""
    clients = [make_client(base_url, room["name"]) for _ in range(3)]
    try:
        ops = [c[1] for c in clients]
        H = admin["headers"]

        r = httpx.post(f"{base_url}/api/admin/rooms/{room['name']}/session/start",
                       json={"duration_minutes": 30}, headers=H, timeout=10)
        assert r.status_code == 200, r.text
        assert all(wait_until(e, "room_session") for e in ops), "room_session tidak diterima semua klien"

        r = httpx.post(f"{base_url}/api/admin/rooms/{room['name']}/session/extend",
                       json={"minutes": 15}, headers=H, timeout=10)
        assert r.status_code == 200, r.text

        r = httpx.post(f"{base_url}/api/admin/rooms/{room['name']}/session/end", headers=H, timeout=10)
        assert r.status_code == 200, r.text
    finally:
        for c, _ in clients:
            try: c.disconnect()
            except Exception: pass


def test_batch_filter_dedup(base_url, room):
    """batch-filter menambah semua hasil filter dan melewati duplikat pada run kedua."""
    r1 = httpx.post(f"{base_url}/api/queue/batch-filter",
                    params={"room_id": room["name"]}, timeout=10)
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["added"] > 0, b1

    r2 = httpx.post(f"{base_url}/api/queue/batch-filter",
                    params={"room_id": room["name"]}, timeout=10)
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    # Run kedua: semua sudah waiting -> tidak ada yang ditambahkan lagi
    assert b2["added"] == 0, b2
    assert b2["skipped_duplicates"] == b1["matched"], b2
