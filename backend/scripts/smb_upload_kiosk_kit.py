#!/usr/bin/env python3
"""Upload kit kiosk (initrd+preseed, menu.lst, go.bat) ke XP via pysmb guest.

Dipakai dari dalam container `karaoke_sync` (pysmb 1.2.15 sudah terpasang).

Penggunaan:
    KIT_DIR=/tmp/kit python smb_upload_kiosk_kit.py

Target: 192.168.100.140:445 (NIC USB GZCYC — onboard Attansic L2 tidak
mendukung Linux), user guest (kosong), share "karaoke bank 1" (= D:\).
File yang di-upload ke D:\\ :
    initrd-usbnic-preseed-v4.gz -> D:\\initrd-new.gz
    menu.lst                   -> D:\\menu.lst.new
    go.bat                     -> D:\\go.bat
Setelah itu user tinggal ketik `D:\\go.bat` di cmd XP.
"""
import os
import sys
from pathlib import Path

from smb.SMBConnection import SMBConnection

HOST = os.getenv("SMB_HOST", "192.168.100.140")
PORT = 445
SHARE = "karaoke bank 1"
MY_NAME = "bpf-sync"
REMOTE_NAME = "KARAOKE"

KIT_DIR = Path(os.getenv("KIT_DIR", "/srv/kiosk_kit"))
FILES = {
    "initrd-usbnic-preseed-v4.gz": "initrd-new.gz",
    "menu.lst": "menu.lst.new",
    "go.bat": "go.bat",
}


def main() -> int:
    conn = SMBConnection("", "", MY_NAME, REMOTE_NAME,
                         use_ntlm_v2=True, is_direct_tcp=True)
    print(f"[upload] konek ke {HOST}:{PORT} share '{SHARE}' ...")
    if not conn.connect(HOST, PORT, timeout=20):
        print("[upload] GAGAL konek — XP tidak jalan / SMB mati?", file=sys.stderr)
        return 1

    for src_name, dst_name in FILES.items():
        src = KIT_DIR / src_name
        if not src.exists():
            print(f"[upload] SKIP {src_name} (tidak ada)", file=sys.stderr)
            continue
        with open(src, "rb") as f:
            size = src.stat().st_size
            conn.storeFile(SHARE, dst_name, f)
        print(f"[upload] ✓ {src_name} ({size} bytes) -> D:\\{dst_name}")

    conn.close()
    print("[upload] SELESAI. Di cmd XP ketik:  D:\\go.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
