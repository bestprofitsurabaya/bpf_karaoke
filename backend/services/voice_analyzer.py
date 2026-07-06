"""
Voice Analyzer - Analisis aktivitas vokal sederhana
Untuk auto-scoring dan deteksi penyanyi
"""

import numpy as np
from collections import deque
from datetime import datetime
from typing import Dict
import asyncio

class VoiceAnalyzer:
    def __init__(self):
        self.audio_buffer = deque(maxlen=100)
        self.is_singing = False
        self.energy_history = deque(maxlen=50)
        self.pitch_history = deque(maxlen=50)
        self.score = 0
        self.total_notes = 0
        self.correct_notes = 0
        
        self.energy_threshold = 0.3
        self.silence_duration = 0
        self.max_silence = 30
        
    def analyze_audio_frame(self, audio_data: bytes, sample_rate: int = 44100) -> Dict:
        """Analisis satu frame audio"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.float32)
            
            if len(audio_array) == 0:
                return self._get_default_result()
            
            energy = np.sqrt(np.mean(audio_array ** 2))
            self.energy_history.append(energy)
            self.audio_buffer.append(energy)
            
            was_singing = self.is_singing
            self.is_singing = energy > self.energy_threshold
            
            if not self.is_singing:
                self.silence_duration += 1
            else:
                self.silence_duration = 0
                zcr = self._calculate_zcr(audio_array)
                self.pitch_history.append(zcr)
                self.total_notes += 1
            
            if self.is_singing and len(self.pitch_history) > 2:
                pitch_variance = np.var(list(self.pitch_history)[-10:])
                self.score = max(0, min(100, 100 - pitch_variance * 1000))
            
            return {
                'is_singing': self.is_singing,
                'energy': float(energy),
                'score': round(self.score, 1),
                'started_singing': not was_singing and self.is_singing,
                'stopped_singing': was_singing and not self.is_singing,
                'silence_duration': self.silence_duration,
                'energy_level': self._get_energy_level(energy),
                'total_notes': self.total_notes
            }
            
        except Exception as e:
            return self._get_default_result()
    
    def get_performance_stats(self) -> Dict:
        """Dapatkan statistik performa"""
        if self.total_notes == 0:
            return {
                'average_score': 0,
                'notes_sung': 0,
                'performance_rating': 'Belum ada data',
                'stars': 0
            }
        
        avg_score = self.score
        
        if avg_score >= 90:
            rating = 'Sempurna! 🌟🌟🌟🌟🌟'
            stars = 5
        elif avg_score >= 75:
            rating = 'Bagus! 🌟🌟🌟🌟'
            stars = 4
        elif avg_score >= 60:
            rating = 'Cukup Baik 🌟🌟🌟'
            stars = 3
        elif avg_score >= 40:
            rating = 'Lumayan 🌟🌟'
            stars = 2
        else:
            rating = 'Semangat! 🌟'
            stars = 1
        
        return {
            'average_score': round(avg_score, 1),
            'notes_sung': self.total_notes,
            'performance_rating': rating,
            'stars': stars
        }
    
    def reset_score(self):
        """Reset skor"""
        self.score = 0
        self.total_notes = 0
        self.correct_notes = 0
        self.pitch_history.clear()
    
    def _calculate_zcr(self, audio_array: np.ndarray) -> float:
        """Hitung Zero Crossing Rate"""
        if len(audio_array) < 2:
            return 0
        return float(np.sum(np.abs(np.diff(np.sign(audio_array)))) / (2 * len(audio_array)))
    
    def _get_energy_level(self, energy: float) -> str:
        """Klasifikasi level energi"""
        if energy < 0.1:
            return 'silent'
        elif energy < 0.3:
            return 'low'
        elif energy < 0.6:
            return 'medium'
        else:
            return 'high'
    
    def _get_default_result(self) -> Dict:
        return {
            'is_singing': False,
            'energy': 0.0,
            'score': 0,
            'started_singing': False,
            'stopped_singing': False,
            'silence_duration': 0,
            'energy_level': 'silent',
            'total_notes': 0
        }

# Singleton instance
voice_analyzer = VoiceAnalyzer()
