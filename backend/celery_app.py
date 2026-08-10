"""
Celery Configuration - Optimized for AI Background Tasks
PT BESTPROFIT FUTURES SURABAYA
"""

import os
from celery import Celery
from celery.schedules import crontab

# Broker & Backend
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://karaoke_redis:6379/1')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://karaoke_redis:6379/2')

app = Celery(
    'karaoke_tasks',
    broker=broker_url,
    backend=result_backend,
    include=['celery_tasks']
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Jakarta',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,       # 30 menit max per task (AI tasks bisa lama)
    task_soft_time_limit=1500,  # 25 menit soft limit
    worker_max_tasks_per_child=20,
    worker_prefetch_multiplier=1,
    result_expires=3600,        # Hasil task expire setelah 1 jam
)

# Queue routing
app.conf.task_routes = {
    'celery_tasks.transcode_video': {'queue': 'transcoding'},
    'celery_tasks.vocal_remove': {'queue': 'ai_heavy'},
    'celery_tasks.batch_auto_genre': {'queue': 'ai_heavy'},
    'celery_tasks.scan_for_new_media': {'queue': 'maintenance'},
    'celery_tasks.sweep_stale_parts': {'queue': 'maintenance'},
    'celery_tasks.cleanup_transcodes': {'queue': 'maintenance'},
    'celery_tasks.weekly_pipeline_report': {'queue': 'maintenance'},
}

# Periodic tasks
app.conf.beat_schedule = {
    'scan-new-media-every-10-minutes': {
        'task': 'celery_tasks.scan_for_new_media',
        'schedule': crontab(minute='*/10'),
    },
    # .part yatim dari worker yang mati (restart/OOM) diblokir s/d cleanup
    # harian 03:00 -> sweep tiap 5 menit agar lagu bisa diantre ulang lebih
    # cepat (task ringan: hanya rglob + Redis, tanpa query DB).
    'sweep-stale-parts-every-5-minutes': {
        'task': 'celery_tasks.sweep_stale_parts',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup-failed-transcodes-daily': {
        'task': 'celery_tasks.cleanup_transcodes',
        'schedule': crontab(hour=3, minute=0),
    },
    # Laporan mingguan pipeline via webhook (tiap Senin 07:00 Asia/Jakarta)
    'weekly-pipeline-report-monday-7am': {
        'task': 'celery_tasks.weekly_pipeline_report',
        'schedule': crontab(hour=7, minute=0, day_of_week=1),
    },
}

if __name__ == '__main__':
    app.start()
