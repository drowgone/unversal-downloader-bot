from typing import List, Union, Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Bot Settings
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = []

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> List[int]:
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [int(i.strip()) for i in v.split(",") if i.strip()]
        return v

    # Database Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "media_downloader"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis & Celery Settings
    REDIS_URL: str = "redis://redis:6379/0"

    # Storage Settings
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    CLEANUP_INTERVAL_MINUTES: int = 30

    # S3 / MinIO Settings
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "media-processing"
    S3_REGION_NAME: str = "us-east-1"
    S3_SIGNED_URL_EXPIRY: int = 86400  # 24 hours

    # Proxy Settings
    PROXY_POOL: List[str] = []
    # Instagram Settings
    INSTAGRAM_COOKIES_PATH: Optional[Path] = None
    USER_AGENT_LIST: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Subscription & Limits
    FREE_DAILY_LIMIT: int = 5
    FREE_PLAYLIST_MAX: int = 10
    PREMIUM_DAILY_LIMIT: int = 100
    PREMIUM_PLAYLIST_MAX: int = 100
    
    # Global Limits
    MAX_CONCURRENT_JOBS_PER_USER: int = 3
    GLOBAL_CONCURRENT_JOBS: int = 20
    MAX_FILE_SIZE_MB: int = 50  # TG limit
    MAX_S3_FILE_SIZE_MB: int = 2000 # 2GB

settings = Settings()
