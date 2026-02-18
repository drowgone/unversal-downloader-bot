import os
import yt_dlp
from typing import Dict, Any, Optional, List
from app.core.logging import logger
from app.core.config import settings
from pathlib import Path
import time

class InstagramService:
    def __init__(self):
        import random
        self.user_agent = random.choice(settings.USER_AGENT_LIST)
        self.base_opts = {
            'format': 'best', # Simpler format for IG/TikTok often works better
            'merge_output_format': 'mp4',
            'logger': logger,
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'outtmpl': f'{settings.STORAGE_DIR}/%(user_id)s/%(job_id)s/instagram/%(title)s.%(ext)s',
            'socket_timeout': 30,
            'user_agent': self.user_agent,
            'http_headers': {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Mode': 'navigate',
            }
        }
        if settings.INSTAGRAM_COOKIES_PATH and settings.INSTAGRAM_COOKIES_PATH.exists():
            self.base_opts['cookiefile'] = str(settings.INSTAGRAM_COOKIES_PATH)
            logger.info(f"Using Instagram cookies from {settings.INSTAGRAM_COOKIES_PATH}")

    async def _resolve_tiktok_redirect(self, url: str) -> str:
        """Resolve vt.tiktok.com and ensure it uses /video/ or /photo/ reliably."""
        if "tiktok.com" not in url:
            return url
            
        import httpx
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                resp = await client.head(url, headers={'User-Agent': self.user_agent})
                final_url = str(resp.url)
                # Force /video/ for photo posts if extracted as such
                final_url = final_url.replace("/photo/", "/video/")
                return final_url.split('?')[0]
        except Exception as e:
            logger.warning(f"TikTok redirect resolution failed for {url}: {e}")
            # Fallback to simple string replacement
            return url.replace("/photo/", "/video/").split('?')[0]

    def _normalize_url(self, url: str) -> str:
        """Fix problematic URLs for extractors."""
        if "tiktok.com" in url:
            # Replace /photo/ with /video/ to force extractor matching
            url = url.replace("/photo/", "/video/")
            return url.split('?')[0]
        return url

    async def _manual_instagram_photo_download(self, url: str, job_dir: Path) -> List[str]:
        """Fallback to manual scraping if yt-dlp fails to find video."""
        import httpx
        import re
        import json
        from pathlib import Path
        
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
            }
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                
                html = resp.text
                downloaded_paths = []
                
                # Try 1: og:image
                img_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
                if img_match:
                    img_url = img_match.group(1).replace('&amp;', '&')
                    img_name = f"instagram_photo_og_{int(time.time())}.jpg"
                    img_path = job_dir / img_name
                    
                    try:
                        img_resp = await client.get(img_url)
                        if img_resp.status_code == 200:
                            with open(img_path, 'wb') as f:
                                f.write(img_resp.content)
                            downloaded_paths.append(str(img_path))
                    except: pass
                
                # Try 2: JSON in script tags (search for display_url)
                if not downloaded_paths:
                    script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
                    for script in script_matches:
                        if 'display_url' in script:
                            # Search for all "display_url":"..."
                            urls = re.findall(r'"display_url"\s*:\s*"([^"]+)"', script)
                            for i, d_url in enumerate(urls):
                                try:
                                    d_url = d_url.encode().decode('unicode-escape').replace('\\/', '/')
                                    img_path = job_dir / f"instagram_photo_json_{i}_{int(time.time())}.jpg"
                                    img_resp = await client.get(d_url)
                                    if img_resp.status_code == 200:
                                        with open(img_path, 'wb') as f:
                                            f.write(img_resp.content)
                                        downloaded_paths.append(str(img_path))
                                        if len(downloaded_paths) >= 10: break # Limit
                                except: continue
                            if downloaded_paths: break

                return downloaded_paths
        except Exception as e:
            logger.error(f"Manual Instagram scrape failed: {e}")
            return []

    async def _manual_tiktok_photo_download(self, url: str, job_dir: Path) -> List[str]:
        """Scrape TikTok HTML for all images in a slideshow."""
        import httpx
        import json
        import re
        
        try:
            async with httpx.AsyncClient(headers={'User-Agent': self.user_agent}, follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                
                # Check for SIGI_STATE or __INITIAL_PROPS__
                html = resp.text
                match = re.search(r'<script id="SIGI_STATE" type="application/json">(.*?)</script>', html)
                if not match:
                    match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', html)
                
                if not match:
                    return []
                
                data = json.loads(match.group(1))
                # TikTok's JSON structure is complex and changes. 
                # We try to find any URLs that look like image URLs in the ItemModule or similar.
                image_urls = []
                
                # Search recursively for image objects
                def find_images(obj):
                    if isinstance(obj, dict):
                        # Look for common TikTok image keys
                        if 'imageURL' in obj and isinstance(obj['imageURL'], dict) and 'urlList' in obj['imageURL']:
                            for u in obj['imageURL']['urlList']:
                                if 'webp' not in u.lower(): # Prefer jpeg
                                    image_urls.append(u)
                                    break
                        elif 'display_image' in obj and 'url' in obj['display_image']:
                            image_urls.append(obj['display_image']['url'])
                        elif 'download_url' in obj and any(x in obj['download_url'].lower() for x in ['.jpg', '.jpeg', '.png']):
                            image_urls.append(obj['download_url'])
                        elif 'image_url' in obj:
                             image_urls.append(obj['image_url'])
                        
                        # Recurse
                        for v in obj.values():
                            find_images(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_images(item)

                find_images(data)
                
                # Deduplicate and download
                downloaded = []
                unique_urls = list(set(image_urls))
                for i, img_url in enumerate(unique_urls):
                    try:
                        img_resp = await client.get(img_url)
                        if img_resp.status_code == 200:
                            ext = 'jpg' if 'jpeg' in img_url.lower() or 'jpg' in img_url.lower() else 'png'
                            img_path = job_dir / f"tiktok_photo_{i}.{ext}"
                            with open(img_path, 'wb') as f:
                                f.write(img_resp.content)
                            downloaded.append(str(img_path))
                    except: continue
                return downloaded
        except Exception as e:
            logger.error(f"Manual TikTok scrape failed: {e}")
            return []

    async def extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract info from URL with robust headers and impersonation."""
        if "tiktok.com" in url:
            url = await self._resolve_tiktok_redirect(url)
        # Note: We don't normalize stories as much to keep query params if needed
        elif "stories" not in url:
            url = self._normalize_url(url)
            
        opts = {
            'extract_flat': False,
            'quiet': True,
            'no_warnings': True,
            'user_agent': self.user_agent,
            'http_headers': self.base_opts['http_headers'].copy(),
        }
        
        opts['ignoreerrors'] = True 

        if 'cookiefile' in self.base_opts:
            opts['cookiefile'] = self.base_opts['cookiefile']

        if "instagram.com" in url:
            opts['http_headers']['Referer'] = 'https://www.google.com/'
            opts['http_headers']['Origin'] = 'https://www.instagram.com'
        elif "tiktok.com" in url:
            opts['http_headers']['Referer'] = 'https://www.tiktok.com/'

        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(None, ydl.extract_info, url, False)
                return info
        except Exception as e:
            # If it's the "No video" error, we return a dummy info for photos
            if "no video" in str(e).lower() and "instagram.com" in url:
                return {"title": "Instagram Photo", "url": url, "_type": "url", "id": "photo"}
            raise e

    def is_video(self, info: Dict[str, Any]) -> bool:
        """Check if info contains any actual video content."""
        if not info: return False
        if info.get('id') == 'photo': return False

        def _has_video(item: Dict[str, Any]) -> bool:
            vcodec = item.get('vcodec')
            if vcodec and vcodec.lower() != 'none':
                return True
            duration = item.get('duration')
            if duration and duration > 0:
                return True
            return False

        if info.get('_type') == 'playlist' or 'entries' in info:
            for entry in info.get('entries', []):
                if entry and _has_video(entry):
                    return True
            return False
        return _has_video(info)

    async def download_media(self, url: str, user_id: int, job_id: str, progress_hook: Optional[callable] = None) -> List[str]:
        """Download media (handles single, carousel, or stories)."""
        original_url = url
        if "tiktok.com" in url:
            url = await self._resolve_tiktok_redirect(url)
        elif "stories" not in url:
            url = self._normalize_url(url)
            
        job_dir = settings.STORAGE_DIR / str(user_id) / job_id / "instagram"
        job_dir.mkdir(parents=True, exist_ok=True)

        opts = self.base_opts.copy()
        opts['outtmpl'] = str(job_dir / '%(title)s_%(id)s.%(ext)s')
        
        if "tiktok.com" in url:
            opts['format'] = 'bestvideo+bestaudio/best'
        else:
            opts['format'] = 'best'
            
        opts['merge_output_format'] = 'mp4'
        opts['ignoreerrors'] = True
        
        if "instagram.com" in url:
            opts['http_headers']['Referer'] = 'https://www.google.com/'
            opts['http_headers']['Origin'] = 'https://www.instagram.com'
        elif "tiktok.com" in url:
            opts['http_headers']['Referer'] = 'https://www.tiktok.com/'

        downloaded_files = set()

        def internal_progress_hook(d):
            if d['status'] == 'finished':
                fn = d.get('filename')
                if fn and os.path.exists(fn):
                    downloaded_files.add(fn)
            if progress_hook:
                progress_hook(d)

        opts['progress_hooks'] = [internal_progress_hook]

        import asyncio
        loop = asyncio.get_event_loop()
        
        try:
            # 1. Try yt-dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                await loop.run_in_executor(None, ydl.download, [url])
        except Exception as e:
            logger.warning(f"yt-dlp download failed: {e}")

        # 2. Check and Fallback
        # Only photos/audio found?
        has_video = any(f.endswith('.mp4') or f.endswith('.mkv') or f.endswith('.webm') for f in downloaded_files)
        
        # Fallback 1: Manual scrape for TikTok photos (if user wants photos only or if yt-dlp failed)
        if "tiktok.com" in url and not has_video:
            # For TikTok photo posts, yt-dlp often only gets audio. 
            # We explicitly fetch images even if we have 'something' (the audio).
            manual_files = await self._manual_tiktok_photo_download(url, job_dir)
            if manual_files:
                # If we got photos, the user said they don't want the mp3
                for f in list(downloaded_files):
                    if f.endswith('.mp3'):
                        try: os.remove(f)
                        except: pass
                        downloaded_files.remove(f)
                downloaded_files.update(manual_files)

        # Fallback 2: Manual scrape for Instagram photos
        if not downloaded_files and "instagram.com" in url:
            manual_files = await self._manual_instagram_photo_download(url, job_dir)
            downloaded_files.update(manual_files)
                
        # Fallback 3: Direct disk scan
        if not downloaded_files:
            for f in os.listdir(job_dir):
                f_path = job_dir / f
                if f_path.is_file():
                    downloaded_files.add(str(f_path))
                    
        return list(downloaded_files)

instagram_service = InstagramService()
