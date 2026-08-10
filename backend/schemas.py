"""
Pydantic Schemas - Request/Response models
PT BESTPROFIT FUTURES SURABAYA
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class SongUpdate(BaseModel):
    title: str
    artist: Optional[str] = None
    genre: Optional[str] = None


class SR(BaseModel):
    id: int
    title: str
    artist: Optional[str] = None
    genre: Optional[str] = None
    file_path: str
    play_count: int = 0
    is_active: bool = True
    # 'mp4' | 'youtube' (yt:<id>) | dll; dipakai player utk memilih sumber playback
    file_format: Optional[str] = None
    duration: Optional[int] = None
    class Config:
        from_attributes = True


class QR(BaseModel):
    song_id: int
    room_id: str = "default"
    requester_name: Optional[str] = Field(None, max_length=50)


class QResp(BaseModel):
    id: int
    song_id: int
    room_id: str
    status: str
    priority: int
    created_at: datetime
    requester_name: Optional[str] = None
    song: Optional[SR] = None
    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    id: int
    song_id: Optional[int] = None
    room_id: str
    title: Optional[str] = None
    artist: Optional[str] = None
    played_at: datetime
    class Config:
        from_attributes = True


class FavoriteResponse(BaseModel):
    id: int
    song_id: int
    created_at: datetime
    song: Optional[SR] = None
    class Config:
        from_attributes = True


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capacity: int = 10


class SessionStart(BaseModel):
    """Mulai sesi room: pilih durasi (menit) ATAU waktu selesai absolut."""
    duration_minutes: Optional[int] = None
    end_time: Optional[datetime] = None
    note: Optional[str] = None


class SessionExtend(BaseModel):
    """Perpanjang sesi room: tambah menit ATAU set waktu selesai baru."""
    minutes: Optional[int] = None
    end_time: Optional[datetime] = None


class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    capacity: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True
