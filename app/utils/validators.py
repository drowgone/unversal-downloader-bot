import re
from urllib.parse import urlparse
from app.core.exceptions import PlatformException

class Validator:
    SUPPORTED_DOMAINS = [
        'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com', 
        'twitter.com', 'x.com', 'facebook.com', 'soundcloud.com'
    ]

    @staticmethod
    def validate_url(url: str) -> bool:
        if not url.startswith(('http://', 'https://')):
            return False
            
        try:
            domain = urlparse(url).netloc.replace('www.', '')
            # Simple check, yt-dlp will handle the rest, but we filter obvious spam
            return any(d in domain for d in Validator.SUPPORTED_DOMAINS) or "." in domain
        except Exception:
            return False

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # Remove non-ascii and special chars
        return re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')
