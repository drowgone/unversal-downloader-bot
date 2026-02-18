from typing import Dict, Any, List
from app.services.user_service import user_service
from app.db.session import SessionLocal
from app.db.models import JobStatus, MediaItem
from app.core.logging import logger

class PlaylistService:
    @staticmethod
    def extract_and_queue(info: Dict[str, Any], user_id: int, job_id: str):
        """Batch engine: Create entries and trigger workers."""
        db = SessionLocal()
        try:
            entries = info.get('entries', [])
            total = len(entries)
            
            logger.info(f"Extracting playlist with {total} entries for job {job_id}")
            
            # Update main job
            user_service.update_job_status(
                db, job_id, 
                JobStatus.PENDING, 
                total_items=total,
                title=info.get('title', 'Playlist')
            )
            
            for entry in entries:
                if not entry: continue
                item = MediaItem(
                    job_id=job_id,
                    title=entry.get('title'),
                    url=entry.get('url') or entry.get('webpage_url'),
                    status=JobStatus.PENDING
                )
                db.add(item)
            
            db.commit()
            return total
        except Exception as e:
            logger.error(f"Batch extraction failed for {job_id}: {e}")
            user_service.update_job_status(db, job_id, JobStatus.FAILED, error="Playlist extraction failed")
            return 0
        finally:
            db.close()

playlist_service = PlaylistService()
