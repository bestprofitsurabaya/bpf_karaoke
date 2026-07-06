# Modifikasi fungsi scan pada backend/main.py untuk integrasi API Internet
import httpx

async def fetch_music_metadata(artist: str, title: str):
    """Mencari genre dan nama artis resmi dari API internet (Deezer)"""
    try:
        query = f"artist:\"{artist}\" track:\"{title}\""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.deezer.com/search", 
                params={"q": query, "limit": 1}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    track_info = data["data"][0]
                    # Ambil data artis resmi
                    official_artist = track_info.get("artist", {}).get("name", artist)
                    
                    # Deezer tidak langsung memberikan genre di search track, kita fetch ke albumnya
                    album_id = track_info.get("album", {}).get("id")
                    genre_name = "Pop" # Default fallback
                    if album_id:
                        album_res = await client.get(f"https://api.deezer.com/album/{album_id}")
                        if album_res.status_code == 200:
                            album_data = album_res.json()
                            if album_data.get("genres", {}).get("data"):
                                genre_name = album_data["genres"]["data"][0].get("name", "Pop")
                    
                    return official_artist, genre_name
    except Exception as e:
        print(f"Internet metadata fetch failed: {str(e)}")
    return artist, "Unknown"

# Implementasikan ke dalam rute scan API
@app.post("/api/admin/songs/scan")
async def scan(path: Optional[str] = Query(None), db=Depends(get_db)):
    sp = Path(path) if path else mp
    if not sp.exists(): raise HTTPException(404, "Path tidak ditemukan")
    ext = {".mp4", ".mkv", ".avi", ".webm", ".mov"}
    n = 0
    for f in sp.rglob("*"):
        if f.suffix.lower() not in ext: continue
        if (await db.execute(select(Song).where(Song.file_path == str(f)))).scalar_one_or_none(): continue
        
        nm = f.stem; art = "Unknown"; tit = nm
        if " - " in nm: 
            p = nm.split(" - ", 1)
            art = p[0].strip()
            tit = p[1].strip()
            
            # FITUR BARU: Ambil metadata dari internet secara otomatis
            art, fetched_genre = await fetch_music_metadata(art, tit)
        else:
            fetched_genre = "Unknown"
            
        db.add(Song(
            title=tit, 
            artist=art, 
            genre=fetched_genre, 
            file_path=str(f), 
            file_format=f.suffix.lower().replace(".", ""), 
            is_active=True
        ))
        n += 1
    await db.commit()
    return {"message": f"{n} lagu baru berhasil ditambahkan dengan metadata internet", "new_songs": n}
