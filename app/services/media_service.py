import os
import yt_dlp
from typing import Dict, Any, Optional, List
from app.core.logging import logger
from app.core.config import settings

class MediaService:
    def __init__(self):
        self.base_opts = {
            'logger': logger,
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'socket_timeout': 30,
        }
        if settings.PROXY_POOL:
            import random
            self.base_opts['proxy'] = random.choice(settings.PROXY_POOL)

    def extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Enterprise-grade metadata extraction."""
        opts = {
            **self.base_opts,
            'extract_flat': 'in_playlist',
            'noplaylist': False, # Allow playlists if present in URL
        }
        # If it's a watch?v=...&list=... URL, force it to treat as playlist if possible
        if 'list=' in url and 'watch?v=' in url:
            opts['yesplaylist'] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return info
            except Exception as e:
                logger.error(f"SaaS Metadata extraction failed for {url}: {e}")
                return None

    def download(self, url: str, user_id: int, job_id: str, format_type: str = "mp3", quality: str = "best", progress_hook: Optional[callable] = None):
        """Download media with specific format and quality."""
        job_dir = settings.STORAGE_DIR / str(user_id) / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        opts = self.base_opts.copy()
        opts['outtmpl'] = str(job_dir / '%(title)s.%(ext)s')
        
        if format_type == "mp3":
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality if quality.isdigit() else '192',
            }]
        else:
            # Video format
            opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]' if quality.isdigit() else 'bestvideo+bestaudio/best'
            opts['merge_output_format'] = 'mp4'

        if progress_hook:
            opts['progress_hooks'] = [progress_hook]

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Handling post-processor extensions
                if format_type == "mp3":
                    filename = os.path.splitext(filename)[0] + '.mp3'
                elif 'mp4' in info.get('ext', ''):
                    filename = os.path.splitext(filename)[0] + '.mp4'
                
                return filename
            except Exception as e:
                logger.error(f"SaaS Download failed for {url}: {e}")
                return None

media_service = MediaService()
