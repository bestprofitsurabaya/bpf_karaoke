"""
Genres Routes - Dynamic Genre List & Detection
PT BESTPROFIT FUTURES SURABAYA
"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, update, or_

from database import get_db
from models import Song
from routers.auth import get_admin_user

router = APIRouter(tags=["Genres"])


@router.get("/api/genres")
async def get_genres(db=Depends(get_db)):
    """
    Get dynamic genre list dari database (SELECT DISTINCT)
    Genre list tumbuh otomatis tanpa hardcode
    """
    r = await db.execute(
        select(Song.genre, func.count(Song.id))
        .where(Song.is_active == True, Song.genre.isnot(None), Song.genre != 'Unknown')
        .group_by(Song.genre)
        .order_by(func.count(Song.id).desc())
    )

    genres = []
    for row in r:
        genres.append({
            'genre': row[0],
            'count': row[1],
            'is_custom': True  # Semua genre dari DB adalah dynamic
        })

    # Tambahkan genre defaults jika belum ada di DB
    default_genres = [
        'Pop Indonesia', 'Dangdut', 'K-Pop', 'Barat', 'Rock',
        'Mandarin', 'Anak', 'Religi', 'Daerah', 'Jazz', 'EDM', 'Hip Hop'
    ]

    existing_genres = {g['genre'] for g in genres}
    for dg in default_genres:
        if dg not in existing_genres:
            genres.append({
                'genre': dg,
                'count': 0,
                'is_custom': False
            })

    return {
        'genres': sorted(genres, key=lambda x: x['count'], reverse=True),
        'total': len(genres),
        'message': 'Genre list diambil secara dinamis dari database'
    }


@router.get("/api/genres/list")
async def list_all_genres(db=Depends(get_db)):
    """Get all unique genres with song count"""
    r = await db.execute(
        select(Song.genre, func.count(Song.id))
        .where(Song.is_active == True, Song.genre.isnot(None), Song.genre != '')
        .group_by(Song.genre)
        .order_by(func.count(Song.id).desc())
    )
    genres = [{"name": row[0], "count": row[1]} for row in r]
    return {"genres": genres, "total": len(genres)}


@router.post("/api/genres/detect")
async def auto_detect_genres(db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Auto-detect genre for songs without genre (admin only)"""
    # Genre keyword mapping
    genre_keywords = {
        "Pop Indonesia": ["pop", "indonesia", "cinta", "hati", "rindu", "sayang"],
        "Dangdut": ["dangdut", "koplo", "jaran", "goyang"],
        "Rock": ["rock", "metal", "punk", "gitar", "band"],
        "K-Pop": ["k-pop", "kpop", "korea", "bts", "blackpink", "exo"],
        "Barat": ["west", "english", "love", "you", "baby", "night", "dream"],
        "Mandarin": ["mandarin", "chinese", "cina", "tiongkok"],
        "Anak": ["anak", "kids", "child", "balita", "tk"],
        "Religi": ["religi", "islam", "sholawat", "quran", "rohani", "gereja"],
        "Daerah": ["daerah", "jawa", "sunda", "batak", "minang"],
        "Akustik": ["akustik", "acoustic", "unplugged"],
        "Ballad": ["ballad", "slow", "mellow"],
        "Jazz": ["jazz", "blues", "swing"],
        "EDM": ["edm", "dj", "remix", "electronic", "dance"],
        "Hip Hop": ["hip hop", "hiphop", "rap", "trap"],
    }

    # Get songs without genre
    r = await db.execute(
        select(Song).where(
            Song.is_active == True,
            or_(Song.genre.is_(None), Song.genre == '')
        )
    )
    songs = r.scalars().all()

    updated = 0
    for song in songs:
        title_lower = (song.title or '').lower()
        artist_lower = (song.artist or '').lower()
        combined = f"{title_lower} {artist_lower}"

        for genre, keywords in genre_keywords.items():
            if any(kw in combined for kw in keywords):
                song.genre = genre
                updated += 1
                break

    await db.commit()

    return {
        "message": f"Auto-detected genre for {updated} songs",
        "total_scanned": len(songs),
        "updated": updated
    }


@router.post("/api/genres/detect-online")
async def detect_genre_online(song_id: int, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Detect genre untuk satu lagu (admin only)"""
    from services.genre_detector import genre_detector

    r = await db.execute(select(Song).where(Song.id == song_id))
    song = r.scalar_one_or_none()
    if not song:
        raise HTTPException(404, "Song not found")

    result = await genre_detector.detect_genre_online(song.title, song.artist)

    if result and result.get('genre'):
        song.genre = result['genre']
        song.updated_at = datetime.utcnow()
        await db.commit()

    return {
        "song_id": song_id,
        "title": song.title,
        "artist": song.artist,
        "detected_genre": result.get('genre', 'Unknown'),
        "confidence": result.get('confidence', 0),
        "source": result.get('source', 'unknown'),
        "tags": result.get('tags', [])
    }


@router.post("/api/genres/detect-online-batch")
async def detect_genre_batch_online(limit: int = Query(50, le=200), db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Detect genre untuk banyak lagu tanpa genre (admin only)"""
    from services.genre_detector import genre_detector

    # Get songs without genre
    r = await db.execute(
        select(Song)
        .where(
            Song.is_active == True,
            or_(Song.genre.is_(None), Song.genre == '')
        )
        .limit(limit)
    )
    songs = r.scalars().all()

    songs_data = [{"id": s.id, "title": s.title, "artist": s.artist} for s in songs]

    # Run batch detection
    results = []
    for song_data in songs_data:
        try:
            genre_info = await genre_detector.detect_genre_online(
                song_data['title'],
                song_data.get('artist')
            )

            if genre_info.get('genre') and genre_info.get('confidence', 0) > 0.3:
                # Update database
                await db.execute(
                    update(Song)
                    .where(Song.id == song_data['id'])
                    .values(genre=genre_info['genre'], updated_at=datetime.utcnow())
                )
                results.append({
                    "song_id": song_data['id'],
                    "title": song_data['title'],
                    "detected_genre": genre_info['genre'],
                    "confidence": genre_info['confidence']
                })

            # Rate limit protection
            await asyncio.sleep(0.5)

        except Exception as e:
            results.append({
                "song_id": song_data['id'],
                "error": str(e)
            })

    await db.commit()

    return {
        "message": f"Detected genre for {len(results)} songs",
        "total_scanned": len(songs_data),
        "detected": len(results),
        "results": results
    }


@router.get("/api/genres/detector-stats")
async def detector_stats(_admin=Depends(get_admin_user)):
    """Get genre detector statistics (admin only)"""
    from services.genre_detector import genre_detector
    return genre_detector.get_stats()


@router.post("/api/songs/batch-genre")
async def batch_update_genre(req: dict, db=Depends(get_db), _admin=Depends(get_admin_user)):
    """Batch update genre untuk multiple songs (admin only)"""
    song_ids = req.get("song_ids", [])
    genre = req.get("genre", "")

    if not song_ids or not genre:
        raise HTTPException(400, "song_ids and genre required")

    await db.execute(
        update(Song)
        .where(Song.id.in_(song_ids))
        .values(genre=genre, updated_at=datetime.utcnow())
    )
    await db.commit()

    return {"message": f"Updated genre to '{genre}' for {len(song_ids)} songs"}
