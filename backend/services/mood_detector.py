"""
Mood Detector - Menganalisis mood ruangan dari pola pemilihan lagu
"""

from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np

class MoodDetector:
    def __init__(self):
        # Mapping genre ke mood
        self.genre_mood_map = {
            'Dangdut': 'energetic',
            'Rock': 'energetic',
            'K-Pop': 'energetic',
            'Pop Indonesia': 'happy',
            'Barat': 'happy',
            'Religi': 'calm',
            'Anak': 'happy',
            'Ballad': 'sad',
            'Jazz': 'relaxed',
            'Akustik': 'relaxed',
            'Mandarin': 'neutral'
        }
        
        # Room mood history
        self.room_moods = defaultdict(list)
        
        # Mood transition probabilities (untuk prediksi mood selanjutnya)
        self.mood_transitions = {
            'happy': {'happy': 0.4, 'energetic': 0.3, 'romantic': 0.2, 'relaxed': 0.1},
            'energetic': {'energetic': 0.5, 'happy': 0.2, 'relaxed': 0.2, 'calm': 0.1},
            'romantic': {'romantic': 0.5, 'relaxed': 0.3, 'happy': 0.2},
            'sad': {'sad': 0.3, 'romantic': 0.3, 'happy': 0.2, 'calm': 0.2},
            'relaxed': {'relaxed': 0.5, 'romantic': 0.2, 'happy': 0.2, 'calm': 0.1},
            'calm': {'calm': 0.4, 'relaxed': 0.3, 'happy': 0.2, 'sad': 0.1}
        }
    
    def detect_mood_from_genre(self, genre):
        """Deteksi mood dari genre lagu"""
        return self.genre_mood_map.get(genre, 'neutral')
    
    def detect_room_mood(self, room_id, recent_songs=10):
        """
        Deteksi mood ruangan dari 10 lagu terakhir
        """
        moods = self.room_moods.get(room_id, [])
        
        if not moods:
            return {
                'current_mood': 'neutral',
                'confidence': 0.0,
                'mood_distribution': {},
                'suggestion': 'Mulai pilih lagu untuk rekomendasi mood'
            }
        
        # Ambil N lagu terakhir
        recent_moods = moods[-recent_songs:]
        
        # Hitung distribusi mood
        mood_counts = defaultdict(int)
        for m in recent_moods:
            mood_counts[m] += 1
        
        # Mood dominan
        dominant_mood = max(mood_counts, key=mood_counts.get)
        confidence = mood_counts[dominant_mood] / len(recent_moods)
        
        # Prediksi mood selanjutnya
        next_mood_prob = self.mood_transitions.get(dominant_mood, {})
        predicted_next = max(next_mood_prob, key=next_mood_prob.get) if next_mood_prob else 'happy'
        
        # Saran untuk operator
        suggestions = {
            'energetic': '🔥 Room sedang semangat! Rekomendasi: lagu upbeat, rock, atau dangdut',
            'happy': '😊 Suasana ceria! Rekomendasi: pop Indonesia atau lagu hits terkini',
            'romantic': '💕 Suasana romantis! Rekomendasi: lagu slow, ballad, atau akustik',
            'sad': '😢 Sedang galau nih! Rekomendasi: lagu ballad atau religi',
            'relaxed': '😌 Santai! Rekomendasi: lagu akustik, jazz, atau instrumental',
            'calm': '🧘‍♂️ Tenang! Rekomendasi: lagu religi atau instrumental'
        }
        
        return {
            'current_mood': dominant_mood,
            'confidence': round(confidence, 2),
            'mood_distribution': dict(mood_counts),
            'predicted_next_mood': predicted_next,
            'suggestion': suggestions.get(dominant_mood, 'Pilih lagu sesuai selera!'),
            'mood_emoji': {
                'energetic': '🔥',
                'happy': '😊',
                'romantic': '💕',
                'sad': '😢',
                'relaxed': '😌',
                'calm': '🧘‍♂️',
                'neutral': '🎵'
            }.get(dominant_mood, '🎵')
        }
    
    def record_song_play(self, room_id, genre):
        """Catat pemutaran lagu untuk tracking mood"""
        mood = self.detect_mood_from_genre(genre)
        self.room_moods[room_id].append(mood)
        
        # Batasi history (maksimal 100)
        if len(self.room_moods[room_id]) > 100:
            self.room_moods[room_id] = self.room_moods[room_id][-100:]
    
    def get_mood_timeline(self, room_id, limit=20):
        """Dapatkan timeline mood"""
        moods = self.room_moods.get(room_id, [])
        return moods[-limit:] if moods else []
    
    def get_peak_hour_mood(self, room_id):
        """Analisis mood berdasarkan jam"""
        # Implementasi sederhana
        current_hour = datetime.now().hour
        
        if 20 <= current_hour or current_hour < 2:
            return 'energetic'  # Jam prime time
        elif 14 <= current_hour < 18:
            return 'relaxed'    # Sore santai
        elif 18 <= current_hour < 20:
            return 'happy'      # Awal malam
        else:
            return 'calm'

# Singleton instance
mood_detector = MoodDetector()
