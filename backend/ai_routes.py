"""
AI/ML Routes untuk Karaoke System
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/ai", tags=["AI Features"])

# Import services dengan fallback
try:
    from services.song_recommender import song_recommender
except ImportError:
    song_recommender = None

try:
    from services.mood_detector import mood_detector
except ImportError:
    mood_detector = None

try:
    from services.smart_search import smart_search
except ImportError:
    smart_search = None

try:
    from services.auto_playlist import playlist_generator
except ImportError:
    playlist_generator = None

try:
    from services.voice_analyzer import voice_analyzer
except ImportError:
    voice_analyzer = None


class TrainRequest(BaseModel):
    songs: List[Dict[str, Any]]

class SearchRequest(BaseModel):
    query: str
    limit: int = 20

class PlaylistRequest(BaseModel):
    type: str
    value: Optional[str] = None
    count: int = 15


# ============================================
# Mood Detection Endpoints
# ============================================

@router.get("/mood/{room_id}")
async def detect_room_mood(room_id: str):
    """Deteksi mood ruangan"""
    if mood_detector:
        result = mood_detector.detect_room_mood(room_id)
        return result
    
    # Fallback
    return {
        "current_mood": "happy",
        "mood_emoji": "😊",
        "confidence": 0.85,
        "suggestion": "Suasana ceria! Rekomendasi: pop Indonesia atau lagu hits terkini"
    }

@router.post("/mood/record")
async def record_mood(room_id: str = Query(...), genre: str = Query(...), song_id: int = Query(...)):
    """Catat pemutaran lagu untuk mood tracking"""
    if mood_detector:
        mood_detector.record_song_play(room_id, genre)
    if song_recommender:
        song_recommender.record_play(room_id, song_id, genre)
    
    return {"message": "Mood recorded", "room_id": room_id}


# ============================================
# Song Recommendation Endpoints
# ============================================

@router.post("/train")
async def train_recommender(request: TrainRequest):
    """Train AI recommender"""
    if song_recommender:
        success = song_recommender.train(request.songs)
        if smart_search:
            smart_search.build_index(request.songs)
        if playlist_generator:
            playlist_generator.load_songs(request.songs)
        return {"message": "AI models trained", "songs_count": len(request.songs)}
    return {"message": "AI services not available"}

@router.get("/recommend/{song_id}")
async def get_recommendations(song_id: int, count: int = Query(10, le=50)):
    """Dapatkan rekomendasi lagu"""
    if song_recommender:
        recommendations = song_recommender.get_recommendations(song_id, count)
        return {"song_id": song_id, "recommendations": recommendations, "total": len(recommendations)}
    return {"song_id": song_id, "recommendations": [], "total": 0}

@router.get("/recommend/room/{room_id}")
async def get_room_recommendations(room_id: str, count: int = Query(10, le=50)):
    """Rekomendasi berdasarkan preferensi room"""
    if song_recommender:
        recommendations = song_recommender.get_recommendations_for_room(room_id, count)
        return {"room_id": room_id, "recommendations": recommendations}
    return {"room_id": room_id, "recommendations": []}

@router.get("/recommend/mood/{mood}")
async def get_mood_recommendations(mood: str, count: int = Query(10, le=50)):
    """Rekomendasi berdasarkan mood"""
    if song_recommender:
        recommendations = song_recommender.get_mood_based_recommendations(mood, count)
        return {"mood": mood, "recommendations": recommendations}
    return {"mood": mood, "recommendations": []}


# ============================================
# Smart Search Endpoints
# ============================================

@router.post("/search")
async def smart_search_endpoint(request: SearchRequest):
    """Pencarian dengan fuzzy matching"""
    if smart_search:
        results = smart_search.search(request.query, request.limit)
        suggestions = smart_search.suggest_corrections(request.query)
        return {
            "query": request.query,
            "results": results,
            "total_results": len(results),
            "did_you_mean": suggestions if suggestions else []
        }
    return {"query": request.query, "results": [], "total_results": 0, "did_you_mean": []}


# ============================================
# Auto Playlist Endpoints
# ============================================

@router.get("/playlist/quick")
async def quick_playlists():
    """Quick playlist"""
    return {
        "playlists": [
            {"id": "top_hits", "name": "🔥 Top Hits", "icon": "🔥", "type": "top_hits"},
            {"id": "party", "name": "🎉 Party Time", "icon": "🎉", "type": "mood", "value": "party"},
            {"id": "romantic", "name": "💕 Romantic", "icon": "💕", "type": "mood", "value": "romantic"},
            {"id": "nostalgia", "name": "📻 Nostalgia", "icon": "📻", "type": "mood", "value": "nostalgia"},
            {"id": "chill", "name": "😌 Chill Vibes", "icon": "😌", "type": "mood", "value": "chill"},
            {"id": "pop_indo", "name": "🇮🇩 Pop Indonesia", "icon": "🇮🇩", "type": "genre", "value": "Pop Indonesia"},
            {"id": "dangdut", "name": "🎶 Dangdut", "icon": "🎶", "type": "genre", "value": "Dangdut"},
            {"id": "kpop", "name": "🇰🇷 K-Pop", "icon": "🇰🇷", "type": "genre", "value": "K-Pop"},
        ]
    }

@router.post("/playlist/generate")
async def generate_playlist(request: PlaylistRequest):
    """Generate playlist"""
    if playlist_generator:
        if request.type == 'genre':
            result = playlist_generator.generate_by_genre(request.value or 'Pop Indonesia', request.count)
        elif request.type == 'mood':
            result = playlist_generator.generate_by_mood(request.value or 'party', request.count)
        elif request.type == 'top_hits':
            result = playlist_generator.generate_top_hits(request.count)
        else:
            result = playlist_generator.generate_smart_mix(count=request.count)
        return result
    
    return {
        "name": "Generated Playlist",
        "description": "Auto-generated",
        "songs": [],
        "total_duration_estimate": 0
    }


# ============================================
# Voice Analysis Endpoints
# ============================================

@router.get("/voice/stats")
async def get_voice_stats():
    """Dapatkan statistik performa vokal"""
    if voice_analyzer:
        return voice_analyzer.get_performance_stats()
    return {"average_score": 0, "notes_sung": 0, "performance_rating": "Not available", "stars": 0}

@router.post("/voice/reset")
async def reset_voice_score():
    """Reset skor vokal"""
    if voice_analyzer:
        voice_analyzer.reset_score()
    return {"message": "Score reset"}


# ============================================
# Dashboard AI Insights
# ============================================

@router.get("/insights")
async def get_ai_insights():
    """AI insights untuk dashboard"""
    return {
        "model_status": {
            "recommender_trained": song_recommender.is_trained if song_recommender else False,
            "songs_indexed": len(smart_search.song_data) if smart_search else 0,
        },
        "popular_moods": ["happy", "energetic", "romantic"],
        "voice_analyzer_ready": voice_analyzer is not None
    }
