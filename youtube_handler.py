"""
Media (YouTube, Instagram, TikTok, etc) bilan ishlash uchun funksiyalar
"""
import os
import yt_dlp
import threading
from typing import List, Dict, Optional, Callable
from config import AUDIO_DLP_OPTIONS, VIDEO_DLP_OPTIONS, MAX_FILE_SIZE_BYTES, DOWNLOAD_DIR, AUDIO_PLATFORMS
from utils import logger, ensure_directory, get_file_size, sanitize_filename, cleanup_file, detect_platform


class YouTubeHandler:
    """Media yuklab olish va konvertatsiya qilish (YouTube, Instagram, TikTok, etc)"""
    
    def __init__(self):
        ensure_directory(DOWNLOAD_DIR)
    
    def _get_user_download_dir(self, user_id: Optional[int] = None) -> str:
        """Foydalanuvchiga tegishli download papkasini qaytarish"""
        if user_id:
            user_dir = os.path.join(DOWNLOAD_DIR, str(user_id))
            ensure_directory(user_dir)
            return user_dir
        return DOWNLOAD_DIR
    
    def get_playlist_info(self, url: str) -> Optional[Dict]:
        """
        Playlist yoki video haqida ma'lumot olish
        """
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True, # Faqat Instagram uchun False qilamiz pastroqda
                'no_warnings': True,
                'noplaylist': True if 'instagram.com/p/' in url else False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                }
            }
            
            # Instagram postlari uchun maxsus sozlama
            if 'instagram.com/p/' in url:
                ydl_opts['extract_flat'] = False
            
            logger.info(f"YDL: Ma'lumot olish boshlandi -> URL: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Agar bitta video/rasm bo'lsa
                if 'entries' not in info:
                    logger.info(f"YDL: Bitta media aniqlandi: {info.get('title')}")
                    
                    # Media turini aniqlash (photo yoki video)
                    media_type = 'video'
                    if info.get('ext') in ['jpg', 'jpeg', 'png', 'webp'] or not info.get('vcodec') or info.get('vcodec') == 'none':
                         if 'instagram.com' in url:
                             media_type = 'photo'
                             logger.info("YDL: Instagram rasm aniqlandi")
                    
                    # Sifatlarni aniqlash (faqat YouTube video uchun)
                    formats = []
                    if media_type == 'video' and ('youtube.com' in url or 'youtu.be' in url):
                        formats = self.get_available_formats(info)
                    
                    return {
                        'type': media_type,
                        'title': info.get('title', 'Unknown'),
                        'count': 1,
                        'videos': [{'title': info.get('title'), 'url': url}],
                        'formats': formats,
                        'id': info.get('id')
                    }
                
                # Instagram uchun maxsus fallback (bo'sh playlist muammosi)
                if 'instagram.com/p/' in url and 'entries' in info and len(info['entries']) == 0:
                    logger.info("YDL: Instagram bo'sh entries qaytardi. Fallback ishga tushirildi.")
                    
                    # 1. Thumbnail-dan foydalanish
                    photo_url = info.get('thumbnail') or info.get('url')
                    
                    # 2. Agar thumbnail bo'lmasa, og:image orqali qidirish
                    if not photo_url:
                        from image_downloader import get_instagram_og_image
                        photo_url = get_instagram_og_image(url)
                    
                    # 3. Agar hali ham yo'q bo'lsa, info ichidan boshqa havolalarni qidirish
                    if not photo_url and info.get('webpage_url'):
                        # Ba'zida webpage_url bitta rasm bo'lishi mumkin
                        if any(ext in info['webpage_url'].lower() for ext in ['.jpg', '.jpeg', '.png']):
                            photo_url = info['webpage_url']
                    
                    if photo_url:
                        logger.info(f"Fallback: Rasm havolasi topildi -> {photo_url[:50]}...")
                        return {
                            'type': 'photo',
                            'title': info.get('title', 'Instagram Photo'),
                            'count': 1,
                            'videos': [{'title': info.get('title', 'Instagram Photo'), 'url': photo_url}],
                            'formats': [],
                            'id': info.get('id')
                        }
                
                # Agar playlist bo'lsa
                videos = []
                logger.info(f"YDL: Playlist aniqlandi: {info.get('title')} (Videolar soni: {len(info.get('entries', []))})")
                for entry in info['entries']:
                    if entry:
                        videos.append({
                            'title': entry.get('title', 'Unknown'),
                            'url': entry.get('url') or entry.get('webpage_url') or f"https://youtube.com/watch?v={entry.get('id')}"
                        })
                
                return {
                    'type': 'playlist',
                    'title': info.get('title', 'Unknown Playlist'),
                    'count': len(videos),
                    'videos': videos
                }
        
        except Exception as e:
            logger.error(f"Playlist ma'lumotlarini olishda xatolik: {e}")
            return None

    def get_available_formats(self, info: Dict) -> List[Dict]:
        """
        Video uchun mavjud sifatlarni aniqlash
        """
        available_formats = []
        seen_heights = set()
        
        # Faqat video + audio birlashgan yoki video formatlarni ko'rib chiqamiz
        for f in info.get('formats', []):
            height = f.get('height')
            if height and height not in seen_heights and height >= 360:
                # Faqat asosiy sifatlarni olamiz: 360, 480, 720, 1080, 1440, 2160
                if height in [360, 480, 720, 1080, 1440, 2160]:
                    available_formats.append({
                        'height': height,
                        'format_id': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
                        'ext': f.get('ext', 'mp4')
                    })
                    seen_heights.add(height)
        
        # Sifatiga ko'ra saralash (o'suvchi)
        return sorted(available_formats, key=lambda x: x['height'])
    
    def download_and_convert(
        self, 
        url: str, 
        progress_callback: Optional[Callable] = None,
        download_video: bool = False,
        format_id: Optional[str] = None,
        max_size_bytes: Optional[int] = None,
        user_id: Optional[int] = None  # Per-user izolyatsiya
    ) -> (Optional[str], Optional[str]):
        """
        Media yuklab olish va kerakli formatga konvertatsiya qilish
        
        Args:
            url: Media URL
            progress_callback: Progress callback funksiyasi
            download_video: True - video yuklab olish (MP4), False - audio (MP3)
        
        Returns:
            (Fayl yo'li, xatolik kodi/xabari)
        """
        try:
            # 0. Agar bu rasm bo'lsa (direct image link)
            from image_downloader import is_direct_image_url, download_image
            if is_direct_image_url(url) or "scontent" in url: # scontent - instagram rasmlari uchun
                logger.info(f"Direct Image aniqlandi: {url[:50]}...")
                return download_image(url, sanitize_filename(url[:20]))

            # Progress hook
            def progress_hook(d):
                if d['status'] == 'downloading' and progress_callback:
                    progress_callback('downloading', d)
                elif d['status'] == 'finished' and progress_callback:
                    progress_callback('converting', d)
            
            # Video yoki Audio sozlamalarini tanlash
            if download_video:
                ydl_opts = VIDEO_DLP_OPTIONS.copy()
                if format_id:
                    ydl_opts['format'] = format_id
                file_extension = 'mp4'
            else:
                ydl_opts = AUDIO_DLP_OPTIONS.copy()
                file_extension = 'mp3'
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # Video ma'lumotlarini olish
            try:
                with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    media_title = info.get('title', 'media')
            except yt_dlp.utils.DownloadError as e:
                msg = str(e).lower()
                if 'age restricted' in msg or 'sign in' in msg:
                    return None, 'age_restricted'
                if 'not available' in msg or 'deleted' in msg:
                    return None, 'not_available'
                if 'copyright' in msg:
                    return None, 'copyright_error'
                return None, 'download_failed'
            
            # Per-user download directory
            download_dir = self._get_user_download_dir(user_id)
            
            # Fayl nomini tozalash
            safe_title = sanitize_filename(media_title)
            output_path = os.path.join(download_dir, f"{safe_title}.{file_extension}")
            
            # Agar fayl allaqachon mavjud bo'lsa, o'chirish
            if os.path.exists(output_path):
                cleanup_file(output_path)
            
            # Yuklab olish va konvertatsiya qilish
            ydl_opts['outtmpl'] = os.path.join(download_dir, f"{safe_title}.%(ext)s")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Fayl tekshirish
            if not os.path.exists(output_path):
                logger.error(f"Fayl topilmadi: {output_path}")
                return None, 'conversion_failed'
            
            # Fayl hajmini tekshirish (agar cheklov berilgan bo'lsa)
            if max_size_bytes:
                file_size = get_file_size(output_path)
                if file_size > max_size_bytes:
                    logger.warning(f"Fayl juda katta: {file_size} bytes (Limit: {max_size_bytes})")
                    cleanup_file(output_path)
                    return None, 'file_too_large'
            
            logger.info(f"Muvaffaqiyatli yuklab olindi: {output_path}")
            return output_path, None
        except Exception as e:
            logger.error(f"Yuklab olishda kutilmagan xatolik: {e}")
            return None, str(e)
    
    def download_playlist(
        self,
        url: str,
        progress_callback: Optional[Callable] = None,
        download_video: bool = False,
        user_id: Optional[int] = None
    ) -> List[str]:
        """
        Playlist'dagi barcha medialarni yuklab olish
        
        Returns:
            Faylllar ro'yxati
        """
        downloaded_files = []
        
        try:
            # Playlist ma'lumotlarini olish
            playlist_info = self.get_playlist_info(url)
            
            if not playlist_info or not playlist_info['videos']:
                logger.error("Playlist bo'sh yoki topilmadi")
                return downloaded_files
            
            total_videos = len(playlist_info['videos'])
            logger.info(f"Jami {total_videos} ta media topildi")
            
            # Har bir videoni yuklab olish
            for index, video in enumerate(playlist_info['videos'], 1):
                video_url = video['url']
                video_title = video['title']
                
                logger.info(f"[{index}/{total_videos}] Yuklab olinmoqda: {video_title}")
                
                if progress_callback:
                    progress_callback('video_start', {
                        'index': index,
                        'total': total_videos,
                        'title': video_title
                    })
                
                # Yuklab olish
                file_path, error_msg = self.download_and_convert(
                    video_url, 
                    progress_callback, 
                    download_video=download_video,
                    user_id=user_id
                )
                
                if file_path:
                    downloaded_files.append(file_path)
                    logger.info(f"✓ Tayyor: {video_title}")
                else:
                    logger.warning(f"✗ Yuklab olinmadi: {video_title}. Xatolik: {error_msg}")
            
            logger.info(f"Jami yuklab olindi: {len(downloaded_files)}/{total_videos}")
            return downloaded_files
        
        except Exception as e:
            logger.error(f"Playlist yuklab olishda xatolik: {e}")
            return downloaded_files
