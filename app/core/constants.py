from enum import Enum

class MediaPlatforms(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    SOUNDCLOUD = "soundcloud"
    GENERIC = "generic"

class MediaTypes(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    CAROUSEL = "carousel"
    PLAYLIST = "playlist"
    STORY = "story"
    REEL = "reel"

# Internal Constants
DEFAULT_MP3_BITRATE = "192k"
DEFAULT_VIDEO_QUALITY = "720"
MAX_TG_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SIGNED_URL_EXPIRY = 86400  # 24 hours
JOB_POLLING_INTERVAL = 5
CLEANUP_THRESHOLD_HOURS = 1
