"""
Auto Playlist Generator - Generate playlist berdasarkan tema/genre
"""

import random
from typing import List, Dict
from collections import defaultdict

class AutoPlaylistGenerator:
    def __init__(self):
        self.songs_by_genre = defaultdict(list)
        self.songs_by_language = defaultdict(list)
        self.songs_by_decade = defaultdict(list)
        self.all_songs = []
        
    def load_songs(self, songs: List[Dict]):
        """Load lagu untuk playlist generation"""
        self.all_songs = songs
        self.songs_by_genre = defaultdict(list)
        self.songs_by_language = defaultdict(list)
        
        for song in songs:
            genre = song.get('genre', 'Unknown')
            language = song.get('language', 'Unknown')
            year = song.get('year', 0)
            
            self.songs_by_genre[genre].append(song)
            self.songs_by_language[language].append(song)
            
            if year:
                decade = (year // 10) * 10
                self.songs_by_decade[decade].append(song)
    
    def generate_by_genre(self, genre: str, count: int = 15) -> Dict:
        """Generate playlist berdasarkan genre"""
        songs = self.songs_by_genre.get(genre, [])
        if len(songs) < count:
            songs = self.all_songs[:count]
        
        selected = random.sample(songs, min(count, len(songs)))
        random.shuffle(selected)
        
        return {
            'name': f'Playlist {genre}',
            'description': f'Kumpulan lagu {genre} terbaik',
            'songs': selected,
            'total_duration_estimate': len(selected) * 4  # Rata-rata 4 menit per lagu
        }
    
    def generate_by_mood(self, mood: str, count: int = 15) -> Dict:
        """Generate playlist berdasarkan mood"""
        mood_genres = {
            'party': ['Dangdut', 'K-Pop', 'Rock', 'Pop Indonesia'],
            'romantic': ['Pop Indonesia', 'Barat', 'Ballad'],
            'nostalgia': ['Pop Indonesia', 'Barat', 'Mandarin'],
            'chill': ['Jazz', 'Akustik', 'Religi'],
            'kids': ['Anak'],
            'dangdut-party': ['Dangdut', 'Pop Indonesia']
        }
        
        genres = mood_genres.get(mood, ['Pop Indonesia'])
        songs = []
        for genre in genres:
            songs.extend(self.songs_by_genre.get(genre, []))
        
        if len(songs) < count:
            songs = self.all_songs
        
        selected = random.sample(songs, min(count, len(songs)))
        
        mood_names = {
            'party': 'Party Time! 🎉',
            'romantic': 'Romantic Night 💕',
            'nostalgia': 'Nostalgia 90an 📻',
            'chill': 'Chill Vibes 😌',
            'kids': 'Lagu Anak Ceria 👶',
            'dangdut-party': 'Dangdut Party 🎶'
        }
        
        return {
            'name': mood_names.get(mood, f'Playlist {mood}'),
            'description': f'Playlist otomatis untuk suasana {mood}',
            'songs': selected,
            'total_duration_estimate': len(selected) * 4
        }
    
    def generate_by_decade(self, decade: int, count: int = 15) -> Dict:
        """Generate playlist berdasarkan dekade"""
        songs = self.songs_by_decade.get(decade, [])
        
        if len(songs) < count:
            songs = self.all_songs[:count]
        
        selected = random.sample(songs, min(count, len(songs)))
        
        return {
            'name': f'Lagu Era {decade}an',
            'description': f'Nostalgia lagu-lagu tahun {decade}an',
            'songs': selected,
            'total_duration_estimate': len(selected) * 4
        }
    
    def generate_top_hits(self, count: int = 20) -> Dict:
        """Generate playlist lagu terpopuler"""
        sorted_songs = sorted(self.all_songs, key=lambda x: x.get('play_count', 0), reverse=True)
        
        return {
            'name': 'Top Hits 🔥',
            'description': 'Lagu paling sering diputar',
            'songs': sorted_songs[:count],
            'total_duration_estimate': min(count, len(sorted_songs)) * 4
        }
    
    def generate_smart_mix(self, room_mood: str = None, count: int = 15) -> Dict:
        """Generate smart mix berdasarkan mood ruangan"""
        if room_mood and room_mood != 'neutral':
            return self.generate_by_mood(room_mood, count)
        else:
            return self.generate_top_hits(count)

# Singleton instance
playlist_generator = AutoPlaylistGenerator()
