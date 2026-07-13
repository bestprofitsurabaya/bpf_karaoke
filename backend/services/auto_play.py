"""
Auto-Play Service - Otomatis putar lagu berikutnya setelah 1 lagu selesai
"""

import asyncio
from datetime import datetime

class AutoPlayManager:
    def __init__(self):
        self.room_timers = {}  # room_id -> asyncio.Task
        self.room_current = {}  # room_id -> current_queue_id
    
    async def play_next_after_delay(self, room_id: str, sio, async_session, QueueItem, Song, delay: int = 5):
        """
        Setelah 1 lagu selesai, tunggu `delay` detik, lalu auto-play lagu berikutnya
        """
        try:
            # Tunggu jeda
            await asyncio.sleep(delay)
            
            # Ambil antrian berikutnya
            from sqlalchemy import select
            async with async_session() as session:
                result = await session.execute(
                    select(QueueItem)
                    .where(QueueItem.room_id == room_id, QueueItem.status == "waiting")
                    .order_by(QueueItem.created_at)
                    .limit(1)
                )
                next_song = result.scalar_one_or_none()
                
                if next_song:
                    # Update status ke playing
                    next_song.status = "playing"
                    next_song.played_at = datetime.utcnow()
                    
                    # Update play count
                    song_result = await session.execute(
                        select(Song).where(Song.id == next_song.song_id)
                    )
                    song = song_result.scalar_one_or_none()
                    if song:
                        song.play_count = (song.play_count or 0) + 1
                    
                    await session.commit()
                    
                    # Emit ke player
                    await sio.emit("play", {
                        "song_id": next_song.song_id,
                        "queue_id": next_song.id
                    }, room=room_id)
                    
                    # Update queue untuk operator
                    await sio.emit("queue_updated", {"room_id": room_id}, room=room_id)
                    
                    print(f"🎵 Auto-play next: song_id={next_song.song_id} in room={room_id}")
                else:
                    # Tidak ada antrian, emit idle
                    await sio.emit("ctrl", {"action": "idle"}, room=room_id)
                    await sio.emit("queue_updated", {"room_id": room_id}, room=room_id)
                    print(f"📭 Queue empty in room={room_id}")
                    
        except Exception as e:
            print(f"❌ Auto-play error: {e}")
    
    def schedule_next(self, room_id: str, sio, async_session, QueueItem, Song, delay: int = 5):
        """Jadwalkan auto-play berikutnya"""
        # Cancel timer yang ada
        if room_id in self.room_timers:
            self.room_timers[room_id].cancel()
        
        # Buat timer baru
        loop = asyncio.get_event_loop()
        self.room_timers[room_id] = loop.create_task(
            self.play_next_after_delay(room_id, sio, async_session, QueueItem, Song, delay)
        )

# Singleton
auto_play_manager = AutoPlayManager()
