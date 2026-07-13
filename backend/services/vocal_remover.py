"""
AI Vocal Removal Service
- Primary: FFmpeg Phase Cancellation (ringan, instant)
- Secondary: Demucs (lebih akurat, butuh GPU opsional)
- Fallback: Simple channel extraction
"""

import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

class VocalRemover:
    def __init__(self, media_path: str = "/media/lagu"):
        self.media_path = Path(media_path)
        self.output_dir = Path("/media/transcoded/vocal_removed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache = {}  # Cache hasil vocal removal
        
    async def remove_vocal(
        self, 
        file_path: str, 
        method: str = "ffmpeg",  # ffmpeg, demucs, channel
        song_id: Optional[int] = None
    ) -> Dict:
        """
        Remove vocal from audio/video file
        
        Methods:
        - ffmpeg: Fast phase cancellation (default, < 1 detik)
        - demucs: AI-based separation (akurat, 30-60 detik)
        - channel: Extract left/right channel only
        """
        input_file = Path(file_path)
        
        if not input_file.exists():
            return {"error": "File not found", "status": "failed"}
        
        # Cek cache
        cache_key = f"{input_file.stem}_{method}"
        if cache_key in self.cache:
            cached_path = self.cache[cache_key]
            if Path(cached_path).exists():
                return {
                    "status": "completed",
                    "file": cached_path,
                    "method": method,
                    "cached": True
                }
        
        try:
            if method == "ffmpeg":
                result = await self._ffmpeg_vocal_remove(input_file)
            elif method == "demucs":
                result = await self._demucs_vocal_remove(input_file)
            elif method == "channel":
                result = await self._channel_extraction(input_file, "left")
            else:
                result = await self._ffmpeg_vocal_remove(input_file)
            
            # Cache result
            if result.get("status") == "completed":
                self.cache[cache_key] = result["file"]
            
            return result
            
        except Exception as e:
            # Fallback ke FFmpeg jika method lain gagal
            if method != "ffmpeg":
                print(f"⚠️ {method} failed, falling back to FFmpeg: {e}")
                return await self._ffmpeg_vocal_remove(input_file)
            return {"error": str(e), "status": "failed"}
    
    async def _ffmpeg_vocal_remove(self, input_file: Path) -> Dict:
        """
        FFmpeg Phase Cancellation Method
        - Sangat cepat (< 1 detik untuk file normal)
        - Menggunakan phase inversion untuk menghilangkan center audio
        """
        output_file = self.output_dir / f"{input_file.stem}_instrumental.mp4"
        
        if output_file.exists():
            return {"status": "completed", "file": str(output_file), "method": "ffmpeg"}
        
        # Dapatkan channel info dulu
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-select_streams", "a:0",
            "-show_entries", "stream=channels,channel_layout",
            "-of", "csv=p=0",
            str(input_file)
        ]
        
        try:
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            channel_info = probe_result.stdout.strip()
            
            # Pilih filter berdasarkan jumlah channel
            if "stereo" in channel_info or channel_info == "2":
                # Stereo: Phase cancellation
                audio_filter = "pan='stereo|c0=c0-c1|c1=c1-c0'"
            else:
                # Mono/Surround: Vocal reduction via bandstop
                audio_filter = (
                    "equalizer=f=250:width=200:gain=-12,"
                    "equalizer=f=1000:width=500:gain=-8,"
                    "equalizer=f=4000:width=1000:gain=-6"
                )
        except:
            audio_filter = "pan='stereo|c0=c0-c1|c1=c1-c0'"
        
        # Jalankan FFmpeg
        cmd = [
            "ffmpeg",
            "-i", str(input_file),
            "-af", audio_filter,
            "-c:v", "copy",
            "-preset", "ultrafast",
            "-threads", "2",
            "-y",
            str(output_file)
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if process.returncode == 0 and output_file.exists():
            file_size = output_file.stat().st_size
            return {
                "status": "completed",
                "file": str(output_file),
                "method": "ffmpeg",
                "size_mb": round(file_size / 1024 / 1024, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "error": f"FFmpeg failed: {process.stderr[:300]}",
                "status": "failed"
            }
    
    async def _demucs_vocal_remove(self, input_file: Path) -> Dict:
        """
        Demucs AI Separation (Facebook Research)
        - Lebih akurat, memisahkan vocal/drums/bass/other
        - Butuh: pip install demucs
        - Ukuran model: ~80MB (htdemucs)
        """
        try:
            import demucs.separate
        except ImportError:
            return {"error": "Demucs not installed. Run: pip install demucs", "status": "failed"}
        
        output_dir = self.output_dir / "demucs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / input_file.stem / "no_vocals.wav"
        
        if output_file.exists():
            # Combine with video
            final_output = self.output_dir / f"{input_file.stem}_demucs_instrumental.mp4"
            if not final_output.exists():
                await self._combine_audio_video(input_file, output_file, final_output)
            return {"status": "completed", "file": str(final_output), "method": "demucs"}
        
        # Run Demucs (htdemucs = hybrid transformer, lebih ringan)
        cmd = [
            "python", "-m", "demucs",
            "-n", "htdemucs",  # Model ringan (~80MB)
            "--two-stems", "vocals",  # Hanya pisah vocal vs instrumental
            "-o", str(output_dir),
            str(input_file)
        ]
        
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if process.returncode == 0:
            instrumental_file = output_dir / "htdemucs" / input_file.stem / "no_vocals.wav"
            if instrumental_file.exists():
                final_output = self.output_dir / f"{input_file.stem}_demucs_instrumental.mp4"
                await self._combine_audio_video(input_file, instrumental_file, final_output)
                return {"status": "completed", "file": str(final_output), "method": "demucs"}
        
        return {"error": "Demucs separation failed", "status": "failed"}
    
    async def _channel_extraction(self, input_file: Path, channel: str = "left") -> Dict:
        """Extract specific audio channel"""
        output_file = self.output_dir / f"{input_file.stem}_{channel}_only.mp4"
        
        if output_file.exists():
            return {"status": "completed", "file": str(output_file), "method": "channel"}
        
        if channel == "left":
            audio_filter = "pan='stereo|c0=c0|c1=c0'"
        else:
            audio_filter = "pan='stereo|c0=c1|c1=c1'"
        
        cmd = [
            "ffmpeg", "-i", str(input_file),
            "-af", audio_filter,
            "-c:v", "copy", "-y",
            str(output_file)
        ]
        
        subprocess.run(cmd, capture_output=True, timeout=60)
        
        if output_file.exists():
            return {"status": "completed", "file": str(output_file), "method": f"channel_{channel}"}
        
        return {"error": "Channel extraction failed", "status": "failed"}
    
    async def _combine_audio_video(self, video_file: Path, audio_file: Path, output_file: Path):
        """Combine video with new audio track"""
        cmd = [
            "ffmpeg",
            "-i", str(video_file),
            "-i", str(audio_file),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            str(output_file)
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)


# Singleton
vocal_remover = VocalRemover()
