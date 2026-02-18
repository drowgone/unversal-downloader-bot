import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional
from app.core.logging import logger
from app.core.config import settings

class FileService:
    @staticmethod
    def get_user_job_dir(user_id: int, job_id: str) -> Path:
        path = settings.STORAGE_DIR / str(user_id) / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def zip_files(file_paths: List[str], zip_name: str) -> Optional[str]:
        """Create a zip file from a list of file paths."""
        if not file_paths:
            return None
        
        try:
            zip_path = f"{os.path.splitext(file_paths[0])[0]}_{zip_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in file_paths:
                    if os.path.exists(file):
                        zipf.write(file, os.path.basename(file))
            return zip_path
        except Exception as e:
            logger.error(f"Error creating zip: {e}")
            return None

    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        if not os.path.exists(file_path):
            return 0
        return os.path.getsize(file_path) / (1024 * 1024)

    @staticmethod
    def cleanup_job_files(user_id: int, job_id: str):
        """Delete storage directory for a specific job."""
        job_dir = settings.STORAGE_DIR / str(user_id) / job_id
        if job_dir.exists():
            try:
                shutil.rmtree(job_dir)
                logger.info(f"Cleaned up files for job {job_id}")
            except Exception as e:
                logger.error(f"Error cleaning up job {job_id}: {e}")

    @staticmethod
    def generic_cleanup():
        """Periodic cleanup of old files in storage."""
        # This will be called by a scheduled task
        # Implementation could check directory mtime
        pass

file_service = FileService()
