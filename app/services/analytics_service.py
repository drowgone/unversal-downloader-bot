from sqlalchemy.orm import Session
from app.db.models import Analytics
from app.core.logging import logger

class AnalyticsService:
    @staticmethod
    def log_download(db: Session, user_id: int, platform: str, media_type: str, file_size_mb: int):
        try:
            entry = Analytics(
                user_id=user_id,
                platform=platform,
                media_type=media_type,
                file_size_mb=file_size_mb
            )
            db.add(entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log analytics: {e}")

analytics_service = AnalyticsService()
