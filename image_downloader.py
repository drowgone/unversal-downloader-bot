"""
Rasm yuklab olish moduli - Instagram, Pinterest va boshqalar
"""
import os
import requests
from typing import Optional, Tuple
from utils import logger, sanitize_filename, cleanup_file
from config import DOWNLOAD_DIR, MAX_FILE_SIZE_BYTES


def download_image(url: str, title: str = "image") -> Tuple[Optional[str], Optional[str]]:
    """
    Rasmni to'g'ridan yuklab olish
    
    Args:
        url: Rasm URL
        title: Rasm nomi
    
    Returns:
        (Fayl yo'li, xatolik kodi)
    """
    try:
        # User agent - ba'zi saytlar buni talab qiladi
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        logger.info(f"Rasm yuklab olinmoqda: {url}")
        
        # Rasm yuklab olish
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        logger.info(f"Image Request: GET {url} -> Status: {response.status_code}")
        response.raise_for_status()
        
        # Content type tekshirish
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type:
            logger.error(f"Bu rasm emas: {content_type}")
            return None, 'not_image'
        
        # Fayl kengaytmasini aniqlash
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = 'jpg'
        elif 'png' in content_type:
            ext = 'png'
        elif 'webp' in content_type:
            ext = 'webp'
        elif 'gif' in content_type:
            ext = 'gif'
        else:
            ext = 'jpg'  # Default
        
        # Fayl nomini tozalash
        safe_title = sanitize_filename(title)
        output_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.{ext}")
        
        # Agar fayl mavjud bo'lsa, o'chirish
        if os.path.exists(output_path):
            cleanup_file(output_path)
        
        # Rasmni saqlash
        total_size = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    # Fayl hajmini tekshirish (yuklab olish paytida)
                    if total_size > MAX_FILE_SIZE_BYTES:
                        logger.warning(f"Rasm juda katta: {total_size} bytes")
                        cleanup_file(output_path)
                        return None, 'file_too_large'
                    f.write(chunk)
        
        logger.info(f"Rasm muvaffaqiyatli yuklandi: {output_path} ({total_size} bytes)")
        return output_path, None
    
    except requests.exceptions.Timeout:
        logger.error("Rasm yuklab olishda timeout")
        return None, 'download_timeout'
    except requests.exceptions.RequestException as e:
        logger.error(f"Rasm yuklab olishda xatolik: {e}")
        return None, 'download_failed'
    except Exception as e:
        logger.error(f"Kutilmagan xatolik: {e}")
        return None, str(e)


def is_direct_image_url(url: str) -> bool:
    """
    To'g'ridan rasm URL ekanligini tekshirish
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
    url_lower = url.lower()
    return any(url_lower.endswith(ext) for ext in image_extensions)


def get_instagram_og_image(url: str) -> Optional[str]:
    """
    Instagram sahifasidan og:image meta tagini olish (Fallback)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        logger.info(f"Instagram OG extraction: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            import re
            # og:image URL ni qidirish
            match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', response.text)
            if match:
                return match.group(1).replace('&amp;', '&')
                
        return None
    except Exception as e:
        logger.error(f"Instagram OG extraction error: {e}")
        return None
