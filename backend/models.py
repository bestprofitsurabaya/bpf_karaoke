"""
SQLAlchemy Models - Song, QueueItem, User, PlaybackHistory, OperatorFavorite, Room
PT BESTPROFIT FUTURES SURABAYA
"""
from datetime import datetime
from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, ForeignKey, Index, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Song(Base):
    __tablename__ = "songs"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    title = mapped_column(String(500), nullable=False, index=True)
    artist = mapped_column(String(300), nullable=True, index=True)
    genre = mapped_column(String(100), nullable=True, index=True)
    album = mapped_column(String(300), nullable=True)
    year = mapped_column(Integer, nullable=True)
    language = mapped_column(String(50), nullable=True)
    file_path = mapped_column(String(1000), nullable=False)
    file_format = mapped_column(String(10), nullable=True)
    duration = mapped_column(Integer, nullable=True)
    has_vocal_track = mapped_column(Boolean, default=False)
    vocal_channel = mapped_column(String(20), nullable=True)
    play_count = mapped_column(Integer, default=0)
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QueueItem(Base):
    __tablename__ = "queue"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id = mapped_column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    room_id = mapped_column(String(100), nullable=False, default="default", index=True)
    requester_name = mapped_column(String(100), nullable=True)
    status = mapped_column(String(20), default="waiting")
    priority = mapped_column(Integer, default=0)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    played_at = mapped_column(DateTime, nullable=True)
    completed_at = mapped_column(DateTime, nullable=True)


class User(Base):
    """User model dengan ISO 27001 security fields"""
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    username = mapped_column(String(100), unique=True, nullable=False)
    password_hash = mapped_column(String(200), nullable=False)
    role = mapped_column(String(20), default="operator")
    is_active = mapped_column(Boolean, default=True)
    # ISO 27001 A.9.2.4: Force password change on first login
    requires_password_change = mapped_column(Boolean, default=True)
    # ISO 27001 A.9.4.2: Brute-force protection
    failed_login_attempts = mapped_column(Integer, default=0)
    locked_until = mapped_column(DateTime, nullable=True)
    # ISO 27001 A.9.4.3: Password history & audit
    last_password_change = mapped_column(DateTime, nullable=True)
    password_history = mapped_column(Text, nullable=True)  # JSON: list of old hashes
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlaybackHistory(Base):
    """Playback history untuk audit & rekomendasi"""
    __tablename__ = "playback_history"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id = mapped_column(Integer, ForeignKey("songs.id", ondelete="SET NULL"), nullable=True)
    room_id = mapped_column(String(100), nullable=False, default="default", index=True)
    title = mapped_column(String(500), nullable=True)
    artist = mapped_column(String(300), nullable=True)
    played_at = mapped_column(DateTime, default=datetime.utcnow, index=True)


class OperatorFavorite(Base):
    """Lagu favorit operator untuk akses cepat"""
    __tablename__ = "operator_favorites"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    song_id = mapped_column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class Room(Base):
    __tablename__ = "rooms"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String(100), nullable=False, unique=True)
    description = mapped_column(String(500), nullable=True)
    capacity = mapped_column(Integer, default=10)
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RoomSession(Base):
    """
    Sesi pemakaian room (durasi penggunaan).
    - end_time: target selesai (absolut). Bisa dari durasi menit atau jam yang
      dikehendaki admin (misal berakhir jam 22:00).
    - status: 'active' | 'completed' (expired auto-completed saat diakses)
    """
    __tablename__ = "room_sessions"
    __table_args__ = (
        # Mencegah dua sesi aktif untuk room yang sama (race condition)
        Index(
            "uq_room_sessions_active", "room_id", unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id = mapped_column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = mapped_column(DateTime, nullable=True)      # target selesai
    duration_minutes = mapped_column(Integer, nullable=True)  # durasi sewa (menit)
    ended_at = mapped_column(DateTime, nullable=True)      # waktu selesai aktual
    status = mapped_column(String(20), default="active", index=True)
    created_by = mapped_column(String(100), nullable=True)
    note = mapped_column(String(500), nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
