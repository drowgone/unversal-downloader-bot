import os
import time
from app.workers.celery_app import celery_app
from app.services.instagram_service import instagram_service
from app.services.user_service import user_service
from app.services.file_service import file_service
from app.workers.media_tasks import create_progress_hook
from app.db.session import SessionLocal
from app.db.models import JobStatus, MediaItem
from app.core.logging import logger
from app.core.config import settings

@celery_app.task(name="process_instagram_job", bind=True, max_retries=3, queue="media")
def process_instagram_job(self, user_id: int, job_id: str, url: str):
    db = SessionLocal()
    try:
        logger.info(f"Processing Instagram job {job_id} for user {user_id}")
        user_service.update_job_status(db, job_id, JobStatus.PENDING, celery_task_id=self.request.id)
        
        # 1. Extract info (handle login/private account errors)
        import asyncio
        try:
            info = asyncio.run(instagram_service.extract_info(url))
        except Exception as e:
            error_msg = str(e)
            if "login required" in error_msg.lower():
                user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Authentication required. Please check bot cookies.")
            elif "private" in error_msg.lower():
                user_service.update_job_status(db, job_id, JobStatus.FAILED, error="This is a private account.")
            else:
                user_service.update_job_status(db, job_id, JobStatus.FAILED, error=f"Instagram/TikTok error: {error_msg}")
            return

        if not info:
            user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Could not extract media info.")
            return

        # 2. Check if it's a carousel (playlist in yt-dlp terms)
        is_carousel = info.get('_type') == 'playlist' or 'entries' in info
        title = info.get('title', 'Media Post')
        
        user_service.update_job_status(
            db, job_id, JobStatus.DOWNLOADING, 
            title=title,
            media_type='carousel' if is_carousel else 'video'
        )

        # 3. Download
        hook, hook_db = create_progress_hook(job_id)
        try:
            files = asyncio.run(instagram_service.download_media(url, user_id, job_id, progress_hook=hook))
        finally:
            hook_db.close()
        
        # Fallback: scan directory if result list is unreliable
        job_dir = settings.STORAGE_DIR / str(user_id) / job_id / "instagram"
        if not files and job_dir.exists():
            files = [str(job_dir / f) for f in os.listdir(job_dir) if os.path.isfile(job_dir / f)]

        if not files:
            user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Download failed. This might be a private post or story requiring cookies.")
            return

        # 4. Handle results
        if len(files) > 1:
            # Carousel: Zip if many, otherwise mark for media group
            if len(files) > 10: 
                user_service.update_job_status(db, job_id, JobStatus.CONVERTING)
                zip_path = file_service.zip_files(files, f"instagram_{job_id}")
                user_service.update_job_status(db, job_id, JobStatus.COMPLETED, storage_path=zip_path)
            else:
                # Mark as carousel by saving the first but the bot will look for more
                user_service.update_job_status(db, job_id, JobStatus.COMPLETED, storage_path=files[0], media_type='carousel')
        else:
            user_service.update_job_status(db, job_id, JobStatus.COMPLETED, storage_path=files[0])

        logger.info(f"Instagram Job {job_id} completed. Found {len(files)} files.")

    except Exception as e:
        logger.error(f"Error in Instagram job {job_id}: {e}")
        try:
            self.retry(exc=e, countdown=10)
        except self.MaxRetriesExceededError:
            user_service.update_job_status(db, job_id, JobStatus.FAILED, error=str(e))
    finally:
        db.close()
