"""
Genre Detector Service - AI Hybrid Genre Prediction
Menggunakan kombinasi Fuzzy Matching + Rule-based Classification
"""

import re
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz

class GenreDetector:
    """
    AI Genre Detector menggunakan:
    1. Keyword-based classification
    2. Artist database matching  
    3. Title pattern analysis
    """
    
    def __init__(self):
        # Genre keywords database
        self.genre_keywords = {
            'Dangdut': [
                'dangdut', 'koplo', 'campursari', 'jaipong', 'sunda',
                'rhoma', 'irama', 'inul', 'dangdutan', 'jaran goyang'
            ],
            'K-Pop': [
                'bts', 'blackpink', 'twice', 'exo', 'nct', 'stray kids',
                'aespa', 'ive', 'newjeans', 'seventeen', 'got7', 'monsta x',
                'red velvet', 'itzy', 'txt', 'enhypen', 'bigbang', 'shinee',
                'k-pop', 'kpop', 'korean', 'girls generation', 'super junior'
            ],
            'Rock': [
                'rock', 'metal', 'punk', 'grunge', 'alternative',
                'linkin park', 'metallica', 'nirvana', 'green day', 'foo fighters',
                'slank', 'superman is dead', 'jamrud', 'padi', 'dewa'
            ],
            'Barat': [
                'ed sheeran', 'taylor swift', 'justin bieber', 'ariana grande',
                'adele', 'bruno mars', 'coldplay', 'maroon 5', 'weeknd',
                'dua lipa', 'billie eilish', 'harry styles', 'shawn mendes',
                'west', 'english', 'international', 'british', 'american'
            ],
            'Pop Indonesia': [
                'raisa', 'isyana', 'fatin', 'tiara andini', 'lyodra',
                'mahalini', 'rizky febian', 'tulus', 'afgan', 'budi doremi',
                'armada', 'dmasiv', 'noah', 'peterpan', 'sheila on 7',
                'geisha', 'kotak', 'vierra', 'nidji', 'letto',
                'ungu', 'rossa', 'bcl', 'agnez mo', 'maudy ayunda',
                'pop', 'indonesia', 'melayu'
            ],
            'Religi': [
                'religi', 'islami', 'sholawat', 'qasidah', 'nasyid',
                'hadad alwi', 'sulis', 'opick', 'unggul', 'gigi religi',
                'christian', 'gospel', 'rohani', 'praise', 'worship',
                'hillsong', 'bethel', 'elevation'
            ],
            'Anak': [
                'anak', 'kids', 'children', 'balonku', 'cicak',
                'naik kereta', 'pelangi', 'bintang kecil', 'kasih ibu',
                'nina bobo', 'abc', 'alfabet'
            ],
            'Mandarin': [
                'mandarin', 'chinese', 'c-pop', 'cpop', 'taiwan',
                'jay chou', 'jj lin', 'wang lee hom', 'teresa teng',
                'faye wong', 'eason chan', 'jolin tsai'
            ],
            'Daerah': [
                'daerah', 'tradisional', 'jawa', 'sunda', 'batak', 'minang',
                'ambon', 'manado', 'papua', 'kalimantan', 'bali',
                'keroncong', 'gambus', 'gamelan', 'angklung'
            ],
            'Jazz': [
                'jazz', 'blues', 'swing', 'bossa nova', 'smooth jazz',
                'louis armstrong', 'miles davis', 'frank sinatra', 'norah jones',
                'jamie cullum', 'diana krall', 'tompi', 'indro hardjodikoro'
            ],
            'EDM': [
                'edm', 'electronic', 'dance', 'house', 'techno', 'trance',
                'dubstep', 'dj', 'remix', 'marshmello', 'calvin harris',
                'avicii', 'tiesto', 'martin garrix', 'zedd', 'skrillex'
            ],
            'Hip Hop': [
                'hip hop', 'rap', 'trap', 'drake', 'eminem', 'kendrick lamar',
                'kanye west', 'jay-z', 'travis scott', 'cardi b', 'nicki minaj',
                'rich brian', 'ramengvrl', 'warren hue'
            ]
        }
        
        # Confidence weights
        self.weights = {
            'exact_artist_match': 0.95,
            'artist_fuzzy_match': 0.75,
            'title_keyword': 0.60,
            'partial_artist_match': 0.50,
            'default': 0.0
        }
        
        # Cache untuk performance
        self._cache = {}
    
    def predict_genre(self, artist: str, title: str) -> Dict:
        """
        Predict genre dengan confidence score
        
        Args:
            artist: Nama artis/penyanyi
            title: Judul lagu
            
        Returns:
            {
                'genre': str,
                'confidence': float (0.0 - 1.0),
                'method': str (detection method used),
                'alternatives': list of dict
            }
        """
        # Normalize inputs
        artist_lower = artist.lower().strip() if artist else ''
        title_lower = title.lower().strip() if title else ''
        
        # Cache key
        cache_key = f"{artist_lower}|{title_lower}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Collect scores from all methods
        scores = defaultdict(float)
        methods = defaultdict(str)
        
        # Method 1: Exact artist match
        if artist_lower:
            exact_genre = self._exact_artist_match(artist_lower)
            if exact_genre:
                scores[exact_genre] = self.weights['exact_artist_match']
                methods[exact_genre] = 'exact_artist_match'
        
        # Method 2: Fuzzy artist match
        if artist_lower:
            fuzzy_genre, fuzzy_score = self._fuzzy_artist_match(artist_lower)
            if fuzzy_genre and fuzzy_score > 75:
                weighted_score = self.weights['artist_fuzzy_match'] * (fuzzy_score / 100)
                scores[fuzzy_genre] = max(scores[fuzzy_genre], weighted_score)
                if not methods.get(fuzzy_genre):
                    methods[fuzzy_genre] = 'fuzzy_artist_match'
        
        # Method 3: Title keyword match
        if title_lower:
            title_genre = self._title_keyword_match(title_lower)
            if title_genre:
                scores[title_genre] = max(scores[title_genre], self.weights['title_keyword'])
                if not methods.get(title_genre):
                    methods[title_genre] = 'title_keyword'
        
        # Method 4: Combined analysis
        combined_genre, combined_score = self._combined_analysis(artist_lower, title_lower)
        if combined_genre:
            scores[combined_genre] = max(scores[combined_genre], combined_score)
            if not methods.get(combined_genre):
                methods[combined_genre] = 'combined_analysis'
        
        # Determine best prediction
        if scores:
            best_genre = max(scores, key=scores.get)
            confidence = scores[best_genre]
            method = methods[best_genre]
            
            # Get alternatives
            alternatives = [
                {'genre': g, 'confidence': s}
                for g, s in sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:4]
                if s > 0.3
            ]
        else:
            best_genre = 'Unknown'
            confidence = 0.0
            method = 'no_match'
            alternatives = []
        
        result = {
            'genre': best_genre,
            'confidence': round(confidence, 3),
            'method': method,
            'alternatives': alternatives,
            'artist': artist,
            'title': title
        }
        
        # Cache result
        self._cache[cache_key] = result
        
        return result
    
    def _exact_artist_match(self, artist: str) -> Optional[str]:
        """Exact match artist name in keyword database"""
        for genre, keywords in self.genre_keywords.items():
            if artist in keywords:
                return genre
        return None
    
    def _fuzzy_artist_match(self, artist: str) -> Tuple[Optional[str], int]:
        """Fuzzy match artist name against keyword database"""
        best_genre = None
        best_score = 0
        
        # Split artist name into parts
        artist_parts = artist.split()
        
        for genre, keywords in self.genre_keywords.items():
            for keyword in keywords:
                # Full match
                score = fuzz.ratio(artist, keyword)
                if score > best_score:
                    best_score = score
                    best_genre = genre
                
                # Partial match (any part of artist name)
                for part in artist_parts:
                    if len(part) >= 3:
                        part_score = fuzz.partial_ratio(part, keyword)
                        if part_score > best_score:
                            best_score = part_score
                            best_genre = genre
        
        return best_genre, best_score
    
    def _title_keyword_match(self, title: str) -> Optional[str]:
        """Check title for genre-indicating keywords"""
        for genre, keywords in self.genre_keywords.items():
            if any(kw in title for kw in ['dangdut', 'koplo', 'religi', 'sholawat', 'k-pop', 'rock']):
                if 'dangdut' in title or 'koplo' in title:
                    return 'Dangdut'
                if 'religi' in title or 'sholawat' in title:
                    return 'Religi'
                if 'k-pop' in title or 'kpop' in title:
                    return 'K-Pop'
                if 'rock' in title:
                    return 'Rock'
        return None
    
    def _combined_analysis(self, artist: str, title: str) -> Tuple[Optional[str], float]:
        """Combined analysis using both artist and title"""
        # Check if it's Indonesian (based on common words in title)
        indonesian_words = ['aku', 'kamu', 'cinta', 'hati', 'sayang', 'rindu', 'bahagia', 'sedih']
        if artist or title:
            combined_text = f"{artist} {title}"
            indo_count = sum(1 for w in indonesian_words if w in combined_text)
            if indo_count >= 2 and artist:
                # Likely Pop Indonesia or Dangdut
                return 'Pop Indonesia', 0.55
        
        return None, 0.0
    
    def predict_batch(self, songs: list) -> list:
        """Predict genre for multiple songs"""
        results = []
        for song in songs:
            prediction = self.predict_genre(
                artist=song.get('artist', ''),
                title=song.get('title', '')
            )
            results.append({
                **song,
                'predicted_genre': prediction['genre'],
                'confidence': prediction['confidence'],
                'method': prediction['method'],
                'alternatives': prediction['alternatives']
            })
        return results
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            'total_genres': len(self.genre_keywords),
            'total_keywords': sum(len(v) for v in self.genre_keywords.values()),
            'cache_size': len(self._cache),
            'genres': list(self.genre_keywords.keys())
        }
    
    def add_keyword(self, genre: str, keyword: str) -> bool:
        """Add keyword to genre database"""
        keyword = keyword.lower().strip()
        if genre not in self.genre_keywords:
            self.genre_keywords[genre] = []
        if keyword not in self.genre_keywords[genre]:
            self.genre_keywords[genre].append(keyword)
            self._cache.clear()  # Invalidate cache
            return True
        return False
    
    def clear_cache(self):
        """Clear prediction cache"""
        self._cache.clear()


# Singleton instance
genre_detector = GenreDetector()
