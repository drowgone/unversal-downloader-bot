import os
from app.workers.celery_app import celery_app
from app.services.file_service import file_service
from app.services.storage_service import storage_service
from app.services.user_service import user_service
from app.db.session import SessionLocal
from app.db.models import JobStatus, MediaItem, Job
from app.core.logging import logger
from app.core.config import settings

@celery_app.task(name="finalize_playlist_job", queue="playlists")
def finalize_playlist_job(user_id: int, job_id: str):
    """SaaS playlist finalizer: Batch -> Zip -> S3 if needed."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return
        
        items = db.query(MediaItem).filter(MediaItem.job_id == job_id).all()
        completed = [i for i in items if i.status == JobStatus.COMPLETED]
        failed = [i for i in items if i.status == JobStatus.FAILED]
        
        job.completed_items = len(completed)
        job.failed_items = len(failed)
        db.commit()

        if len(completed) + len(failed) == job.total_items:
            # Batch complete
            user_service.update_job_status(db, job_id, JobStatus.CONVERTING)
            
            # 1. Zip local files
            file_paths = [i.file_path for i in completed if i.file_path]
            zip_path = file_service.zip_files(file_paths, "full_package")
            
            if not zip_path:
                user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Archiving failed")
                return

            # 2. Logic: Send directly or S3?
            file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
            
            if file_size_mb > settings.MAX_FILE_SIZE_MB:
                user_service.update_job_status(db, job_id, JobStatus.UPLOADING)
                s3_key = storage_service.upload_file(zip_path, user_id, job_id)
                if s3_key:
                    s3_url = storage_service.get_signed_url(s3_key)
                    user_service.update_job_status(db, job_id, JobStatus.COMPLETED, s3_url=s3_url, s3_key=s3_key)
                else:
                    user_service.update_job_status(db, job_id, JobStatus.FAILED, error="S3 upload failed for archive")
            else:
                user_service.update_job_status(db, job_id, JobStatus.COMPLETED, storage_path=zip_path)

    finally:
        db.close()
