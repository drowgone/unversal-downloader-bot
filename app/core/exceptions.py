class PlatformException(Exception):
    """Base exception for the platform."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class MediaExtractionError(PlatformException):
    """Raised when yt-dlp fails to extract info."""
    pass

class DownloadError(PlatformException):
    """Raised when download process fails."""
    pass

class ConversionError(PlatformException):
    """Raised when FFmpeg conversion fails."""
    pass

class StorageError(PlatformException):
    """Raised when S3 or local storage fails."""
    pass

class RateLimitError(PlatformException):
    """Raised when user exceeds limits."""
    pass

class SubscriptionError(PlatformException):
    """Raised for unauthorized subscription features."""
    pass
