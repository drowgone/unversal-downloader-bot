from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, BigInteger, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base

class JobStatus(enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    COMPRESSING = "compressing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SubscriptionType(enum.Enum):
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    subscription_type = Column(Enum(SubscriptionType), default=SubscriptionType.FREE)
    daily_usage_count = Column(Integer, default=0)
    last_usage_date = Column(DateTime(timezone=True), server_default=func.now())
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    jobs = relationship("Job", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    platform = Column(String, nullable=True)
    media_type = Column(String, nullable=True) # e.g., 'video', 'playlist', 'carousel'
    format_settings = Column(JSON, nullable=True) # e.g., {"bitrate": "320kbps", "quality": "1080p"}
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    current_speed = Column(String, nullable=True)
    eta = Column(String, nullable=True)
    download_percentage = Column(Integer, default=0)
    
    # Storage info
    storage_path = Column(String, nullable=True)
    s3_url = Column(String, nullable=True)
    s3_key = Column(String, nullable=True)
    result_file_id = Column(String, nullable=True)
    
    error_message = Column(String, nullable=True)
    celery_task_id = Column(String, nullable=True) # For cancellation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="jobs")
    media_items = relationship("MediaItem", back_populates="job")

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    title = Column(String)
    url = Column(String)
    file_path = Column(String, nullable=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    celery_task_id = Column(String, nullable=True)
    
    job = relationship("Job", back_populates="media_items")

class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String)
    media_type = Column(String)
    file_size_mb = Column(Integer)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
