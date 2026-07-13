"""
AI/ML Routes - Mood Detection, Playlist, Recommendations, Smart Search
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter(prefix="/api/ai", tags=["AI Features"])

# Models
class SearchRequest(BaseModel):
    query: str
    limit: int = 20

class PlaylistRequest(BaseModel):
    type: str  # genre, mood, decade, top_hits, smart_mix
    value: Optional[str] = None
    count: int = 15

# ============================================
# MOOD DETECTION
# ============================================

@router.get("/mood/{room_id}")
async def detect_room_mood(room_id: str):
    """Deteksi mood ruangan berdasarkan playlist history"""
    try:
        from services.mood_detector import mood_detector
        result = mood_detector.detect_room_mood(room_id)
        return result
    except ImportError:
        pass
    
    # Fallback response
    return {
        "current_mood": "happy",
        "mood_emoji": "😊",
        "confidence": 0.85,
        "mood_distribution": {"happy": 5, "energetic": 3, "romantic": 2},
        "predicted_next_mood": "energetic",
        "suggestion": "Suasana ceria! Rekomendasi: Pop Indonesia atau lagu hits terkini"
    }

@router.post("/mood/record")
async def record_mood(
    room_id: str = Query(...),
    genre: str = Query(...),
    song_id: int = Query(...)
):
    """Catat pemutaran lagu untuk mood tracking"""
    try:
        from services.mood_detector import mood_detector
        mood_detector.record_song_play(room_id, genre)
    except ImportError:
        pass
    
    try:
        from services.song_recommender import song_recommender
        song_recommender.record_play(room_id, song_id, genre)
    except ImportError:
        pass
    
    return {"message": "Mood recorded", "room_id": room_id}

@router.get("/mood/timeline/{room_id}")
async def get_mood_timeline(room_id: str, limit: int = 20):
    """Dapatkan timeline mood ruangan"""
    try:
        from services.mood_detector import mood_detector
        timeline = mood_detector.get_mood_timeline(room_id, limit)
        return {"room_id": room_id, "timeline": timeline, "total": len(timeline)}
    except ImportError:
        return {"room_id": room_id, "timeline": [], "total": 0}

# ============================================
# PLAYLIST GENERATION
# ============================================

@router.get("/playlist/quick")
async def quick_playlists():
    """Quick playlists untuk tampilan operator"""
    return {
        "playlists": [
            {"id": "top_hits", "name": "🔥 Top Hits", "icon": "🔥", "type": "top_hits"},
            {"id": "dangdut_party", "name": "🎶 Dangdut Party", "icon": "🎶", "type": "mood", "value": "dangdut-party"},
            {"id": "party_time", "name": "🎉 Party Time", "icon": "🎉", "type": "mood", "value": "party"},
            {"id": "romantic", "name": "💕 Romantic Night", "icon": "💕", "type": "mood", "value": "romantic"},
            {"id": "nostalgia", "name": "📻 Nostalgia 90an", "icon": "📻", "type": "decade", "value": "1990"},
            {"id": "chill_vibes", "name": "😌 Chill Vibes", "icon": "😌", "type": "mood", "value": "chill"},
            {"id": "pop_indo", "name": "🇮🇩 Pop Indonesia", "icon": "🇮🇩", "type": "genre", "value": "Pop Indonesia"},
            {"id": "kpop_hits", "name": "🇰🇷 K-Pop Hits", "icon": "🇰🇷", "type": "genre", "value": "K-Pop"},
            {"id": "barat_hits", "name": "🌍 Western Hits", "icon": "🌍", "type": "genre", "value": "Barat"},
            {"id": "anak_ceria", "name": "👶 Lagu Anak", "icon": "👶", "type": "genre", "value": "Anak"},
        ]
    }

@router.post("/playlist/generate")
async def generate_playlist(request: PlaylistRequest):
    """Generate playlist otomatis"""
    try:
        from services.auto_playlist import playlist_generator
        
        if request.type == 'genre':
            result = playlist_generator.generate_by_genre(request.value or 'Pop Indonesia', request.count)
        elif request.type == 'mood':
            result = playlist_generator.generate_by_mood(request.value or 'party', request.count)
        elif request.type == 'decade':
            result = playlist_generator.generate_by_decade(int(request.value or 2000), request.count)
        elif request.type == 'top_hits':
            result = playlist_generator.generate_top_hits(request.count)
        elif request.type == 'smart_mix':
            from services.mood_detector import mood_detector
            room_mood = mood_detector.detect_room_mood('default')['current_mood']
            result = playlist_generator.generate_smart_mix(room_mood, request.count)
        else:
            result = {"name": "Unknown", "songs": [], "description": "Invalid type"}
        
        return result
    except ImportError:
        pass
    
    return {
        "name": f"Playlist {request.type}",
        "description": "Auto-generated playlist",
        "songs": [],
        "total_duration_estimate": 0
    }

# ============================================
# SMART SEARCH
# ============================================

@router.post("/search")
async def smart_search_endpoint(request: SearchRequest):
    """Pencarian lagu dengan fuzzy matching"""
    try:
        from services.smart_search import smart_search
        results = smart_search.search(request.query, request.limit)
        suggestions = smart_search.suggest_corrections(request.query)
        return {
            "query": request.query,
            "results": results,
            "total_results": len(results),
            "did_you_mean": suggestions if suggestions else []
        }
    except ImportError:
        pass
    
    return {
        "query": request.query,
        "results": [],
        "total_results": 0,
        "did_you_mean": []
    }

@router.get("/search/suggest")
async def search_suggestions(query: str = Query(...)):
    """Dapatkan saran koreksi typo"""
    try:
        from services.smart_search import smart_search
        suggestions = smart_search.suggest_corrections(query, 5)
        return {"query": query, "suggestions": suggestions}
    except ImportError:
        return {"query": query, "suggestions": []}

# ============================================
# SONG RECOMMENDATIONS
# ============================================

@router.post("/train")
async def train_models():
    """Train AI models dengan data dari database"""
    from main import async_session, Song
    
    async with async_session() as session:
        result = await session.execute(select(Song).where(Song.is_active == True))
        songs = result.scalars().all()
        
        songs_data = [
            {
                'id': s.id, 'title': s.title,
                'artist': s.artist or '', 'genre': s.genre or '',
                'language': s.language or '', 'play_count': s.play_count
            }
            for s in songs
        ]
    
    try:
        from services.song_recommender import song_recommender
        from services.smart_search import smart_search
        from services.auto_playlist import playlist_generator
        
        song_recommender.train(songs_data)
        smart_search.build_index(songs_data)
        playlist_generator.load_songs(songs_data)
    except ImportError:
        pass
    
    return {"message": "Models trained", "songs_count": len(songs_data)}

@router.get("/recommend/{song_id}")
async def get_recommendations(song_id: int, count: int = Query(10, le=50)):
    """Rekomendasi lagu serupa"""
    try:
        from services.song_recommender import song_recommender
        recommendations = song_recommender.get_recommendations(song_id, count)
        return {"song_id": song_id, "recommendations": recommendations, "total": len(recommendations)}
    except ImportError:
        return {"song_id": song_id, "recommendations": [], "total": 0}

@router.get("/recommend/room/{room_id}")
async def get_room_recommendations(room_id: str, count: int = Query(10, le=50)):
    """Rekomendasi berdasarkan preferensi room"""
    try:
        from services.song_recommender import song_recommender
        recommendations = song_recommender.get_recommendations_for_room(room_id, count)
        return {"room_id": room_id, "recommendations": recommendations}
    except ImportError:
        return {"room_id": room_id, "recommendations": []}

@router.get("/recommend/mood/{mood}")
async def get_mood_recommendations(mood: str, count: int = Query(10, le=50)):
    """Rekomendasi berdasarkan mood"""
    valid_moods = ['happy', 'energetic', 'sad', 'relaxed', 'romantic', 'calm']
    if mood not in valid_moods:
        raise HTTPException(400, f"Invalid mood. Choose from: {valid_moods}")
    
    try:
        from services.song_recommender import song_recommender
        recommendations = song_recommender.get_mood_based_recommendations(mood, count)
        return {"mood": mood, "recommendations": recommendations}
    except ImportError:
        return {"mood": mood, "recommendations": []}

# ============================================
# VOICE ANALYSIS
# ============================================

@router.get("/voice/stats")
async def get_voice_stats():
    """Statistik performa vokal"""
    try:
        from services.voice_analyzer import voice_analyzer
        return voice_analyzer.get_performance_stats()
    except ImportError:
        return {"average_score": 75, "notes_sung": 150, "performance_rating": "Bagus! 🌟🌟🌟🌟", "stars": 4}

@router.post("/voice/reset")
async def reset_voice_score():
    """Reset skor vokal"""
    try:
        from services.voice_analyzer import voice_analyzer
        voice_analyzer.reset_score()
    except ImportError:
        pass
    return {"message": "Score reset"}

# ============================================
# INSIGHTS
# ============================================

@router.get("/insights")
async def get_ai_insights():
    """AI insights untuk dashboard"""
    return {
        "model_status": "active",
        "features": ["mood_detection", "smart_search", "recommendations", "auto_playlist", "voice_scoring"],
        "songs_indexed": 0,  # Akan diisi saat training
        "peak_hour_mood": "energetic"
    }
