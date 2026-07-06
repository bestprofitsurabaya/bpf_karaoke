"""
Smart Search - Fuzzy matching untuk toleransi typo
Menggunakan Levenshtein Distance untuk pencarian yang lebih cerdas
"""

from fuzzywuzzy import fuzz, process
from typing import List, Dict, Tuple
import re

class SmartSearch:
    def __init__(self):
        self.search_index = {}  # {keyword: [song_ids]}
        self.song_data = {}     # {song_id: {...}}
        
    def build_index(self, songs: List[Dict]):
        """Bangun index pencarian dari data lagu"""
        self.song_data = {s['id']: s for s in songs}
        self.search_index = {}
        
        for song in songs:
            # Tokenize title dan artist
            title_tokens = self._tokenize(song.get('title', ''))
            artist_tokens = self._tokenize(song.get('artist', ''))
            genre_tokens = self._tokenize(song.get('genre', ''))
            
            all_tokens = set(title_tokens + artist_tokens + genre_tokens)
            
            for token in all_tokens:
                if token not in self.search_index:
                    self.search_index[token] = []
                self.search_index[token].append(song['id'])
    
    def search(self, query: str, limit: int = 20, threshold: int = 60) -> List[Dict]:
        """
        Cari lagu dengan fuzzy matching
        threshold: minimum similarity score (0-100)
        """
        if not query or not self.search_index:
            return []
        
        query_lower = query.lower().strip()
        results = {}
        
        # 1. Exact match dulu
        exact_matches = self._exact_search(query_lower)
        for song_id in exact_matches:
            results[song_id] = {
                **self.song_data.get(song_id, {}),
                'match_score': 100,
                'match_type': 'exact'
            }
        
        # 2. Fuzzy match dengan judul dan artis
        for song_id, song in self.song_data.items():
            if song_id in results:
                continue
            
            # Hitung similarity dengan judul
            title_score = fuzz.partial_ratio(query_lower, song.get('title', '').lower())
            
            # Hitung similarity dengan artis
            artist_score = fuzz.partial_ratio(query_lower, song.get('artist', '').lower())
            
            # Hitung similarity dengan genre
            genre_score = fuzz.partial_ratio(query_lower, song.get('genre', '').lower())
            
            max_score = max(title_score, artist_score, genre_score)
            
            if max_score >= threshold:
                results[song_id] = {
                    **song,
                    'match_score': max_score,
                    'match_type': 'fuzzy'
                }
        
        # 3. Token-based search
        query_tokens = self._tokenize(query_lower)
        for token in query_tokens:
            if token in self.search_index:
                for song_id in self.search_index[token]:
                    if song_id not in results:
                        results[song_id] = {
                            **self.song_data.get(song_id, {}),
                            'match_score': 80,
                            'match_type': 'token'
                        }
        
        # Sort by match_score dan limit
        sorted_results = sorted(results.values(), key=lambda x: x['match_score'], reverse=True)
        return sorted_results[:limit]
    
    def suggest_corrections(self, query: str, limit: int = 5) -> List[str]:
        """
        Berikan saran koreksi untuk typo
        """
        if not query:
            return []
        
        query_lower = query.lower()
        all_titles = [s.get('title', '') for s in self.song_data.values()]
        all_artists = [s.get('artist', '') for s in self.song_data.values() if s.get('artist')]
        
        # Cari judul yang mirip
        title_matches = process.extract(query_lower, all_titles, limit=limit)
        artist_matches = process.extract(query_lower, all_artists, limit=limit)
        
        suggestions = []
        for match, score in title_matches + artist_matches:
            if score >= 70 and match.lower() != query_lower:
                suggestions.append(match)
        
        return list(dict.fromkeys(suggestions))[:limit]  # Remove duplicates
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text menjadi keyword"""
        if not text:
            return []
        
        # Lowercase dan hapus special characters
        text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Split dan filter token pendek
        tokens = text.split()
        return [t for t in tokens if len(t) >= 2]
    
    def _exact_search(self, query: str) -> List[int]:
        """Pencarian exact match"""
        results = []
        for song_id, song in self.song_data.items():
            if (query in song.get('title', '').lower() or 
                query in song.get('artist', '').lower() or
                query == song.get('genre', '').lower()):
                results.append(song_id)
        return results

# Singleton instance
smart_search = SmartSearch()
