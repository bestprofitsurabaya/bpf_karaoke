"""
Celery Task Routes - Vocal Remove, Batch Genre, Status
PT BESTPROFIT FUTURES SURABAYA
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select

from database import get_db
from models import Song
from routers.auth import get_admin_user

router = APIRouter(tags=["Background Tasks"])


@router.post("/api/tasks/vocal-remove/{song_id}")
async def start_vocal_remove(song_id: int, method: str = "ffmpeg", db=Depends(get_db)):
    """Start AI vocal removal sebagai background task Celery"""
    r = await db.execute(select(Song).where(Song.id == song_id))
    song = r.scalar_one_or_none()
    if not song:
        raise HTTPException(404, "Song not found")

    from celery_tasks import vocal_remove
    task = vocal_remove.delay(song_id, song.file_path, method)

    return {
        "message": "Vocal removal started",
        "task_id": task.id,
        "song_id": song_id,
        "method": method,
        "check_status": f"/api/tasks/status/{task.id}"
    }


@router.post("/api/tasks/batch-genre")
async def start_batch_genre(limit: int = Query(100, le=500), _admin=Depends(get_admin_user)):
    """Start batch genre detection sebagai background task Celery (admin only)"""
    from celery_tasks import batch_auto_genre
    task = batch_auto_genre.delay(limit)

    return {
        "message": f"Batch genre detection started for {limit} songs",
        "task_id": task.id,
        "check_status": f"/api/tasks/status/{task.id}"
    }


@router.get("/api/tasks/status/{task_id}")
async def get_task_status(task_id: str):
    """Cek status Celery task"""
    from celery_app import app as celery_app
    from celery.result import AsyncResult

    task = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task.status,
        "ready": task.ready(),
        "successful": task.successful() if task.ready() else None,
    }

    if task.ready():
        response["result"] = task.result if task.successful() else str(task.info)
    elif task.status == 'PROGRESS':
        response["progress"] = task.info

    return response


@router.get("/api/tasks/stats")
async def get_celery_stats(_admin=Depends(get_admin_user)):
    """Get Celery worker statistics (admin only)"""
    from celery_app import app as celery_app

    stats = {
        "active_tasks": [],
        "scheduled_tasks": [],
    }

    try:
        inspect = celery_app.control.inspect()
        stats["active_tasks"] = inspect.active() or {}
        stats["scheduled_tasks"] = inspect.scheduled() or {}
        stats["registered_tasks"] = list(celery_app.tasks.keys())
    except Exception as e:
        stats["error"] = str(e)

    return stats
