"""
SMB Karaoke Bank Sync Engine (pysmb / SMB1) - PARALLEL
=======================================================
Menyalin seluruh lagu dari share Windows XP (karaoke bank 1 & 2) ke storage
server secara INCREMENTAL & RESUMABLE dengan beberapa koneksi SMB paralel:

- Aman terhadap putus koneksi / pemadaman listrik: file yang sudah tersalin
  (ukuran sama) dilewati; salinan memakai `.part` lalu rename atomik.
- PARALEL: tiap worker punya koneksi SMB sendiri dan memproses folder
  top-level yang berbeda (walk + copy paralel). Default 4 worker.
- Menulis `sync_state.json` secara atomik tiap ±5 detik (UI admin real-time).
- Mendeteksi "semua sudah tersalin" (done), menulis `SYNC_COMPLETE.txt`, dan
  (opsional) mengirim notifikasi ke webhook (SMB_WEBHOOK_URL).
- Memonitor ruang disk /srv; memberi warning bila menipis.

Config (env):
  SMB_HOST          default 192.168.100.140 (IP terakhir dikenal)
  SMB_AUTO_DETECT   default 1 (aktif) — bila SMB_HOST mati, cari otomatis via
                    NetBIOS: broadcast dulu, lalu scan subnet /24 + reverse
                    query nama SMB_REMOTE_NAME. Berguna saat IP XP berubah.
  SMB_PORT          default 445
  SMB_USER          default ""  (guest)
  SMB_PASSWORD      default ""
  SMB_SHARES        default "karaoke bank 1,karaoke bank 2"
  SMB_PARALLEL      default 4  (jumlah koneksi paralel; batas XP = 10 sesi)
  SMB_WEBHOOK_URL   default "" (opsional; dikirimi POST JSON saat done/error)
  MEDIA_PATH        default /media/lagu
  SYNC_STATE_PATH   default /srv_media/sync_state.json
"""
import concurrent.futures
import errno
import json
import os
import queue
import re
import shutil
import socket
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from smb.SMBConnection import SMBConnection

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# SMB_HOST = IP terakhir yang dikenal (dipakai dulu; auto-detect hanya
# dipicu bila koneksi ke IP ini GAGAL — maka XP kemungkinan pindah IP).
SMB_HOST_ENV = os.getenv("SMB_HOST", "").strip()
SMB_AUTO_DETECT = os.getenv("SMB_AUTO_DETECT", "1").lower() \
    in ("1", "true", "yes", "on")
DEFAULT_SMB_HOST = os.getenv("SMB_DEFAULT_HOST", "192.168.100.140")
SMB_PORT = int(os.getenv("SMB_PORT", "445"))
SMB_USER = os.getenv("SMB_USER", "")
SMB_PASSWORD = os.getenv("SMB_PASSWORD", "")
SMB_MY_NAME = os.getenv("SMB_MY_NAME", "bpf-sync")
SMB_REMOTE_NAME = os.getenv("SMB_REMOTE_NAME", "KARAOKE")
SMB_SHARES = [s.strip() for s in
              os.getenv("SMB_SHARES", "karaoke bank 1,karaoke bank 2").split(",")
              if s.strip()]
SMB_PARALLEL = max(1, min(8, int(os.getenv("SMB_PARALLEL", "4"))))
SMB_WEBHOOK_URL = os.getenv("SMB_WEBHOOK_URL", "").strip()
MEDIA_PATH = Path(os.getenv("MEDIA_PATH", "/media/lagu"))
SYNC_STATE_PATH = Path(os.getenv("SYNC_STATE_PATH", "/srv_media/sync_state.json"))

# Kontrol manual via panel admin (v2.7): flag pause & heartbeat disimpan di Redis.
# - PAUSE_KEY  : 'sync:paused' = 1 -> worker berhenti menyalin (tidur), state tetap
#                 ditulis; file .part yang tertinggal aman (rename atomik).
# - HEARTBEAT_KEY: timestamp terakhir worker aktif -> UI tahu proses hidup/mati.
# Fail-open: bila Redis bermasalah, dianggap TIDAK pause (sync jalan normal).
PAUSE_KEY = 'sync:paused'
HEARTBEAT_KEY = 'sync:heartbeat'
HEARTBEAT_SEC = 10        # tulis heartbeat tiap N detik saat proses berjalan
PAUSE_POLL_SEC = 3        # cek flag pause tiap N detik saat sedang pause

def _redis():
    try:
        import redis
        return redis.from_url(
            os.getenv("REDIS_URL", "redis://karaoke_redis:6379/0"),
            socket_connect_timeout=3, socket_timeout=3)
    except Exception:
        return None

def is_paused() -> bool:
    """True bila panel admin sedang menjeda sync (fail-open: Redis error = jalan)."""
    r = _redis()
    if r is None:
        return False
    try:
        return r.get(PAUSE_KEY) in (b"1", "1", b"true", "true")
    except Exception:
        return False
    finally:
        try: r.close()
        except Exception: pass

def set_paused(paused: bool) -> None:
    """Set/hapus flag pause (dipakai task admin / helper test)."""
    r = _redis()
    if r is None:
        return
    try:
        if paused:
            r.set(PAUSE_KEY, "1")
        else:
            r.delete(PAUSE_KEY)
    except Exception:
        pass
    finally:
        try: r.close()
        except Exception: pass

def heartbeat() -> None:
    """Tulis timestamp aktivitas worker (untuk deteksi proses hidup di UI)."""
    r = _redis()
    if r is None:
        return
    try:
        r.set(HEARTBEAT_KEY, str(time.time()))
    except Exception:
        pass
    finally:
        try: r.close()
        except Exception: pass

def _wait_if_paused(state: dict) -> bool:
    """Saat flag pause aktif: tulis state (dengan penanda paused) & tidur.
    Mengembalikan True bila sekarang boleh lanjut (flag sudah di-resume)."""
    while is_paused():
        state["paused"] = True
        state["phase"] = "paused"
        save_state(state)
        print("[smb_sync] ⏸ DI-JEDA dari panel admin — menunggu resume...", flush=True)
        time.sleep(PAUSE_POLL_SEC)
    state["paused"] = False
    return True
# Lokasi MP4 hasil transcode (di server: /srv_media/transcoded).
# Dipakai untuk TIDAK menyalin ulang sumber yang sudah punya MP4 (lihat
# transcoded_exists_for) — penting karena sumber .mpg/.mpeg sengaja dihapus
# setelah transcode sukses; tanpa cek ini sync akan menyalinnya lagi tiap pass.
TRANSCODED_PATH = Path(os.getenv("TRANSCODED_PATH", "/srv_media/transcoded"))

MEDIA_EXTS = {e.lower() for e in
              os.getenv("SMB_EXTS",
                        ".mpg,.mpeg,.mp4,.avi,.mkv,.wmv,.flv,.vob,.mov,.m2v,.mpv,.3gp,.dat")
              .split(",") if e.strip()}

# Folder sistem Windows yang harus dilewati
SKIP_DIRS = {
    "$recycle.bin", "$recyclebin", "system volume information",
    "recycler", "$winnt$.~bt", "msocache",
}

DISK_WARN_GB = 20
DISK_CRIT_GB = 5

CONN_ERROR_THRESHOLD = 5      # error beruntun sebelum anggap koneksi mati
MAX_DEPTH = 14                # kedalaman maks walk folder
PASS_PAUSE_SEC = 10           # jeda antar pass saat masih ada file tersisa
DONE_RECHECK_SEC = 1800       # setelah done, re-walk tiap 30 menit utk lagu baru
STATE_SAVE_SEC = 5            # simpan state tiap N detik saat worker berjalan
NOTIFY_ERROR_COOLDOWN = 600   # min. 10 menit antar notifikasi error
BUILD_TIMEOUT_SEC = 300       # watchdog build_items (XP bisa hang di listPath)
ITEM_TIMEOUT_SEC = 900        # watchdog satu item kerja per worker (15 mnt)
HANG_RETRY_SEC = 1800         # coba ulang folder yang pernah hang tiap 30 mnt
POISON_THRESHOLD = int(os.getenv("SMB_POISON_THRESHOLD", "3"))
# File yang gagal disalin N pass berturut-turut di-skip sementara agar tidak
# membuat phase = error terus-menerus; dicoba ulang saat reset berkala / done.
_FILE_FAIL_KEY = "failed_files"

# Folder top-level yang pernah macet saat dipecah (split) — diingat agar
# pass berikutnya tidak menunggu lagi. Di-seed dari state saat start,
# di-reset berkala (HANG_RETRY_SEC) dan saat sync selesai (done).
_build_hang = set()

_UNSAFE_END = re.compile(r"[. ]+$")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_space_error(e) -> bool:
    """True bila kegagalan berasal dari disk penuh — JANGAN di-poison (bukan
    masalah file, melainkan masalah kapasitas; poison hanya untuk file yang
    memang bermasalah di sisi XP)."""
    if isinstance(e, OSError) and e.errno in (errno.ENOSPC, errno.EDQUOT):
        return True
    s = str(e).lower()
    return "no space" in s or "disk full" in s or "not enough space" in s


def sanitize_name(name: str) -> str:
    """Bersihkan karakter yang bermasalah di filesystem Linux."""
    name = _UNSAFE_END.sub("", name)
    name = name.replace("/", "_").replace("\x00", "")
    return name or "untitled"


# ---------------------------------------------------------------------------
# State file (ditulis atomik)
# ---------------------------------------------------------------------------
def default_state() -> dict:
    return {
        "started_at": iso_now(),
        "updated_at": iso_now(),
        "phase": "starting",
        "shares": list(SMB_SHARES),
        "discovered_files": 0,
        "discovered_bytes": 0,
        "copied_files": 0,
        "copied_bytes": 0,
        "skipped_existing": 0,
        "errors": 0,
        "passes": 0,
        "current_file": "",
        "last_error": "",
        "done": False,
        "percent": 0.0,
        "last_copy_at": "",
        "total_known": False,
        "total_files": 0,
        "total_bytes": 0,
        "parallel": SMB_PARALLEL,
        "hang_dirs": [],
        "failed_files": [],
        "disk": {"free_gb": 0.0, "used_gb": 0.0, "total_gb": 0.0, "warning": ""},
    }


def load_state() -> dict:
    try:
        with open(SYNC_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = default_state()
        base.update(data)
        return base
    except Exception:
        return default_state()


def save_state(state: dict) -> None:
    try:
        try:
            du = shutil.disk_usage(MEDIA_PATH)
            free_gb = du.free / 1024 ** 3
            state["disk"] = {
                "free_gb": round(free_gb, 1),
                "used_gb": round(du.used / 1024 ** 3, 1),
                "total_gb": round(du.total / 1024 ** 3, 1),
                "warning": "",
            }
            if free_gb < DISK_CRIT_GB:
                state["disk"]["warning"] = f"KRITIS: sisa disk hanya {free_gb:.1f} GB!"
            elif free_gb < DISK_WARN_GB:
                state["disk"]["warning"] = f"Warning: sisa disk {free_gb:.1f} GB."
        except Exception:
            pass

        state["updated_at"] = iso_now()
        if state["done"]:
            state["percent"] = 100.0
        elif state["total_known"] and state["total_files"] > 0:
            state["percent"] = min(
                99.0, 100.0 * state["copied_files"] / state["total_files"])
        else:
            state["percent"] = 0.0
        state["phase"] = "done" if state["done"] else (
            "error" if state["last_error"] else "syncing")

        tmp = SYNC_STATE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, SYNC_STATE_PATH)

        marker = MEDIA_PATH.parent / "SYNC_COMPLETE.txt"
        if state["done"]:
            marker.write_text(
                f"Semua lagu tersalin dari bank ({state['copied_files']} file).\n"
                f"Terakhir diperbarui: {state['updated_at']}\n", encoding="utf-8")
        else:
            marker.unlink(missing_ok=True)
    except Exception as e:
        print(f"[smb_sync] gagal simpan state: {e}", flush=True)


# ---------------------------------------------------------------------------
# Notifikasi webhook (opsional)
# ---------------------------------------------------------------------------
_last_notify = {"done": False, "error": 0.0}


def notify(text: str, state: dict) -> None:
    if not SMB_WEBHOOK_URL:
        return

    def _post():
        try:
            payload = {
                "text": text,
                "content": text,
                "status": state.get("phase"),
                "done": state.get("done"),
                "copied_files": state.get("copied_files"),
                "total_files": state.get("total_files"),
                "errors": state.get("errors"),
                "disk_free_gb": state.get("disk", {}).get("free_gb"),
                "updated_at": state.get("updated_at"),
            }
            req = urllib.request.Request(
                SMB_WEBHOOK_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    threading.Thread(target=_post, daemon=True).start()


def notify_if_needed(state: dict) -> None:
    if state.get("done") and not _last_notify["done"]:
        _last_notify["done"] = True
        notify(f"🎉 Karaoke Bank Sync: SEMUA LAGU TERSALIN "
               f"({state.get('copied_files')} file, {state.get('errors')} error).", state)
    if not state.get("done") and state.get("last_error"):
        now = time.time()
        if now - _last_notify["error"] > NOTIFY_ERROR_COOLDOWN:
            _last_notify["error"] = now
            notify(f"⚠️ Karaoke Bank Sync error: {state.get('last_error')}", state)
    if not state.get("done"):
        _last_notify["done"] = False


# ---------------------------------------------------------------------------
# Auto-detect IP Windows XP (NetBIOS)
# ---------------------------------------------------------------------------
# IP XP bisa berubah-ubah (DHCP). Strategi: pakai SMB_HOST yang dikenal dulu;
# bila gagal, cari XP via NetBIOS: (1) broadcast query nama, lalu (2) scan
# subnet /24 — host dengan port 445/139 terbuka di-reverse-query namanya dan
# dicocokkan dengan SMB_REMOTE_NAME. Hasil terakhir di-cache (_resolved_ip).
_resolved_ip = {"ip": None, "at": 0.0}
_last_scan = 0.0
_detect_lock = threading.Lock()
DETECT_CACHE_SEC = 3600       # hasil deteksi berlaku 1 jam (hindari scan ulang)
DETECT_FAIL_COOLDOWN = 600    # setelah scan gagal, tunggu 10 mnt sebelum scan lagi
DETECT_BROADCAST_TIMEOUT = 3  # detik
DETECT_SCAN_PORT_TIMEOUT = 0.6
DETECT_REVERSE_TIMEOUT = 1.5
DETECT_MAX_WORKERS = 64       # paralel scan port


def _netbios_names_for(ip: str) -> list:
    """Reverse NetBIOS name query: nama mesin di IP tsb ([] bila bukan SMB host)."""
    try:
        from nmb.NetBIOS import NetBIOS
        n = NetBIOS()
        try:
            names = n.queryIPForName(ip, timeout=DETECT_REVERSE_TIMEOUT) or []
            return [str(x) for x in names]
        finally:
            n.close()
    except Exception:
        return []


def _host_has_smb(ip: str) -> bool:
    """True bila port 445/139 terbuka (kemungkinan Windows/SMB)."""
    for port in (445, 139):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(DETECT_SCAN_PORT_TIMEOUT)
            try:
                if s.connect_ex((ip, port)) == 0:
                    return True
            finally:
                s.close()
        except Exception:
            continue
    return False


def _scan_subnet_for_karaoke(base_ip: str) -> list:
    """Scan subnet /24 dari base_ip: cari host yang nama NetBIOS-nya cocok.
    Kembalikan daftar IP yang cocok (urut)."""
    try:
        subnet = ".".join(base_ip.split(".")[:3])
    except Exception:
        return []
    found = []

    def _probe(i: int):
        ip = f"{subnet}.{i}"
        if not _host_has_smb(ip):
            return None
        names = _netbios_names_for(ip)
        for nm in names:
            if nm.strip().upper() == SMB_REMOTE_NAME.strip().upper():
                return ip
        return None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=DETECT_MAX_WORKERS) as ex:
            for r in ex.map(_probe, range(1, 255)):
                if r:
                    found.append(r)
    except Exception:
        pass
    return found


def auto_detect_host() -> str:
    """Cari IP XP secara otomatis. Kembalikan IP atau "" bila tidak ketemu.
    Urutan: (1) broadcast NetBIOS, (2) scan subnet + reverse query."""
    try:
        from nmb.NetBIOS import NetBIOS
        n = NetBIOS()
        try:
            hits = n.queryName(SMB_REMOTE_NAME, timeout=DETECT_BROADCAST_TIMEOUT) or []
        finally:
            n.close()
        if hits:
            return str(hits[0])
    except Exception:
        pass
    # Broadcast sering tidak tembus bridge Docker -> fallback scan subnet
    base = SMB_HOST_ENV or DEFAULT_SMB_HOST
    if base:
        hits = _scan_subnet_for_karaoke(base)
        if hits:
            return hits[0]
    return ""


def get_smb_host() -> str:
    """IP target saat ini: hasil deteksi terakhir (cache), atau SMB_HOST env."""
    with _detect_lock:
        if _resolved_ip["ip"] and (time.time() - _resolved_ip["at"]) < DETECT_CACHE_SEC:
            return _resolved_ip["ip"]
        if SMB_HOST_ENV:
            return SMB_HOST_ENV
        return DEFAULT_SMB_HOST


def _should_rescan() -> bool:
    """True bila cooldown scan (DETECT_FAIL_COOLDOWN) sudah lewat."""
    with _detect_lock:
        return time.time() - _last_scan >= DETECT_FAIL_COOLDOWN


# ---------------------------------------------------------------------------
# Koneksi SMB1
# ---------------------------------------------------------------------------
def connect(timeout: int = 20):
    """Koneksi SMB ke XP. Bila IP yang dikenal gagal (XP pindah IP), lakukan
    auto-detect sekali dan coba ulang ke IP hasil deteksi."""
    target = get_smb_host()
    conn = SMBConnection(SMB_USER, SMB_PASSWORD, SMB_MY_NAME,
                         SMB_REMOTE_NAME, use_ntlm_v2=True, is_direct_tcp=True)
    try:
        if conn.connect(target, SMB_PORT, timeout=timeout):
            return conn
    except Exception:
        pass

    # Gagal ke IP dikenal -> coba auto-detect (XP mungkin pindah IP)
    try:
        conn.close()
    except Exception:
        pass
    if not SMB_AUTO_DETECT:
        raise ConnectionError(f"tidak dapat konek ke {target}:{SMB_PORT}")

    # Gunakan hasil deteksi cache bila masih berlaku; jika tidak, scan ulang
    # hanya bila cooldown sudah lewat (mencegah scan berulang tiap retry).
    with _detect_lock:
        cached = _resolved_ip["ip"]
        cache_fresh = cached and (time.time() - _resolved_ip["at"]) < DETECT_CACHE_SEC
    if cache_fresh and cached and cached != target:
        detected = cached
    elif not _should_rescan():
        detected = _resolved_ip["ip"] or target
    else:
        print(f"[smb_sync] ⚠️ {target} tidak merespons — auto-detect XP "
              f"({SMB_REMOTE_NAME})...", flush=True)
        detected = auto_detect_host()
        with _detect_lock:
            _last_scan = time.time()
            if detected:
                _resolved_ip.update(ip=detected, at=time.time())

    if detected and detected != target:
        print(f"[smb_sync] 🎯 XP ditemukan di {detected} (berubah dari {target})",
              flush=True)
        conn2 = SMBConnection(SMB_USER, SMB_PASSWORD, SMB_MY_NAME,
                              SMB_REMOTE_NAME, use_ntlm_v2=True, is_direct_tcp=True)
        try:
            if conn2.connect(detected, SMB_PORT, timeout=timeout):
                return conn2
        except Exception:
            pass
        try:
            conn2.close()
        except Exception:
            pass
    raise ConnectionError(f"tidak dapat konek ke {detected or target}:{SMB_PORT}")


def is_media_file(name: str) -> bool:
    return Path(name).suffix.lower() in MEDIA_EXTS


def local_path_for(share: str, rel: str) -> Path:
    """Lokasi lokal master: MEDIA_PATH/<share>/<relpath> (struktur dipertahankan)."""
    parts = [sanitize_name(p) for p in Path(rel.lstrip("/")).parts]
    return MEDIA_PATH / sanitize_name(share) / Path(*parts) if parts else None


def transcoded_exists_for(local: Path) -> bool:
    """True bila sumber lokal ini sudah punya MP4 hasil transcode (rel path sama)."""
    try:
        rel = local.resolve().relative_to(MEDIA_PATH.resolve())
    except ValueError:
        return False
    if not rel.suffix:
        return False
    out = TRANSCODED_PATH / rel.with_suffix(".mp4")
    try:
        return out.exists() and out.stat().st_size > 0
    except OSError:
        return False


def copy_file(conn, share: str, remote_rel: str, local: Path) -> None:
    """Salin satu file remote -> lokal via .part + rename atomik."""
    local.parent.mkdir(parents=True, exist_ok=True)
    tmp = local.with_name(local.name + ".part")
    try:
        with open(tmp, "wb") as f:
            conn.retrieveFile(share, remote_rel, f, timeout=120)
        os.replace(tmp, local)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _force_close_socket(conn) -> None:
    """Tutup socket dari thread lain agar operasi SMB yang hang ter-unblock.

    pysmb (SMB1) terkadang tidak menghormati timeout internal untuk koneksi
    lambat/parsial ke Windows XP; recv() bisa memblokir selamanya. Menutup
    socket dari thread lain membuat recv() yang terblokir melempar exception,
    sehingga hang berubah menjadi retry yang terbatas.
    """
    try:
        sock = getattr(conn, "sock", None)
        if sock is not None:
            sock.close()
    except Exception:
        pass


class HangError(ConnectionError):
    """Operasi SMB macet (timeout internal pysmb tidak efektif ke XP) dan
    diputus watchdog. Subclass ConnectionError agar tertangani di worker."""


def safe_listpath(conn, share: str, path: str, label: str = "",
                  timeout: int = 60) -> list:
    """listPath dengan watchdog per-panggilan (default 60 dtk).

    Bila XP tidak membalas (hang), socket ditutup dari thread lain sehingga
    listPath melempar HangError — terbatas, tidak macet selamanya.
    """
    killed = {"flag": False}

    def _kill():
        killed["flag"] = True
        print(f"[smb_sync] ⚠️ hang di listPath: {label} — socket ditutup.",
              flush=True)
        _force_close_socket(conn)

    wd = threading.Timer(timeout, _kill)
    wd.daemon = True
    wd.start()
    try:
        result = conn.listPath(share, path, timeout=timeout)
    except Exception as e:
        if killed["flag"]:
            raise HangError(f"hang: {label}") from e
        raise
    finally:
        wd.cancel()
    return result


def _process_item_guarded(conn, stats, share: str, base: str, recursive: bool) -> None:
    """Jalankan process_item dengan watchdog per item kerja."""
    wd = threading.Timer(ITEM_TIMEOUT_SEC, lambda: _force_close_socket(conn))
    wd.daemon = True
    wd.start()
    try:
        process_item(conn, stats, share, base, recursive)
    finally:
        wd.cancel()


# ---------------------------------------------------------------------------
# State thread-safe untuk worker paralel
# ---------------------------------------------------------------------------
class SyncStats:
    def __init__(self, state: dict):
        self.lock = threading.RLock()
        self.state = state
        self.pass_discovered = 0
        self.pass_bytes = 0
        self.pass_copied = 0
        self.pass_errors = 0
        self.hang_dirs = set(state.get("hang_dirs") or [])
        # File bermasalah konsisten (gagal POISON_THRESHOLD pass berturut-turut)
        self.failed_files = set(state.get(_FILE_FAIL_KEY) or [])
        # Counter kegagalan berturut-turut per file (persisten via state)
        self.file_fail_counts = state.setdefault("file_fail_counts", {})

    def note_hang(self, path: str) -> None:
        """Catat folder yang selalu macet di XP agar dilewati pass berikutnya."""
        with self.lock:
            self.hang_dirs.add(path)
            self.state["hang_dirs"] = sorted(self.hang_dirs)

    def note_file(self, share: str, rel: str, size: int, outcome: str) -> None:
        with self.lock:
            self.pass_discovered += 1
            self.pass_bytes += size
            if self.pass_discovered > self.state["discovered_files"]:
                self.state["discovered_files"] = self.pass_discovered
                self.state["discovered_bytes"] = self.pass_bytes
            self.state["current_file"] = f"{share}{rel}"
            if outcome == "copied":
                self.pass_copied += 1
                self.state["copied_files"] += 1
                self.state["copied_bytes"] += size
                self.state["last_copy_at"] = iso_now()
            elif outcome == "skipped":
                self.state["skipped_existing"] += 1
            # outcome == "error": hanya catat discovered/current_file;
            # penghitungan error dilakukan note_error() agar TIDAK dobel.

    def note_error(self, msg: str) -> None:
        with self.lock:
            self.pass_errors += 1
            self.state["errors"] += 1
            self.state["last_error"] = msg

    def note_file_fail(self, key: str) -> None:
        """Catat satu kegagalan salin file; setelah POISON_THRESHOLD pass
        berturut-turut, file di-skip (masuk state failed_files)."""
        with self.lock:
            n = int(self.file_fail_counts.get(key, 0)) + 1
            self.file_fail_counts[key] = n
            if n >= POISON_THRESHOLD:
                self.failed_files.add(key)
                self.state[_FILE_FAIL_KEY] = sorted(self.failed_files)

    def note_file_success(self, key: str) -> None:
        """File berhasil disalin -> reset counter & cabut dari failed_files."""
        with self.lock:
            self.file_fail_counts.pop(key, None)
            if key in self.failed_files:
                self.failed_files.discard(key)
                self.state[_FILE_FAIL_KEY] = sorted(self.failed_files)


# ---------------------------------------------------------------------------
# Pemrosesan satu item kerja (satu folder top-level)
# ---------------------------------------------------------------------------
def process_item(conn, stats: SyncStats, share: str, base: str, recursive: bool):
    conn_errors = 0
    stack = [(base, 0)]
    while stack:
        path, depth = stack.pop()
        if path in stats.hang_dirs:
            continue  # folder ini macet di XP; lewati pass ini
        try:
            entries = safe_listpath(conn, share, path, label=f"{share}{path}")
        except HangError as e:
            stats.note_hang(path)
            # Socket sudah mati; minta worker reconnect & retry item. Folder
            # hang sudah masuk hang_dirs sehingga retry langsung melewatinya.
            raise ConnectionError(str(e))
        except Exception as e:
            conn_errors += 1
            msg = f"listPath {share}{path}: {type(e).__name__}: {str(e)[:70]}"
            stats.note_error(msg)
            if conn_errors >= CONN_ERROR_THRESHOLD:
                raise ConnectionError(msg)
            # Coba lagi folder ini dalam pass yang sama (setelah folder lain),
            # jangan langsung dibuang dari stack.
            stack.insert(0, (path, depth))
            continue

        conn_errors = 0
        for ent in entries:
            name = ent.filename
            if name in (".", ".."):
                continue
            rel = (path.rstrip("/") + "/" + name) if path != "/" else "/" + name
            if getattr(ent, "isDirectory", False):
                if not recursive:
                    continue
                if name.lower() in SKIP_DIRS:
                    continue
                if depth < MAX_DEPTH:
                    stack.append((rel, depth + 1))
                continue
            if not is_media_file(name):
                continue

            size = getattr(ent, "file_size", 0) or 0
            local = local_path_for(share, rel)
            if local is None:
                continue
            fkey = f"{share}{rel}"
            if fkey in stats.failed_files:
                # File ini gagal POISON_THRESHOLD pass berturut-turut -> skip
                # sementara agar tidak bikin phase=error terus; dicoba lagi saat
                # reset berkala (HANG_RETRY_SEC) atau saat sync tuntas (done).
                stats.note_file(share, rel, size, "skipped")
                continue
            if local.exists() and local.stat().st_size == size:
                stats.note_file(share, rel, size, "skipped")
                continue
            if transcoded_exists_for(local):
                # MP4 hasil transcode sudah ada -> sumber tak perlu disalin
                # ulang dari XP (mencegah loop: salin -> transcode -> hapus).
                stats.note_file(share, rel, size, "skipped")
                continue

            copied = False
            last_err = ""
            last_exc = None
            for attempt in range(3):
                try:
                    copy_file(conn, share, rel, local)
                    copied = True
                    break
                except Exception as e:
                    last_err = f"{name}: {type(e).__name__}: {str(e)[:90]}"
                    last_exc = e
                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))
            if copied:
                stats.note_file_success(fkey)
                stats.note_file(share, rel, size, "copied")
            else:
                stats.note_file(share, rel, size, "error")  # hanya tracking
                stats.note_error(last_err)                   # hitung error sekali
                # Disk penuh jangan di-poison (bukan masalah file-nya)
                if not _is_space_error(last_exc):
                    stats.note_file_fail(fkey)
                conn_errors += 1
                if conn_errors >= CONN_ERROR_THRESHOLD:
                    raise ConnectionError(last_err)


# ---------------------------------------------------------------------------
# Worker: satu thread = satu koneksi SMB
# ---------------------------------------------------------------------------
def worker(stats: SyncStats, work_queue: queue.Queue) -> None:
    conn = None
    try:
        while True:
            try:
                share, base, recursive = work_queue.get_nowait()
            except queue.Empty:
                return
            retries = 3
            while retries > 0:
                try:
                    if conn is None:
                        conn = connect()
                    _process_item_guarded(conn, stats, share, base, recursive)
                    break
                except ConnectionError as e:
                    retries -= 1
                    stats.note_error(f"koneksi terputus: {e}")
                    if conn is not None:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = None
                    time.sleep(5)
                except Exception as e:
                    retries -= 1
                    stats.note_error(f"{type(e).__name__}: {e}")
                    if conn is not None:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = None
                    time.sleep(5)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Bangun daftar item kerja (folder top-level per share)
# ---------------------------------------------------------------------------
SPLIT_THRESHOLD = 6   # pecah folder top-level bila punya > N subfolder langsung


def build_items(conn) -> list:
    """
    Bangun daftar item kerja. Folder top-level raksasa (banyak subfolder
    langsung) dipecah menjadi item per-subfolder agar beban kerja merata
    antar worker paralel (mencegah 1 worker macet di folder terbesar).
    """
    items = []
    for share in SMB_SHARES:
        try:
            entries = safe_listpath(conn, share, "/", label=f"root {share}")
        except HangError as e:
            raise ConnectionError(f"root {share} hang: {e}")
        except Exception as e:
            raise ConnectionError(f"list root {share}: {type(e).__name__}: {e}")
        for ent in entries:
            name = ent.filename
            if name in (".", ".."):
                continue
            if getattr(ent, "isDirectory", False):
                if name.lower() in SKIP_DIRS:
                    continue
                items.append((share, "/" + name, True))
        # File di akar share (tanpa rekursi folder)
        items.append((share, "/", False))

    # Pecah folder raksasa agar load balance
    final = []
    for share, base, recursive in items:
        if not recursive or base == "/":
            final.append((share, base, recursive))
            continue
        if base in _build_hang:
            final.append((share, base, recursive))  # pernah macet -> utuh saja
            continue
        try:
            subdirs = [e.filename for e in
                       safe_listpath(conn, share, base, label=f"split {share}{base}")
                       if getattr(e, "isDirectory", False)
                       and e.filename not in (".", "..")
                       and e.filename.lower() not in SKIP_DIRS]
        except HangError:
            _build_hang.add(base)
            final.append((share, base, recursive))  # macet -> utuh saja
            continue
        except Exception:
            final.append((share, base, recursive))  # gagal list -> utuh saja
            continue
        if len(subdirs) > SPLIT_THRESHOLD:
            for sd in subdirs:
                final.append((share, base.rstrip("/") + "/" + sd, True))
            final.append((share, base, False))  # file langsung di folder ini
        else:
            final.append((share, base, True))
    return final


# ---------------------------------------------------------------------------
# Pass paralel
# ---------------------------------------------------------------------------
def do_pass(state: dict) -> bool:
    """
    Satu pass penuh (paralel). Kembalikan True bila tidak ada yang perlu
    disalin dan tidak ada error (== semua sudah tersinkron).
    """
    if is_paused():
        # Panel admin menjeda sync — jangan mulai pass baru.
        state["paused"] = True
        save_state(state)
        return False
    stats = SyncStats(state)
    with stats.lock:
        state["discovered_files"] = 0
        state["discovered_bytes"] = 0
        state["last_error"] = ""

    main_conn = None
    watchdog = None
    try:
        main_conn = connect()

        def _kill_main():
            print("[smb_sync] ⚠️ watchdog: build_items terlalu lama, "
                  "koneksi utama ditutup (akan retry pass).", flush=True)
            _force_close_socket(main_conn)

        watchdog = threading.Timer(BUILD_TIMEOUT_SEC, _kill_main)
        watchdog.daemon = True
        watchdog.start()
        items = build_items(main_conn)
        # Sinkronkan folder hang dari split (build_items) ke state agar
        # persist lintas restart dan langsung dilewati process_item.
        with stats.lock:
            stats.hang_dirs.update(_build_hang)
            state["hang_dirs"] = sorted(stats.hang_dirs)
    finally:
        if watchdog is not None:
            watchdog.cancel()
        if main_conn is not None:
            try:
                main_conn.close()
            except Exception:
                pass

    if not items:
        save_state(state)
        return True

    print(f"[smb_sync] pass: {len(items)} item kerja, "
          f"{min(SMB_PARALLEL, len(items))} worker", flush=True)

    work_queue = queue.Queue()
    for it in items:
        work_queue.put(it)

    n_workers = min(SMB_PARALLEL, len(items))
    threads = [
        threading.Thread(target=worker, args=(stats, work_queue), daemon=True)
        for _ in range(n_workers)
    ]
    for t in threads:
        t.start()

    while any(t.is_alive() for t in threads):
        time.sleep(STATE_SAVE_SEC)
        with stats.lock:
            save_state(state)
            notify_if_needed(state)

    for t in threads:
        t.join(timeout=2)

    with stats.lock:
        state["discovered_files"] = max(state["discovered_files"], stats.pass_discovered)
        state["discovered_bytes"] = max(state["discovered_bytes"], stats.pass_bytes)
        state["total_known"] = True
        state["total_files"] = state["discovered_files"]
        state["total_bytes"] = state["discovered_bytes"]
        done_now = (stats.pass_copied == 0 and stats.pass_errors == 0)
    save_state(state)
    return done_now


# ---------------------------------------------------------------------------
# Runner kontinu
# ---------------------------------------------------------------------------
def run_forever() -> None:
    print(f"[smb_sync] mulai. host={get_smb_host()} (auto-detect={'ON' if SMB_AUTO_DETECT else 'OFF'}) "
          f"shares={SMB_SHARES} media={MEDIA_PATH} parallel={SMB_PARALLEL}", flush=True)
    print(f"[smb_sync] ekstensi: {sorted(MEDIA_EXTS)}", flush=True)
    if SMB_WEBHOOK_URL:
        print("[smb_sync] notifikasi webhook: aktif", flush=True)

    state = load_state()
    state["last_error"] = ""
    state["parallel"] = SMB_PARALLEL
    _build_hang.update(state.get("hang_dirs") or [])
    save_state(state)

    _last_hang_clear = time.time()
    while True:
        try:
            heartbeat()
            _wait_if_paused(state)
            done_now = do_pass(state)
            state["passes"] += 1
            state["done"] = done_now
            state["phase"] = "done" if done_now else "syncing"
            save_state(state)
            notify_if_needed(state)
            if done_now:
                # reset: coba lagi semua folder bermasalah setelah tuntas
                state["hang_dirs"] = []
                state[_FILE_FAIL_KEY] = []
                state["file_fail_counts"] = {}
                _build_hang.clear()
                print("[smb_sync] ✅ SEMUA LAGU TERSALIN. Memantau lagu baru...",
                      flush=True)
                time.sleep(DONE_RECHECK_SEC)
            else:
                # Coba ulang folder/file bermasalah secara berkala, agar
                # XP yang hanya sesaat lambat tidak terlewat selamanya.
                if time.time() - _last_hang_clear >= HANG_RETRY_SEC:
                    state["hang_dirs"] = []
                    state[_FILE_FAIL_KEY] = []
                    state["file_fail_counts"] = {}
                    _build_hang.clear()
                    _last_hang_clear = time.time()
                print("[smb_sync] ada file tersisa, lanjut pass berikutnya...",
                      flush=True)
                time.sleep(PASS_PAUSE_SEC)
        except Exception as e:
            state["last_error"] = f"{type(e).__name__}: {e}"
            state["phase"] = "error"
            # Kegagalan koneksi (XP mati/lambat) JANGAN meng-poison file —
            # poison hanya untuk kegagalan file-spesifik saat koneksi sehat.
            state[_FILE_FAIL_KEY] = []
            state["file_fail_counts"] = {}
            save_state(state)
            notify_if_needed(state)
            print(f"[smb_sync] error: {state['last_error']} — coba lagi 30 dtk.",
                  flush=True)
            time.sleep(30)


def sync_once() -> dict:
    """Satu pass sinkronisasi (dipakai untuk test / task terjadwal)."""
    state = load_state()
    done_now = do_pass(state)
    state["done"] = done_now
    save_state(state)
    return {"done": done_now, **{k: v for k, v in state.items()
                                 if k != "shares"}}


if __name__ == "__main__":
    run_forever()
