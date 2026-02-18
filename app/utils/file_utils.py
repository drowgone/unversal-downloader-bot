import os
import shutil
import zipfile
from typing import List
from app.core.logging import logger

class FileUtils:
    @staticmethod
    def ensure_dir(path: str):
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def get_file_size_mb(path: str) -> float:
        if not os.path.exists(path):
            return 0.0
        return os.path.getsize(path) / (1024 * 1024)

    @staticmethod
    def zip_files(files: List[str], zip_path: str) -> bool:
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    if os.path.exists(file):
                        zipf.write(file, os.path.basename(file))
            return True
        except Exception as e:
            logger.error(f"Zipping failed: {e}")
            return False

    @staticmethod
    def cleanup_dir(path: str):
        if os.path.exists(path):
            shutil.rmtree(path)
            logger.info(f"Cleaned up directory: {path}")
