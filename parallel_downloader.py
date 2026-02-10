"""
Media fayllarni parallel yuklab olish moduli
"""
import asyncio
from typing import List, Dict, Optional, Callable
from utils import logger

class ParallelDownloader:
    """Bir vaqtning o'zida bir nechta fayllarni yuklab olish uchun klass"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
    
    async def download_multiple(
        self,
        youtube_handler,
        videos: List[Dict],
        progress_callback: Optional[Callable] = None,
        download_video: bool = False,
        format_id: Optional[str] = None,
        max_size_bytes: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        """Video/Audiolarni parallel yuklab olish va tayyor bo'lishi bilan qaytarish (Generator)"""
        
        # Semaphore'ni joriy event loop'da yaratamiz
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def download_single(index, video):
            title = video.get('title', 'Unknown')
            url = video.get('url')
            
            async with semaphore:
                # Progress callback orqali holatni bildirish
                if progress_callback:
                    await progress_callback(index, len(videos), title, 'downloading')
                
                # youtube_handler async emas, shuning uchun run_in_executor ishlatamiz
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.get_event_loop()

                file_path, error_code = await loop.run_in_executor(
                    None, 
                    lambda: youtube_handler.download_and_convert(
                        url, 
                        None,
                        download_video=download_video,
                        format_id=format_id,
                        max_size_bytes=max_size_bytes,
                        user_id=user_id
                    )
                )
                
                if progress_callback:
                    status = 'success' if file_path else 'error'
                    await progress_callback(index, len(videos), title, status)
                
                return (file_path, error_code, title)

        # Barcha medialarni parallel yuklab olish uchun task'larni yaratamiz
        tasks = [
            asyncio.create_task(download_single(index, video))
            for index, video in enumerate(videos, 1)
        ]
        
        logger.info(f"Parallel Downloader: {len(tasks)} ta vazifa boshlandi (Workers: {self.max_workers})")
        
        try:
            # Tayyor bo'lishi bilan qaytarish
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    yield result
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Task bajarishda xato: {e}")
        finally:
            # Agar generator yopilsa (masalan, Break yoki Error), qolgan task'larni bekor qilamiz
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Task'lar tugashini kutamiz (optional but safer)
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
