#!/usr/bin/env python3
"""
Dedupe Songs Script (CLI) - Hapus Lagu Duplikat (versi TERBARU, pertahankan ORIGINAL)
=====================================================================================
CLI tipis di atas services/song_dedupe.py — semua logika deteksi/penghapusan
berada di modul service (dipakai juga oleh task Celery mingguan & API admin).

Cara pakai:
  python dedupe_songs.py            # DRY-RUN: hanya laporan, tidak mengubah apa pun
  python dedupe_songs.py --apply    # EKSEKUSI: hapus permanen (DB + file)
"""
import sys
import os
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import async_session
from services.song_dedupe import (
    find_duplicate_groups, delete_selected,
)


async def main():
    ap = argparse.ArgumentParser(description="Hapus lagu duplikat (versi terbaru)")
    ap.add_argument("--apply", action="store_true",
                    help="Eksekusi penghapusan permanen. Tanpa flag = dry-run.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Batasi jumlah lagu yang dihapus (uji coba kecil).")
    args = ap.parse_args()

    async with async_session() as session:
        report = await find_duplicate_groups(session)
        print(f"Grup duplikat ditemukan : {report['total_groups']}")
        print(f"Lagu yang akan dihapus  : {report['total_to_delete']} "
              f"(versi lebih baru; keep yang terlama)")

        print("\nContoh (10 pertama):")
        for i, g in enumerate(report["groups"][:10], 1):
            k = g["keep"]
            print(f"  {i}. KEEP id={k['id']} | {k['artist'] or '-'} - "
                  f"{k['title'] or '(tanpa metadata)'} | {k['file_path']}")
            for c in g["candidates"]:
                print(f"     DEL id={c['id']} | {c['artist'] or '-'} - "
                      f"{c['title'] or '(tanpa metadata)'} | {c['file_path']}")

        # Perkiraan ruang yang dibebaskan
        freed = 0
        n = 0
        for g in report["groups"]:
            for c in g["candidates"]:
                n += 1
                if c.get("size_bytes"):
                    freed += c["size_bytes"]
        print(f"\nPerkiraan ruang dibebaskan: {freed / 1024**3:.2f} GB ({n} file)")

        if not args.apply:
            print("\nDRY-RUN selesai — tidak ada yang diubah. "
                  "Jalankan dengan --apply untuk eksekusi.")
            return

        ids = [c["id"] for g in report["groups"] for c in g["candidates"]]
        if args.limit > 0:
            ids = ids[: args.limit]
            print(f"  (--limit={args.limit}: hanya {len(ids)} diproses)")
        res = await delete_selected(session, ids)
        print(f"\n✅ Selesai. Baris DB dihapus: {res['deleted_rows']} | "
              f"File dihapus: {res['deleted_files']} | File dipertahankan "
              f"(dipakai lagu lain): {res['skipped_files']}")
        print(f"Backup: {res['backup_path']}")


if __name__ == "__main__":
    asyncio.run(main())
