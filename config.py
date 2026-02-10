"""
Bot konfiguratsiyasi va sozlamalar
"""
import os
from dotenv import load_dotenv

# .env fayldan environment variables yuklash
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Maksimal fayl hajmi (baytlarda)
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Yuklab olish papkasi (Hidden / Temporary)
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', '.temp_downloads')

# Parallel yuklab olish sozlamalari
MAX_PARALLEL_DOWNLOADS = int(os.getenv('MAX_PARALLEL_DOWNLOADS', 5))  # Bir vaqtda 5 ta video (tezroq!)

# Multi-user concurrency sozlamalari
MAX_DOWNLOADS_PER_USER = int(os.getenv('MAX_DOWNLOADS_PER_USER', 3))  # Har bir foydalanuvchi uchun max parallel download
GLOBAL_MAX_DOWNLOADS = int(os.getenv('GLOBAL_MAX_DOWNLOADS', 15))  # Server uchun jami max parallel download

# Audio platforms (MP3 yuklab olish)
AUDIO_PLATFORMS = ['youtube', 'soundcloud']

# yt-dlp AUDIO sozlamalari (MP3)
AUDIO_DLP_OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '128',  # 128kbps - tezlik va sifat balansi
    }],
    'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    # Parallel fragment yuklab olish (tezroq)
    'concurrent_fragment_downloads': 5,  # 4 dan 5 ga oshirildi
    # Buffer va cache tezlashtirishlari
    'http_chunk_size': 10485760,  # 10MB chunks (tezroq yuklab olish)
    'buffersize': 16384,  # 16KB buffer
    # FFmpeg uchun tezlikni oshirish
    'postprocessor_args': [
        '-threads', '4',
        '-preset', 'ultrafast',
        '-ab', '128k',  # Audio bitrate - aniq belgilash
    ],
}

# yt-dlp VIDEO sozlamalari (MP4)
VIDEO_DLP_OPTIONS = {
    'format': 'bestvideo+bestaudio/best',  # Universal format (yt-dlp handles selection)
    'merge_output_format': 'mp4',
    'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'concurrent_fragment_downloads': 5,
    'http_chunk_size': 10485760,
    'buffersize': 16384,
    'postprocessor_args': [
        '-threads', '4',
        '-preset', 'ultrafast',
    ],
}

# Backward compatibility
YT_DLP_OPTIONS = AUDIO_DLP_OPTIONS

# Bot xabarlari
MESSAGES = {
    'start': """
🎵 *Multi-Platform Media Downloader Bot*

Salom! Men turli platformalardan media yuklab olaman.

*Qo'llab-quvvatlanadigan platformalar:*
🎥 YouTube - Audio/Video
📸 Instagram - Video/Photo
🎵 TikTok - Video
📘 Facebook - Video
🐦 Twitter/X - Video
🎧 SoundCloud - Audio
🌐 Va 1000+ boshqa platformalar!

*Qanday foydalanish:*
Shunchaki media linkini yuboring!

🚀 Linkni yuboring!
""",
    'help': """
*Yordam*

Shunchaki YouTube, Instagram yoki TikTok linkini yuboring.
Bot avtomatik tarzda platformani aniqlaydi va yuklab beradi.

YouTube bitta video bo'lsa, sizdan Audio yoki Video holatda yuklashni so'raydi.

Eslatma: Telegram fayl limiti 50MB.
""",
    'checking': "🔍 Havola tekshirilyabdi...",
    'invalid_url': "❌ Noto'g'ri URL. Iltimos, to'g'ri media linkini yuboring.",
    'processing': "⏳ Qayta ishlanmoqda... Kuting.",
    'downloading': "📥 Yuklab olinmoqda...",
    'downloading_video': "🎬 Video yuklab olinmoqda...",
    'downloading_audio': "🎵 Audio yuklab olinmoqda...",
    'converting': "🔄 Qayta ishlanmoqda...",
    'success': "✅ Tayyor!",
    'error': "❌ Xatolik yuz berdi: {}",
    'file_too_large': "⚠️ Fayl juda katta (50MB dan yuqori). Telegram cheklovi tufayli yuborib bo'lmaydi.",
    'age_restricted': "🔞 Bu video yosh chekloviga ega yoki avtorizatsiya talab qiladi.",
    'not_available': "🚫 Bu media endi mavjud emas.",
    'copyright_error': "⚖️ Mualliflik huquqi tufayli yuklab bo'lmadi.",
    'download_failed': "📥 Yuklab olishda xatolik yuz berdi.",
    'conversion_failed': "🔄 Formatga o'tkazishda xatolik yuz berdi.",
    'platform_detected': "{emoji} *{platform}* platformasi aniqlandi!",
    'choose_format': "🎬 *YouTube* videosi aniqlandi.\n\nQaysi formatda yuklamoqchisiz?",
}
