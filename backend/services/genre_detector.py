"""
Online Genre Detection Service
Uses multiple APIs to detect song genre automatically:
1. MusicBrainz (free, no API key)
2. AudD (free tier, needs API key)
3. iTunes/Apple Music Search
"""

import aiohttp
import asyncio
from typing import Optional, Dict, List
from urllib.parse import quote
import hashlib
import json
from pathlib import Path
from datetime import datetime

class OnlineGenreDetector:
    def __init__(self):
        self.cache = {}
        self.cache_file = Path("/app/uploads/genre_cache.json")
        self._load_cache()
        
        # Rate limiting
        self.last_request_time = {}
        self.min_interval = 1.0  # 1 second between requests to same API
        
    def _load_cache(self):
        """Load cached genre results"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
        except:
            self.cache = {}
    
    def _save_cache(self):
        """Save genre results to cache"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except:
            pass
    
    def _get_cache_key(self, title: str, artist: str = None) -> str:
        """Generate cache key from title and artist"""
        combined = f"{title or ''}-{artist or ''}".lower().strip()
        return hashlib.md5(combined.encode()).hexdigest()[:12]
    
    async def _rate_limit(self, api_name: str):
        """Rate limit API requests"""
        import time
        now = time.time()
        if api_name in self.last_request_time:
            elapsed = now - self.last_request_time[api_name]
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
        self.last_request_time[api_name] = time.time()
    
    async def detect_genre_online(self, title: str, artist: str = None) -> Dict:
        """
        Detect genre using multiple online APIs
        Returns: {"genre": "Pop", "confidence": 0.85, "source": "musicbrainz"}
        """
        # Check cache first
        cache_key = self._get_cache_key(title, artist)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Cache valid for 7 days
            if (datetime.now() - datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))).days < 7:
                return cached
        
        # Try multiple APIs
        result = None
        
        # 1. Try MusicBrainz (free, reliable)
        result = await self._detect_musicbrainz(title, artist)
        if result and result.get('confidence', 0) > 0.5:
            self._add_to_cache(cache_key, result)
            return result
        
        # 2. Try iTunes/Apple Music
        result = await self._detect_itunes(title, artist)
        if result and result.get('confidence', 0) > 0.4:
            self._add_to_cache(cache_key, result)
            return result
        
        # 3. Fallback: Local keyword matching
        result = self._detect_local(title, artist)
        self._add_to_cache(cache_key, result)
        return result
    
    async def detect_batch_online(self, songs: List[Dict], progress_callback=None) -> Dict:
        """
        Detect genre for multiple songs
        songs: [{"id": 1, "title": "...", "artist": "..."}, ...]
        """
        results = []
        total = len(songs)
        
        for i, song in enumerate(songs):
            try:
                genre_info = await self.detect_genre_online(
                    song.get('title', ''),
                    song.get('artist', '')
                )
                results.append({
                    "song_id": song['id'],
                    "title": song.get('title', ''),
                    "artist": song.get('artist', ''),
                    "detected_genre": genre_info.get('genre', 'Unknown'),
                    "confidence": genre_info.get('confidence', 0),
                    "source": genre_info.get('source', 'local'),
                    "subgenres": genre_info.get('subgenres', []),
                    "tags": genre_info.get('tags', [])
                })
                
                # Report progress
                if progress_callback:
                    await progress_callback(i + 1, total, song.get('title', ''))
                
                # Rate limit
                await asyncio.sleep(0.3)
                
            except Exception as e:
                results.append({
                    "song_id": song['id'],
                    "title": song.get('title', ''),
                    "error": str(e),
                    "detected_genre": "Unknown",
                    "confidence": 0
                })
        
        return {
            "total": total,
            "detected": len([r for r in results if r.get('confidence', 0) > 0]),
            "results": results
        }
    
    async def _detect_musicbrainz(self, title: str, artist: str = None) -> Optional[Dict]:
        """
        Detect genre using MusicBrainz API
        Free, no API key required, rate limit: 1 request/second
        """
        try:
            await self._rate_limit('musicbrainz')
            
            # Search for recording
            query = f'"{title}"'
            if artist:
                query += f' AND artist:"{artist}"'
            
            url = "https://musicbrainz.org/ws/2/recording/"
            params = {
                "query": query,
                "fmt": "json",
                "limit": 5
            }
            
            headers = {
                "User-Agent": "BPFKaraoke/3.0 (bestprofit-futures.com)",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        recordings = data.get('recordings', [])
                        
                        if recordings:
                            # Get tags/genres from first matching recording
                            for rec in recordings:
                                tags = rec.get('tags', [])
                                if tags:
                                    # Map MusicBrainz tags to Indonesian genre names
                                    genre_tags = [t.get('name', '') for t in tags]
                                    main_genre = self._map_musicbrainz_genre(genre_tags)
                                    
                                    if main_genre:
                                        return {
                                            "genre": main_genre,
                                            "confidence": min(0.9, 0.5 + len(tags) * 0.1),
                                            "source": "musicbrainz",
                                            "subgenres": genre_tags[:5],
                                            "tags": genre_tags[:10]
                                        }
                        
                        # If no tags, try to get from artist
                        if artist and recordings:
                            artist_tags = await self._get_artist_tags_musicbrainz(artist)
                            if artist_tags:
                                main_genre = self._map_musicbrainz_genre(artist_tags)
                                return {
                                    "genre": main_genre,
                                    "confidence": 0.6,
                                    "source": "musicbrainz_artist",
                                    "subgenres": artist_tags[:5],
                                    "tags": artist_tags
                                }
            
            return None
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"MusicBrainz error: {e}")
            return None
    
    async def _get_artist_tags_musicbrainz(self, artist: str) -> List[str]:
        """Get tags for an artist from MusicBrainz"""
        try:
            await self._rate_limit('musicbrainz')
            
            url = "https://musicbrainz.org/ws/2/artist/"
            params = {
                "query": f'artist:"{artist}"',
                "fmt": "json",
                "limit": 3
            }
            
            headers = {"User-Agent": "BPFKaraoke/3.0 (bestprofit-futures.com)"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        artists = data.get('artists', [])
                        if artists:
                            tags = artists[0].get('tags', [])
                            return [t.get('name', '') for t in tags]
            
            return []
        except:
            return []
    
    async def _detect_itunes(self, title: str, artist: str = None) -> Optional[Dict]:
        """
        Detect genre using iTunes Search API
        Free, no API key, provides genre info
        """
        try:
            await self._rate_limit('itunes')
            
            term = title
            if artist:
                term = f"{artist} {title}"
            
            url = "https://itunes.apple.com/search"
            params = {
                "term": term,
                "media": "music",
                "limit": 3,
                "country": "ID"  # Indonesia store
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get('results', [])
                        
                        if results:
                            genre = results[0].get('primaryGenreName', '')
                            if genre:
                                # Map iTunes genre to our categories
                                mapped_genre = self._map_itunes_genre(genre)
                                return {
                                    "genre": mapped_genre,
                                    "confidence": 0.7,
                                    "source": "itunes",
                                    "original_genre": genre,
                                    "tags": [genre]
                                }
            
            return None
            
        except Exception as e:
            print(f"iTunes error: {e}")
            return None
    
    def _map_musicbrainz_genre(self, tags: List[str]) -> Optional[str]:
        """Map MusicBrainz tags to Indonesian genre categories"""
        tag_string = ' '.join(tags).lower()
        
        mapping = {
            "Pop Indonesia": ["indonesian pop", "indo pop", "pop indonesia", "indonesian"],
            "Dangdut": ["dangdut", "koplo", "dangdut koplo"],
            "Rock": ["rock", "alternative rock", "hard rock", "metal", "punk", "indie rock"],
            "K-Pop": ["k-pop", "kpop", "korean pop", "korean"],
            "Barat": ["pop", "western pop", "american pop", "british", "english"],
            "Mandarin": ["mandopop", "cantopop", "chinese", "mandarin"],
            "Jazz": ["jazz", "smooth jazz", "bossa nova", "swing"],
            "EDM": ["electronic", "edm", "house", "techno", "dance", "trance", "dubstep"],
            "Hip Hop": ["hip hop", "hip-hop", "rap", "trap", "rnb"],
            "Ballad": ["ballad", "slow", "mellow", "acoustic"],
            "Religi": ["religious", "gospel", "islamic", "christian", "spiritual"],
        }
        
        for genre, keywords in mapping.items():
            if any(kw in tag_string for kw in keywords):
                return genre
        
        # Default based on first tag
        if "pop" in tag_string:
            return "Barat"
        elif "rock" in tag_string:
            return "Rock"
        
        return None
    
    def _map_itunes_genre(self, genre: str) -> str:
        """Map iTunes genres to our categories"""
        genre_lower = genre.lower()
        
        mapping = {
            "Pop Indonesia": ["pop indonesia", "indo pop", "indonesian pop"],
            "Dangdut": ["dangdut", "world"],
            "Rock": ["rock", "alternative", "metal"],
            "K-Pop": ["k-pop", "korean"],
            "Barat": ["pop", "adult contemporary", "singer/songwriter"],
            "Jazz": ["jazz"],
            "EDM": ["electronic", "dance"],
            "Hip Hop": ["hip-hop", "rap"],
            "R&B": ["r&b", "soul"],
            "Religi": ["gospel", "christian", "religious"],
        }
        
        for our_genre, keywords in mapping.items():
            if any(kw in genre_lower for kw in keywords):
                return our_genre
        
        return genre  # Return original if no match
    
    def _detect_local(self, title: str, artist: str = None) -> Dict:
        """Fallback: Local keyword-based detection"""
        combined = f"{title or ''} {artist or ''}".lower()
        
        genre_patterns = {
            "Dangdut": ["dangdut", "koplo", "jaran goyang", "gendang", "suling"],
            "K-Pop": ["bts", "blackpink", "exo", "twice", "nct", "korea", "seoul"],
            "Mandarin": ["mandarin", "chinese", "cina", "tiongkok", "shanghai", "beijing"],
            "Rock": ["rock", "metal", "punk", "gitar listrik", "distorsi"],
            "Jazz": ["jazz", "saxophone", "piano jazz", "blues"],
            "EDM": ["dj", "remix", "electronic", "dance", "drop"],
            "Hip Hop": ["rap", "trap", "beatbox", "freestyle"],
            "Religi": ["sholawat", "quran", "rohani", "puji", "tuhan", "gereja", "islam"],
            "Anak": ["anak", "balita", "tk", "paud", "kids", "children"],
            "Ballad": ["ballad", "akustik", "piano", "slow", "acoustic"],
        }
        
        for genre, keywords in genre_patterns.items():
            if any(kw in combined for kw in keywords):
                return {
                    "genre": genre,
                    "confidence": 0.5,
                    "source": "local_keyword",
                    "tags": [genre]
                }
        
        # Default
        return {
            "genre": "Pop Indonesia",
            "confidence": 0.2,
            "source": "local_default",
            "tags": ["Unknown"]
        }
    
    def _add_to_cache(self, cache_key: str, result: Dict):
        """Add result to cache"""
        result['cached_at'] = datetime.now().isoformat()
        self.cache[cache_key] = result
        # Save cache every 10 additions
        if len(self.cache) % 10 == 0:
            self._save_cache()
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "cached_entries": len(self.cache),
            "cache_file": str(self.cache_file),
            "apis_available": ["musicbrainz", "itunes", "local"]
        }

# Singleton
genre_detector = OnlineGenreDetector()
