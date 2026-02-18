from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "media_downloader",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.media_tasks", 
        "app.workers.playlist_tasks", 
        "app.workers.cleanup_tasks",
        "app.workers.instagram_tasks"
    ]
)

celery_app.conf.update(
    task_default_queue="media",
    task_routes={
        "process_media_job": {"queue": "media"},
        "download_media_item": {"queue": "media"},
        "finalize_playlist_job": {"queue": "playlists"},
        "periodic_cleanup": {"queue": "media"},
        "process_instagram_job": {"queue": "media"},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    # Periodic tasks
    beat_schedule={
        "cleanup-every-30-minutes": {
            "task": "periodic_cleanup",
            "schedule": 1800.0,
        },
    },
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max per task
)
