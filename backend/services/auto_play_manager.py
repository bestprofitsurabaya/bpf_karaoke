"""
Auto Play Manager - Otomatis memutar lagu berikutnya setelah lagu selesai
+ AI Vocal Separation menggunakan Spleeter
"""
import asyncio
import subprocess
import os
from pathlib import Path
from datetime import datetime
import json

class AutoPlayManager:
    def __init__(self):
        self.auto_play_enabled = True
        self.gap_between_songs = 5  # Jeda 5 detik antar lagu
        self.vocal_separation_enabled = False
        self.separated_tracks = {}  # Cache hasil separasi
        
    async def play_next_in_queue(self, room_id: str, socket_server, db_session):
        """
        Dipanggil saat lagu selesai (video ended)
        Auto-play lagu berikutnya di queue dengan jeda 5 detik
        """
        try:
            from main import QueueItem, Song, async_session
            from sqlalchemy import select, update
            
            # Tunggu jeda 5 detik
            await asyncio.sleep(self.gap_between_songs)
            
            async with db_session() as session:
                # Ambil antrian waiting pertama
                result = await session.execute(
                    select(QueueItem)
                    .where(
                        QueueItem.room_id == room_id,
                        QueueItem.status == "waiting"
                    )
                    .order_by(QueueItem.priority.desc(), QueueItem.created_at.asc())
                    .limit(1)
                )
                next_item = result.scalar_one_or_none()
                
                if next_item:
                    # Update status ke playing
                    await session.execute(
                        update(QueueItem)
                        .where(QueueItem.id == next_item.id)
                        .values(status="playing", played_at=datetime.utcnow())
                    )
                    
                    # Update play count
                    await session.execute(
                        update(Song)
                        .where(Song.id == next_item.song_id)
                        .values(play_count=Song.play_count + 1)
                    )
                    
                    await session.commit()
                    
                    # Emit event ke player
                    await socket_server.emit("play", {
                        "song_id": next_item.song_id,
                        "queue_id": next_item.id,
                        "auto_play": True
                    }, room=room_id)
                    
                    # Notify queue update
                    await socket_server.emit("queue_updated", {
                        "room_id": room_id,
                        "action": "auto_play_next"
                    }, room=room_id)
                    
                    return {
                        "status": "playing_next",
                        "song_id": next_item.song_id,
                        "queue_id": next_item.id
                    }
                else:
                    # Tidak ada lagu di antrian
                    await socket_server.emit("queue_empty", {
                        "room_id": room_id,
                        "message": "Antrian kosong, silakan tambah lagu"
                    }, room=room_id)
                    
                    return {
                        "status": "queue_empty",
                        "message": "No more songs in queue"
                    }
        except Exception as e:
            print(f"AutoPlay error: {e}")
            return {"status": "error", "error": str(e)}

    def separate_vocals(self, audio_path: str, output_dir: str = "/media/separated") -> dict:
        """
        AI Vocal Separation menggunakan Spleeter/Demucs
        Memisahkan vokal dari instrumental
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            file_name = Path(audio_path).stem
            
            # Cek cache
            cache_key = f"{file_name}_instrumental"
            if cache_key in self.separated_tracks:
                return self.separated_tracks[cache_key]
            
            # Coba pakai spleeter (jika terinstall)
            try:
                cmd = [
                    "spleeter", "separate",
                    "-p", "spleeter:2stems",  # vocals + accompaniment
                    "-o", str(output_path),
                    audio_path
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if process.returncode == 0:
                    instrumental_path = output_path / file_name / "accompaniment.wav"
                    vocals_path = output_path / file_name / "vocals.wav"
                    
                    result = {
                        "status": "success",
                        "instrumental_path": str(instrumental_path),
                        "vocals_path": str(vocals_path),
                        "method": "spleeter"
                    }
                    
                    # Cache hasil
                    self.separated_tracks[cache_key] = result
                    return result
                    
            except FileNotFoundError:
                pass  # Spleeter tidak terinstall
            
            # Fallback: Gunakan FFmpeg untuk vocal reduction sederhana
            return self._ffmpeg_vocal_reduction(audio_path, output_path, file_name)
            
        except Exception as e:
            print(f"Vocal separation error: {e}")
            return {"status": "error", "error": str(e)}
    
    def _ffmpeg_vocal_reduction(self, audio_path: str, output_path: Path, file_name: str) -> dict:
        """
        Fallback: Vocal reduction menggunakan FFmpeg
        Teknik: Phase cancellation + frequency filtering
        """
        try:
            instrumental_file = output_path / f"{file_name}_instrumental.mp3"
            
            # FFmpeg vocal reduction filter
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-af", "pan='stereo|c0=c0-c1|c1=c1-c0',highpass=f=200,lowpass=f=8000",
                "-q:a", "2",
                str(instrumental_file)
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if process.returncode == 0:
                return {
                    "status": "success",
                    "instrumental_path": str(instrumental_file),
                    "method": "ffmpeg_phase_cancel",
                    "note": "Basic vocal reduction (install spleeter for better quality)"
                }
            else:
                return {
                    "status": "error",
                    "error": f"FFmpeg failed: {process.stderr[:200]}"
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_key_change_ffmpeg(self, semitones: int) -> str:
        """
        Generate FFmpeg filter untuk pitch/key change
        +1 = naik 1 semitone, -1 = turun 1 semitone
        """
        if semitones == 0:
            return ""
        
        # FFmpeg rubberband filter untuk pitch shifting
        # atempo menyesuaikan tempo agar tetap sama
        pitch_factor = 2 ** (semitones / 12)  # Konversi semitone ke ratio
        tempo_factor = 1.0 / pitch_factor  # Kompensasi tempo
        
        return f"rubberband=pitch={pitch_factor}:tempo={tempo_factor}"


# Singleton instance
auto_play_manager = AutoPlayManager()
