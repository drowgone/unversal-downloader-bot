import boto3
import os
from botocore.config import Config
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logging import logger
from typing import Optional

class StorageService:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME,
            config=Config(signature_version='s3v4')
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        except ClientError:
            self.s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)
            logger.info(f"Created bucket {settings.S3_BUCKET_NAME}")

    def upload_file(self, local_path: str, user_id: int, job_id: str) -> Optional[str]:
        """Upload file to S3 and return the key."""
        filename = os.path.basename(local_path)
        s3_key = f"{user_id}/{job_id}/{filename}"
        
        try:
            self.s3.upload_file(local_path, settings.S3_BUCKET_NAME, s3_key)
            logger.info(f"Uploaded {filename} to S3 bucket {settings.S3_BUCKET_NAME}")
            return s3_key
        except Exception as e:
            logger.error(f"S3 Upload failed: {e}")
            return None

    def get_signed_url(self, s3_key: str) -> Optional[str]:
        """Generate a temporary signed URL."""
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=settings.S3_SIGNED_URL_EXPIRY
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None

    def delete_file(self, s3_key: str):
        """Delete file from S3."""
        try:
            self.s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
            logger.info(f"Deleted {s3_key} from S3")
        except Exception as e:
            logger.error(f"Failed to delete {s3_key}: {e}")

storage_service = StorageService()
