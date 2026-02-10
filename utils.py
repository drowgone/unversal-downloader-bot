"""
Yordamchi funksiyalar
"""
import os
import re
import logging
from pathlib import Path

# Ranglar va formatlash uchun ANSI kodlari
class ColorFormatter(logging.Formatter):
    """Loglarni rangli qilib chiqarish uchun klass"""
    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"
    GREEN = "\x1b[32;20m"
    
    # Formatlar
    base_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    FORMATS = {
        logging.DEBUG: GREY + base_format + RESET,
        logging.INFO: BLUE + base_format + RESET,
        logging.WARNING: YELLOW + base_format + RESET,
        logging.ERROR: RED + base_format + RESET,
        logging.CRITICAL: BOLD_RED + base_format + RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        # Maxsus 'SUCCESS' statusi uchun yashil rang (ixtiyoriy)
        if hasattr(record, 'is_success') and record.is_success:
            log_fmt = self.GREEN + self.base_format + self.RESET
            
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)

# Logger sozlash
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter())

logger = logging.getLogger("BotCore")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Tashqi kutubxonalar loglarini kamaytirish
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


def is_valid_youtube_url(url: str) -> bool:
    """
    YouTube URL validatsiyasi (backward compatibility)
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=|playlist\?list=|shorts/)?([^&=%\?]{11}|[^&=%\?]{34})'
    )
    return bool(re.match(youtube_regex, url))


def is_valid_media_url(url: str) -> bool:
    """
    Umumiy media URL validatsiyasi (YouTube, Instagram, TikTok, va boshqalar)
    """
    # Asosiy URL pattern
    url_pattern = r'^https?://'
    
    # Qo'llab-quvvatlanadigan platformalar
    supported_platforms = [
        r'(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)(/shorts/)?',  # YouTube & Shorts
        r'(www\.)?instagram\.com',  # Instagram
        r'(www\.)?(tiktok\.com|vm\.tiktok\.com)',  # TikTok
        r'(www\.)?(facebook|fb)\.(com|watch)',  # Facebook
        r'(www\.)?(twitter|x)\.com',  # Twitter/X
        r'(www\.)?reddit\.com',  # Reddit
        r'(www\.)?vimeo\.com',  # Vimeo
        r'(www\.)?dailymotion\.com',  # Dailymotion
        r'(www\.)?soundcloud\.com',  # SoundCloud
        r'(www\.)?twitch\.tv',  # Twitch
    ]
    
    # Biror bir platformaga mos kelsa
    for platform in supported_platforms:
        if re.search(url_pattern + platform, url):
            return True
    
    # Agar URL pattern to'g'ri bo'lsa, yt-dlp o'zi tekshiradi
    # Oddiy URL pattern tekshirish
    return bool(re.match(url_pattern + r'.+\..+', url))


def detect_platform(url: str) -> str:
    """
    URLdan platformani aniqlash
    
    Returns:
        'youtube', 'instagram', 'tiktok', 'facebook', 'twitter', 'soundcloud', 'other'
    """
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower:
        return 'tiktok'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'facebook'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'soundcloud.com' in url_lower:
        return 'soundcloud'
    elif 'reddit.com' in url_lower:
        return 'reddit'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    elif 'twitch.tv' in url_lower:
        return 'twitch'
    else:
        return 'other'


def get_platform_emoji(platform: str) -> str:
    """
    Platforma uchun emoji qaytarish
    """
    emojis = {
        'youtube': '🎥',
        'instagram': '📸',
        'tiktok': '🎵',
        'facebook': '📘',
        'twitter': '🐦',
        'soundcloud': '🎧',
        'reddit': '🤖',
        'vimeo': '🎬',
        'twitch': '🎮',
        'other': '🌐'
    }
    return emojis.get(platform, '🌐')


def format_file_size(size_bytes: int) -> str:
    """
    Fayl hajmini formatlash (MB formatda)
    """
    size_mb = size_bytes / (1024 * 1024)
    return f"{size_mb:.2f}"


def get_file_size(filepath: str) -> int:
    """
    Fayl hajmini olish (baytlarda)
    """
    return os.path.getsize(filepath)


def cleanup_file(filepath: str) -> None:
    """
    Faylni o'chirish
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Fayl o'chirildi: {filepath}")
    except Exception as e:
        logger.error(f"Faylni o'chirishda xatolik: {e}")


def cleanup_directory(directory: str, keep_dir: bool = True) -> None:
    """
    Papkadagi barcha fayllarni o'chirish
    """
    try:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            
            if not keep_dir:
                os.rmdir(directory)
            
            logger.info(f"Papka tozalandi: {directory}")
    except Exception as e:
        logger.error(f"Papkani tozalashda xatolik: {e}")


def cleanup_user_directory(user_id: int, base_dir: str = None) -> None:
    """
    Foydalanuvchiga tegishli temp papkani tozalash
    """
    if base_dir is None:
        from config import DOWNLOAD_DIR
        base_dir = DOWNLOAD_DIR
    user_dir = os.path.join(base_dir, str(user_id))
    cleanup_directory(user_dir, keep_dir=False)


def ensure_directory(directory: str) -> None:
    """
    Papka mavjudligini ta'minlash
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """
    Fayl nomini tozalash (xavfsiz belgilar)
    """
    # Xavfli belgilarni olib tashlash
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Oxirgi va boshidagi bo'sh joylarni olib tashlash
    sanitized = sanitized.strip()
    # Agar fayl nomi bo'sh bo'lsa, default nom berish
    if not sanitized:
        sanitized = "media"
    return sanitized
