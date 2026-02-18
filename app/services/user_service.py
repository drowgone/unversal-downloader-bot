from sqlalchemy.orm import Session
from app.db.models import User, Job, JobStatus, MediaItem, SubscriptionType
from typing import Optional, List
from app.core.logging import logger
from app.core.config import settings

class UserService:
    @staticmethod
    def get_or_create_user(db: Session, user_id: int, username: str = None, full_name: str = None) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            sub_type = SubscriptionType.ADMIN if user_id in settings.ADMIN_IDS else SubscriptionType.FREE
            user = User(id=user_id, username=username, full_name=full_name, subscription_type=sub_type)
            db.add(user)
            try:
                db.commit()
                db.refresh(user)
            except:
                db.rollback()
                user = db.query(User).filter(User.id == user_id).first()
        else:
            # Sync admin status if it changed in .env
            is_admin_in_config = user_id in settings.ADMIN_IDS
            if is_admin_in_config and user.subscription_type != SubscriptionType.ADMIN:
                user.subscription_type = SubscriptionType.ADMIN
                db.commit()
                db.refresh(user)
            elif not is_admin_in_config and user.subscription_type == SubscriptionType.ADMIN:
                user.subscription_type = SubscriptionType.FREE
                db.commit()
                db.refresh(user)
        return user

    @staticmethod
    def create_job(db: Session, user_id: int, job_id: str, url: str, platform: str = None, media_type: str = 'video') -> Job:
        job = Job(
            id=job_id,
            user_id=user_id,
            url=url,
            platform=platform,
            media_type=media_type,
            status=JobStatus.PENDING
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def update_job_status(db: Session, job_id: str, status: JobStatus, error: str = None, **kwargs):
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            if error:
                job.error_message = error
            for key, value in kwargs.items():
                setattr(job, key, value)
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def get_active_jobs_count(db: Session, user_id: int) -> int:
        return db.query(Job).filter(
            Job.user_id == user_id,
            Job.status.in_([JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.CONVERTING])
        ).count()

user_service = UserService()
