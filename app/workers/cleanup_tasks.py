from app.workers.celery_app import celery_app
from app.services.file_service import file_service
from app.services.storage_service import storage_service
from app.db.session import SessionLocal
from app.db.models import Job, JobStatus
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.logging import logger

@celery_app.task(name="periodic_cleanup", queue="media")
def periodic_cleanup():
    """Enterprise cleanup: Local transience + S3 expiry."""
    db = SessionLocal()
    try:
        # 1. Local cleanup (older than 1 hour for safety in distributed)
        expiry = datetime.utcnow() - timedelta(hours=1)
        old_jobs = db.query(Job).filter(Job.created_at < expiry).all()
        
        for job in old_jobs:
            file_service.cleanup_job_files(job.user_id, job.id)
            
        # 2. S3 cleanup could be handled by S3 Lifecycle Policies (recommended)
        # But we can also check for jobs marked for deletion
        logger.info(f"Enterprise cleanup processed {len(old_jobs)} jobs")
    finally:
        db.close()
