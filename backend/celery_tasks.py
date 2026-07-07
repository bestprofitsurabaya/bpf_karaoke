"""
Celery Tasks untuk Background Processing
- Transcoding video otomatis
- Upload ke MinIO
- Cleanup file master
"""

import os
import subprocess
import json
import time
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import asyncio

from celery_app import app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Konfigurasi
MEDIA_PATH = Path(os.getenv('MEDIA_PATH', '/media/lagu'))
TRANSCODED_PATH = Path('/media/transcoded')
MASTER_EXTENSIONS = {'.mpg', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.vob', '.dat'}
TARGET_EXTENSION = '.mp4'
TARGET_CODEC = 'libx264'
TARGET_AUDIO_CODEC = 'aac'
TARGET_PRESET = 'medium'  # fast, medium, slow
TARGET_CRF = '23'  # 18-28, lower = better quality

# MinIO Configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'karaoke_minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'karaoke_admin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', '')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'karaoke-media')
MINIO_PUBLIC_URL = os.getenv('MINIO_PUBLIC_URL', '')

# ============================================
# TASK: Scan untuk file master baru
# ============================================

@app.task(name='celery_tasks.scan_for_new_media')
def scan_for_new_media():
    """
    Scan folder media untuk file master (.mpg, .avi, .mov) yang belum di-transcode
    """
    logger.info(f"Scanning {MEDIA_PATH} for new master files...")
    
    if not MEDIA_PATH.exists():
        logger.error(f"Media path {MEDIA_PATH} does not exist")
        return {"error": "Media path not found"}
    
    found_files = []
    
    for ext in MASTER_EXTENSIONS:
        for file_path in MEDIA_PATH.rglob(f'*{ext}'):
            # Skip jika sudah ada versi transcoded-nya
            transcoded_file = TRANSCODED_PATH / f"{file_path.stem}{TARGET_EXTENSION}"
            
            if not transcoded_file.exists():
                found_files.append(str(file_path))
                # Kirim task transcoding
                transcode_video.delay(str(file_path))
                logger.info(f"Queued transcoding: {file_path.name}")
    
    return {
        "scanned": True,
        "found_master_files": len(found_files),
        "files": found_files,
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# TASK: Transcoding Video
# ============================================

@app.task(name='celery_tasks.transcode_video', bind=True)
def transcode_video(self, input_path: str):
    """
    Transcode video master ke format MP4 (H.264 + AAC)
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        return {"error": f"File not found: {input_path}", "status": "failed"}
    
    # Skip jika bukan file master
    if input_file.suffix.lower() not in MASTER_EXTENSIONS:
        return {"message": f"Not a master file: {input_file.suffix}", "status": "skipped"}
    
    # Buat folder transcoded jika belum ada
    TRANSCODED_PATH.mkdir(parents=True, exist_ok=True)
    
    output_file = TRANSCODED_PATH / f"{input_file.stem}{TARGET_EXTENSION}"
    
    # Skip jika sudah ada
    if output_file.exists():
        logger.info(f"Already transcoded: {output_file.name}")
        # Hapus file master
        cleanup_master_file(str(input_file))
        return {"message": "Already transcoded", "status": "skipped", "output": str(output_file)}
    
    logger.info(f"🎬 Transcoding: {input_file.name} → {output_file.name}")
    
    # Update task state
    self.update_state(state='PROGRESS', meta={'stage': 'transcoding', 'file': input_file.name})
    
    try:
        # Command FFmpeg untuk transcoding
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-c:v', TARGET_CODEC,
            '-preset', TARGET_PRESET,
            '-crf', TARGET_CRF,
            '-c:a', TARGET_AUDIO_CODEC,
            '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-movflags', '+faststart',  # Optimize for web streaming
            '-y',  # Overwrite output
            str(output_file)
        ]
        
        # Jalankan FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr[:500]}")
            return {
                "error": "FFmpeg transcoding failed",
                "details": stderr[:500],
                "status": "failed"
            }
        
        # Dapatkan informasi file output
        output_size = output_file.stat().st_size
        input_size = input_file.stat().st_size
        compression_ratio = (1 - output_size / input_size) * 100 if input_size > 0 else 0
        
        logger.info(f"✅ Transcoding complete: {output_file.name} ({output_size / 1024 / 1024:.1f} MB, {compression_ratio:.1f}% smaller)")
        
        # Update database path
        update_song_file_path(str(input_file), str(output_file))
        
        # Upload ke MinIO
        upload_to_minio.delay(str(output_file))
        
        # Hapus file master setelah sukses
        cleanup_master_file(str(input_file))
        
        return {
            "status": "completed",
            "input": str(input_file),
            "output": str(output_file),
            "input_size_mb": round(input_size / 1024 / 1024, 2),
            "output_size_mb": round(output_size / 1024 / 1024, 2),
            "compression_ratio": round(compression_ratio, 1),
            "timestamp": datetime.now().isoformat()
        }
        
    except FileNotFoundError:
        logger.error("FFmpeg not installed!")
        return {"error": "FFmpeg not found", "status": "failed"}
    except Exception as e:
        logger.error(f"Transcoding error: {str(e)}")
        return {"error": str(e), "status": "failed"}


# ============================================
# TASK: Upload ke MinIO
# ============================================

@app.task(name='celery_tasks.upload_to_minio', bind=True)
def upload_to_minio(self, file_path: str):
    """
    Upload file hasil transcoding ke MinIO Object Storage
    """
    try:
        from minio import Minio
        from minio.error import S3Error
    except ImportError:
        logger.warning("MinIO client not installed, skipping upload")
        return {"status": "skipped", "reason": "MinIO client not available"}
    
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {"error": f"File not found: {file_path}", "status": "failed"}
    
    self.update_state(state='PROGRESS', meta={'stage': 'uploading', 'file': file_path.name})
    
    try:
        # Initialize MinIO client
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False  # Internal network
        )
        
        # Check bucket
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info(f"Created bucket: {MINIO_BUCKET}")
        
        # Upload file
        object_name = f"karaoke/{file_path.name}"
        file_size = file_path.stat().st_size
        
        result = client.fput_object(
            MINIO_BUCKET,
            object_name,
            str(file_path),
            content_type='video/mp4'
        )
        
        # Generate public URL
        public_url = f"{MINIO_PUBLIC_URL}/{MINIO_BUCKET}/{object_name}"
        
        logger.info(f"✅ Uploaded to MinIO: {object_name} ({file_size / 1024 / 1024:.1f} MB)")
        
        return {
            "status": "completed",
            "object_name": object_name,
            "bucket": MINIO_BUCKET,
            "size_mb": round(file_size / 1024 / 1024, 2),
            "public_url": public_url,
            "etag": result.etag,
            "timestamp": datetime.now().isoformat()
        }
        
    except S3Error as e:
        logger.error(f"MinIO error: {str(e)}")
        return {"error": str(e), "status": "failed"}
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return {"error": str(e), "status": "failed"}


# ============================================
# TASK: Sync media ke MinIO secara periodik
# ============================================

@app.task(name='celery_tasks.sync_media_to_minio')
def sync_media_to_minio():
    """
    Sync semua file transcoded ke MinIO
    """
    logger.info("Starting MinIO sync...")
    
    if not TRANSCODED_PATH.exists():
        return {"message": "No transcoded files found"}
    
    synced = 0
    skipped = 0
    
    for file_path in TRANSCODED_PATH.rglob(f'*{TARGET_EXTENSION}'):
        # Cek apakah file sudah di MinIO (simple check: cek file age)
        file_age = time.time() - file_path.stat().st_mtime
        
        if file_age < 3600:  # File lebih muda dari 1 jam
            upload_to_minio.delay(str(file_path))
            synced += 1
        else:
            skipped += 1
    
    return {
        "synced": synced,
        "skipped": skipped,
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# TASK: Cleanup failed transcodes
# ============================================

@app.task(name='celery_tasks.cleanup_failed_transcodes')
def cleanup_failed_transcodes():
    """
    Bersihkan file transcoding yang gagal
    """
    logger.info("Cleaning up failed transcodes...")
    
    cleaned = 0
    
    if TRANSCODED_PATH.exists():
        for file_path in TRANSCODED_PATH.rglob('*'):
            if file_path.is_file():
                # Hapus file yang ukurannya 0 (gagal transcode)
                if file_path.stat().st_size == 0:
                    file_path.unlink()
                    cleaned += 1
                    logger.info(f"Removed empty file: {file_path.name}")
    
    return {
        "cleaned": cleaned,
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# HELPER FUNCTIONS
# ============================================

def cleanup_master_file(file_path: str):
    """
    Hapus file master setelah berhasil di-transcode
    """
    try:
        file = Path(file_path)
        if file.exists() and file.suffix.lower() in MASTER_EXTENSIONS:
            # Cek apakah file transcoded sudah ada
            transcoded = TRANSCODED_PATH / f"{file.stem}{TARGET_EXTENSION}"
            if transcoded.exists() and transcoded.stat().st_size > 0:
                file.unlink()
                logger.info(f"🗑️ Removed master file: {file.name}")
                return True
    except Exception as e:
        logger.error(f"Failed to remove master file: {str(e)}")
    
    return False


def update_song_file_path(old_path: str, new_path: str):
    """
    Update file_path di database (sync)
    """
    try:
        import psycopg2
        import os
        
        db_url = os.getenv('DATABASE_URL', '')
        # Parse connection string
        conn = psycopg2.connect(db_url.replace('+asyncpg', ''))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE songs SET file_path = %s, file_format = 'mp4' WHERE file_path = %s",
            (new_path, old_path)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"📝 Updated database: {old_path} → {new_path}")
        return True
        
    except Exception as e:
        logger.error(f"Database update failed: {str(e)}")
        return False


def get_file_info(file_path: str) -> Dict:
    """
    Dapatkan informasi file
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return info
    except Exception as e:
        logger.error(f"Failed to get file info: {str(e)}")
    
    return {}


def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
    """
    Hitung hash file
    """
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception:
        return None
