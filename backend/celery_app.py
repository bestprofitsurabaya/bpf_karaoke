"""
Celery Application Configuration
Untuk background tasks: transcoding video, upload ke MinIO
"""

import os
from celery import Celery
from celery.schedules import crontab

# Broker & Backend URLs
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://karaoke_redis:6379/1')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://karaoke_redis:6379/2')

# Create Celery app
app = Celery(
    'karaoke_tasks',
    broker=broker_url,
    backend=result_backend,
    include=['celery_tasks']
)

# Celery Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Jakarta',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 jam max per task
    task_soft_time_limit=3000,  # 50 menit soft limit
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=1,
)

# Periodic Tasks Schedule
app.conf.beat_schedule = {
    'scan-new-media-every-5-minutes': {
        'task': 'celery_tasks.scan_for_new_media',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-failed-transcodes-daily': {
        'task': 'celery_tasks.cleanup_failed_transcodes',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'sync-to-minio-hourly': {
        'task': 'celery_tasks.sync_media_to_minio',
        'schedule': crontab(minute=0),  # Every hour
    },
}

# Task routing
app.conf.task_routes = {
    'celery_tasks.transcode_video': {'queue': 'transcoding'},
    'celery_tasks.upload_to_minio': {'queue': 'upload'},
    'celery_tasks.scan_for_new_media': {'queue': 'maintenance'},
    'celery_tasks.cleanup_failed_transcodes': {'queue': 'maintenance'},
    'celery_tasks.sync_media_to_minio': {'queue': 'maintenance'},
}

if __name__ == '__main__':
    app.start()
