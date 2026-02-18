import os
import time
from app.workers.celery_app import celery_app
from app.services.media_service import media_service
from app.services.file_service import file_service
from app.services.storage_service import storage_service

from app.services.analytics_service import analytics_service
from app.services.user_service import user_service
from app.services.playlist_service import playlist_service
from app.utils.validators import Validator
from app.db.models import JobStatus, MediaItem, Job
from app.db.session import SessionLocal
from app.core.logging import logger
from app.core.config import settings

def create_progress_hook(job_id: str):
    db_hook = SessionLocal()
    last_update = 0
    
    def progress_hook(d):
        nonlocal last_update
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_update < 2: # Update every 2 seconds
                return
            
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                pct = int(float(p))
            except:
                pct = 0
                
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            
            user_service.update_job_status(
                db_hook, job_id, JobStatus.DOWNLOADING,
                download_percentage=pct,
                current_speed=speed,
                eta=eta
            )
            last_update = now
            
    return progress_hook, db_hook

@celery_app.task(name="process_media_job", bind=True, max_retries=3, queue="media")
def process_media_job(self, user_id: int, job_id: str, url: str, format_type: str = "mp3", quality: str = "best"):
    db = SessionLocal()
    try:
        logger.info(f"Starting process_media_job for {job_id} | URL: {url}")
        
        # Save task ID for cancellation
        user_service.update_job_status(db, job_id, JobStatus.PENDING, celery_task_id=self.request.id)
        
        # 1. Metadata Extraction
        logger.info(f"Extracting info for {job_id}...")
        info = media_service.extract_info(url)
        if not info:
            logger.error(f"Extraction failed for {job_id}")
            user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Platform not supported or link broken")
            return
        
        logger.info(f"Extraction successful for {job_id}: {info.get('title')}")

        # 1.5 Instagram specialized routing
        if "instagram.com" in url:
            from app.workers.instagram_tasks import process_instagram_job
            process_instagram_job.delay(user_id, job_id, url)
            return

        # 2. Routing
        if info.get('_type') == 'playlist':
            total = playlist_service.extract_and_queue(info, user_id, job_id)
            if total > 0:
                # Trigger child tasks
                items = db.query(MediaItem).filter(MediaItem.job_id == job_id).all()
                for item in items:
                    download_media_item.delay(user_id, job_id, item.id, format_type, quality)
            return

        # 3. Single Download
        user_service.update_job_status(db, job_id, JobStatus.DOWNLOADING, title=info.get('title'))
        
        hook, hook_db = create_progress_hook(job_id)
        try:
            file_path = media_service.download(url, user_id, job_id, format_type, quality, progress_hook=hook)
        finally:
            hook_db.close()
        
        if not file_path:
            user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Download engine error")
            return

        # 4. Storage Flow (Enterprise)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            user_service.update_job_status(db, job_id, JobStatus.UPLOADING)
            s3_key = storage_service.upload_file(file_path, user_id, job_id)
            if s3_key:
                s3_url = storage_service.get_signed_url(s3_key)
                user_service.update_job_status(db, job_id, JobStatus.COMPLETED, s3_url=s3_url, s3_key=s3_key)
            else:
                user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Cloud storage upload failed")
        else:
            user_service.update_job_status(db, job_id, JobStatus.COMPLETED, storage_path=file_path)

        # 5. Analytics
        analytics_service.log_download(db, user_id, info.get('extractor'), format_type, int(file_size_mb))

    except Exception as e:
        logger.error(f"Media job {job_id} failed: {e}")
        user_service.update_job_status(db, job_id, JobStatus.FAILED, error=str(e))
    finally:
        db.close()

@celery_app.task(name="download_media_item", bind=True, max_retries=3, queue="media")
def download_media_item(self, user_id: int, job_id: str, item_id: int, format_type: str, quality: str):
    db = SessionLocal()
    try:
        # Check if job was already cancelled
        job = db.query(Job).filter(Job.id == job_id).first()
        if job and job.status == JobStatus.CANCELLED:
            logger.info(f"Skipping download_media_item for cancelled job {job_id}")
            return

        item = db.query(MediaItem).filter(MediaItem.id == item_id).first()
        if not item: return

        # Record Task ID for cancellation
        item.celery_task_id = self.request.id
        item.status = JobStatus.DOWNLOADING
        db.commit()

        hook, hook_db = create_progress_hook(job_id)
        try:
            file_path = media_service.download(item.url, user_id, job_id, format_type, quality, progress_hook=hook)
        finally:
            hook_db.close()
        
        if file_path:
            item.status = JobStatus.COMPLETED
            item.file_path = file_path
        else:
            item.status = JobStatus.FAILED
        
        db.commit()
        # Fan-in check
        from app.workers.playlist_tasks import finalize_playlist_job
        finalize_playlist_job.delay(user_id, job_id)

    finally:
        db.close()
