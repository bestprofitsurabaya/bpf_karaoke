"""
MinIO Client Service
Untuk upload dan download media dari Object Storage
"""

import os
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import io

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False


class MinIOClient:
    """MinIO Object Storage Client"""
    
    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'karaoke_minio:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'karaoke_admin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', '')
        self.bucket = os.getenv('MINIO_BUCKET', 'karaoke-media')
        self.public_url = os.getenv('MINIO_PUBLIC_URL', '')
        self.client = None
        
        if MINIO_AVAILABLE:
            self._init_client()
    
    def _init_client(self):
        """Initialize MinIO client"""
        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=False  # Internal Docker network
            )
            
            # Ensure bucket exists
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"Created MinIO bucket: {self.bucket}")
                
        except Exception as e:
            print(f"MinIO connection failed: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if MinIO is available"""
        return self.client is not None and MINIO_AVAILABLE
    
    def upload_file(self, local_path: str, object_name: str = None) -> Dict:
        """
        Upload file ke MinIO
        """
        if not self.is_available():
            return {"error": "MinIO not available", "status": "failed"}
        
        file_path = Path(local_path)
        if not file_path.exists():
            return {"error": "File not found", "status": "failed"}
        
        if object_name is None:
            object_name = f"karaoke/{file_path.name}"
        
        try:
            result = self.client.fput_object(
                self.bucket,
                object_name,
                str(file_path),
                content_type=self._get_content_type(file_path.suffix)
            )
            
            return {
                "status": "success",
                "object_name": object_name,
                "size": file_path.stat().st_size,
                "public_url": f"{self.public_url}/{self.bucket}/{object_name}",
                "etag": result.etag
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def download_file(self, object_name: str, local_path: str) -> Dict:
        """
        Download file dari MinIO
        """
        if not self.is_available():
            return {"error": "MinIO not available", "status": "failed"}
        
        try:
            self.client.fget_object(
                self.bucket,
                object_name,
                local_path
            )
            
            return {
                "status": "success",
                "local_path": local_path
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def get_presigned_url(self, object_name: str, expires_hours: int = 24) -> Optional[str]:
        """
        Generate presigned URL untuk akses file
        """
        if not self.is_available():
            return None
        
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(hours=expires_hours)
            )
            return url
        except Exception:
            return None
    
    def list_objects(self, prefix: str = "karaoke/") -> List[Dict]:
        """
        List semua object di bucket
        """
        if not self.is_available():
            return []
        
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix)
            return [
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
                }
                for obj in objects
            ]
        except Exception:
            return []
    
    def delete_object(self, object_name: str) -> Dict:
        """
        Hapus object dari MinIO
        """
        if not self.is_available():
            return {"error": "MinIO not available", "status": "failed"}
        
        try:
            self.client.remove_object(self.bucket, object_name)
            return {"status": "success", "deleted": object_name}
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    def get_stats(self) -> Dict:
        """
        Dapatkan statistik bucket
        """
        if not self.is_available():
            return {"available": False}
        
        try:
            objects = list(self.client.list_objects(self.bucket))
            total_size = sum(obj.size for obj in objects)
            
            return {
                "available": True,
                "bucket": self.bucket,
                "total_objects": len(objects),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "endpoint": self.endpoint
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def _get_content_type(self, extension: str) -> str:
        """Get MIME type dari extension"""
        mime_types = {
            '.mp4': 'video/mp4',
            '.mkv': 'video/x-matroska',
            '.avi': 'video/x-msvideo',
            '.mp3': 'audio/mpeg',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')


# Singleton instance
minio_client = MinIOClient()
