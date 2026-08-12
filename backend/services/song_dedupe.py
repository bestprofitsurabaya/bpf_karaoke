"""
Song Dedupe Service - Deteksi & Penghapusan Lagu Duplikat
==========================================================
Satu sumber kebenaran untuk logika dedupe yang dipakai oleh:
  1. CLI   : backend/dedupe_songs.py            (one-off manual)
  2. Celery: celery_tasks.dedupe_duplicates     (terjadwal mingguan)
  3. API   : /api/admin/dedupe/*                (review manual di UI admin)

Strategi deteksi (3 pass, saling lepas):
  - Pass A (metadata exact) : (lower artist, lower title) sama persis.
  - Pass B (metadata fuzzy) : normalisasi tanpa tanda baca/spasi — hanya untuk
    lagu yang belum diputuskan pass A dan artisnya bukan placeholder.
  - Pass C (path-based)     : lagu TANPA metadata (artis/judul kosong) dicocokkan
    lewat rel-path setelah menghapus prefix "karaoke bank N/" — mis.
    ".../karaoke bank 1/Bank 3/Mandarin/Wang Cie/Ing Siung Lei.mp4" vs
    ".../karaoke bank 2/Bank 3/Mandarin/Wang Cie/Ing Siung Lei.mp4" → duplikat.

Kebijakan penghapusan:
  - Versi yang DIPERTAHANKAN = created_at paling awal (tie-break id terkecil).
  - Hapus PERMANEN (baris DB + file) — kecuali file masih direferensikan lagu
    lain (aktif/nonaktif) yang TIDAK ikut dihapus.
  - Backup JSON semua baris yang dihapus ditulis SEBELUM eksekusi.
  - Fail-closed: hanya lagu yang benar-benar terdeteksi duplikat yang boleh
    dihapus via API (id diverifikasi ulang terhadap kandidat saat ini).
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, delete

from database import async_session
from models import Song

# Artis "generik" yang dipakai banyak bank sebagai placeholder — hanya dicocokkan
# EXACT (jangan fuzzy, risiko salah pasang).
PLACEHOLDER_ARTISTS = {
    "western artist", "various", "various artists", "unknown",
    "unknown artist", "none", "no artist", "artis", "?", "-",
}

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/uploads"))
MEDIA_ROOTS = ("/media/lagu/", "/media/transcoded/")
# Prefix bank pada file hasil transcode: .../karaoke bank N/<rel>.mp4
_BANK_PREFIX_RE = re.compile(r"^/media/transcoded/karaoke bank \d+/", re.I)


def norm(s: str) -> str:
    """Normalisasi fuzzy ringan: lowercase + buang semua non-alphanumeric."""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def is_placeholder_artist(artist) -> bool:
    if not artist:
        return True
    return artist.strip().lower() in PLACEHOLDER_ARTISTS


def keep_key(song) -> tuple:
    """Kunci 'versi mana yang dipertahankan': (created_at, id)."""
    return (song.created_at or datetime.min, song.id or 0)


def rel_path_without_bank(file_path: str) -> str:
    """Rel path setelah menghapus prefix bank — untuk mencocokkan duplikat
    antar 'karaoke bank 1' dan 'karaoke bank 2' pada lagu tanpa metadata."""
    if not file_path:
        return ""
    return _BANK_PREFIX_RE.sub("", file_path, count=1).lower()


async def collect_metadata_songs(session):
    """Lagu AKTIF dengan metadata lengkap (artis & judul tidak kosong)."""
    q = await session.execute(
        select(Song).where(
            Song.is_active == True,
            Song.artist.isnot(None),
            Song.title.isnot(None),
            Song.artist != "",
            Song.title != "",
        )
    )
    return q.scalars().all()


async def collect_no_metadata_songs(session):
    """Lagu AKTIF yang TIDAK punya metadata lengkap — hanya bisa dicocokkan
    via rel-path (Pass C)."""
    q = await session.execute(
        select(Song).where(
            Song.is_active == True,
            (Song.artist.is_(None) | (Song.artist == "")
             | Song.title.is_(None) | (Song.title == "")),
        )
    )
    return q.scalars().all()


async def collect_all_paths(session):
    """SEMUA (id, file_path) di tabel songs — aktif & nonaktif.
    Dipakai untuk proteksi file: lagu nonaktif bisa diaktifkan kembali, jadi
    filenya tidak boleh dihapus bila masih direferensikan baris lain."""
    rows = await session.execute(select(Song.id, Song.file_path))
    return [(r[0], str(r[1])) for r in rows if r[1]]


def compute_protected_paths(all_rows, delete_ids) -> set:
    """Path file yang TIDAK boleh dihapus = path yang masih direferensikan
    oleh setidaknya satu baris yang TIDAK ikut dihapus. Kunci keamanan:
    file hanya dihapus bila SEMUA referensinya adalah lagu yang dihapus."""
    protected = set()
    for sid, fp in all_rows:
        if sid not in delete_ids:
            protected.add(fp)
    return protected


def build_metadata_groups(songs) -> list:
    """Pass A (exact) + Pass B (fuzzy). Return list grup lagu duplikat."""
    groups = []

    # Pass A: exact
    exact = {}
    for s in songs:
        k = (s.artist.strip().lower(), s.title.strip().lower())
        exact.setdefault(k, []).append(s)
    decided = set()
    for k, members in exact.items():
        if len(members) > 1:
            groups.append(members)
            decided.update(s.id for s in members)

    # Pass B: fuzzy ringan (sisa lagu, artis non-placeholder)
    fuzzy = {}
    for s in songs:
        if s.id in decided:
            continue
        if is_placeholder_artist(s.artist):
            continue
        kn = (norm(s.artist), norm(s.title))
        if not kn[0] or not kn[1]:
            continue
        fuzzy.setdefault(kn, []).append(s)
    for k, members in fuzzy.items():
        if len(members) > 1:
            groups.append(members)

    return groups


def build_path_groups(no_meta_songs) -> list:
    """Pass C: lagu tanpa metadata → grup via rel-path tanpa prefix bank.
    Hanya file di MEDIA_ROOTS yang dipertimbangkan."""
    by_rel = {}
    for s in no_meta_songs:
        fp = s.file_path or ""
        if not fp.startswith(MEDIA_ROOTS):
            continue
        rel = rel_path_without_bank(fp)
        if not rel:
            continue
        by_rel.setdefault(rel, []).append(s)
    return [members for members in by_rel.values() if len(members) > 1]


async def find_duplicate_groups(session) -> dict:
    """Analisis lengkap (tanpa mengubah apa pun). Struktur siap untuk API/UI.

    Return:
      {
        "total_groups": N, "total_to_delete": M,
        "groups": [{ "kind": "metadata"|"path", "keep": {...}, "candidates": [...] }]
      }
    """
    meta = await collect_metadata_songs(session)
    no_meta = await collect_no_metadata_songs(session)

    groups = []  # list (kind, members)
    for g in build_metadata_groups(meta):
        groups.append(("metadata", g))
    for g in build_path_groups(no_meta):
        groups.append(("path", g))

    out = []
    for kind, members in groups:
        keeper = min(members, key=keep_key)
        cands = [s for s in members if s.id != keeper.id]
        if not cands:
            continue
        out.append({
            "kind": kind,
            "keep": _song_payload(keeper),
            "candidates": [_song_payload(c) for c in cands],
        })
    return {
        "total_groups": len(out),
        "total_to_delete": sum(len(g["candidates"]) for g in out),
        "groups": out,
    }


def _song_payload(song) -> dict:
    size = None
    try:
        size = Path(song.file_path).stat().st_size if song.file_path else None
    except OSError:
        size = None
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "file_path": song.file_path,
        "created_at": str(song.created_at) if song.created_at else None,
        "size_bytes": size,
    }


async def _current_delete_ids(session) -> set:
    """Kandidat hapus SAAT INI (fail-closed untuk endpoint delete):
    hanya id yang terdeteksi sebagai versi lebih baru dari suatu grup."""
    meta = await collect_metadata_songs(session)
    no_meta = await collect_no_metadata_songs(session)
    groups = list(build_metadata_groups(meta)) + list(build_path_groups(no_meta))
    ids = set()
    for members in groups:
        keeper = min(members, key=keep_key)
        for s in members:
            if s.id != keeper.id:
                ids.add(s.id)
    return ids


async def delete_selected(session, song_ids: list) -> dict:
    """Hapus permanen lagu terpilih (baris DB + file, dengan proteksi path).
    Fail-closed: id yang tidak termasuk kandidat duplikat saat ini ditolak.

    Return: {"deleted_rows": N, "deleted_files": N, "skipped_files": N,
             "rejected": [...], "backup_path": "..."}
    """
    song_ids = [int(i) for i in song_ids]
    allowed = await _current_delete_ids(session)
    rejected = [i for i in song_ids if i not in allowed]

    ids = [i for i in song_ids if i in allowed]
    if not ids:
        return {"deleted_rows": 0, "deleted_files": 0, "skipped_files": 0,
                "rejected": rejected, "backup_path": None,
                "message": "Tidak ada lagu valid untuk dihapus."}

    rows = await session.execute(select(Song).where(Song.id.in_(ids)))
    songs = rows.scalars().all()
    if not songs:
        return {"deleted_rows": 0, "deleted_files": 0, "skipped_files": 0,
                "rejected": rejected, "backup_path": None}

    # Proteksi file: semua path di DB yang masih direferensikan lagu lain
    all_rows = await collect_all_paths(session)
    protected = compute_protected_paths(all_rows, set(ids))

    # Backup sebelum hapus
    backup_path = BACKUP_DIR / f"dedupe_backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(
        json.dumps([_song_payload(s) | {"reason": "admin-selected"} for s in songs],
                   indent=2, ensure_ascii=False), encoding="utf-8")

    deleted_rows = deleted_files = skipped_files = 0
    for s in songs:
        fp = s.file_path or ""
        if fp not in protected and fp.startswith(MEDIA_ROOTS):
            try:
                Path(fp).unlink(missing_ok=True)
                deleted_files += 1
            except OSError:
                skipped_files += 1
        else:
            skipped_files += 1
        await session.execute(delete(Song).where(Song.id == s.id))
        deleted_rows += 1

    await session.commit()
    return {
        "deleted_rows": deleted_rows,
        "deleted_files": deleted_files,
        "skipped_files": skipped_files,
        "rejected": rejected,
        "backup_path": str(backup_path),
    }
