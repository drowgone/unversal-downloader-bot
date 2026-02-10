# 🎵 Advanced Multi-Platform Media Downloader Bot

Bu bot YouTube, Instagram, TikTok va boshqa 1000+ platformalardan media fayllarni (Video/Audio/Photo) yuqori tezlikda yuklab olish va Telegram orqali yuborish uchun mo'ljallangan.

## ✨ Asosiy Imkoniyatlar

- **🚀 Parallel Yuklab Olish**: Playlist'dagi videolarni bir vaqtning o'zida bir nechta worker'lar yordamida yuklaydi.
- **👥 Multi-User Support**: Bir vaqtning o'zida o'nlab foydalanuvchilar botdan foydalanishi mumkin. Har bir foydalanuvchi uchun alohida navbat va papka izolyatsiyasi mavjud.
- **📱 Ko'p Platformali**:
  - **YouTube**: Bitta video yoki butun playlist. MP3 (Audio) yoki MP4 (Video) tanlash imkoniyati.
  - **Instagram**: Video (Reels), Rasm va Karusel (multiple photos) postlarini yuklab olish.
  - **TikTok**: Suv belgisiz (no watermark) videolarni yuklash.
  - **Va boshqalar**: Facebook, Twitter, SoundCloud va boshqa 1000+ saytlar.
- **📦 Katta Fayllar Bilan Ishlash**:
  - 50MB dan katta fayllar avtomatik ravishda **Document** sifatida yuboriladi (Telegram Bot API limiti sababli).
  - Timeout xatoliklarini oldini olish uchun 10 daqiqalik (600s) yuborish vaqti o'rnatilgan.
- **📂 Per-User Isolation**: Har bir foydalanuvchi fayllari alohida `.temp_downloads/{user_id}/` papkasida saqlanadi, bu xavfsizlik va tartibni ta'minlaydi.
- **⏳ Navbat Tizimi (Queue)**: Server resurslarini himoya qilish uchun global (15) va per-user (3) parallel yuklash cheklovlari (Semaphore) mavjud.

## 🚀 O'rnatish

### 1. Repozitoriyani clone qiling

```bash
git clone https://github.com/drowgone/unversal-dowonloader.git
cd unversal-dowonloader
```

### 2. Virtual environment yarating

```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# yoki
venv\Scripts\activate  # Windows
```

### 3. Dependencies o'rnating

```bash
pip install -r requirements.txt
```

### 4. FFmpeg o'rnating (Audio konvertatsiya uchun zarur)

**Ubuntu/Debian:** `sudo apt install ffmpeg`  
**MacOS:** `brew install ffmpeg`  
**Windows:** https://ffmpeg.org/download.html dan yuklab olib PATH'ga qo'shing.

### 5. Environment sozlash

`.env` faylini yarating va quyidagilarni to'ldiring:

```env
TELEGRAM_BOT_TOKEN=sizning_bot_tokeningiz
MAX_FILE_SIZE_MB=50
MAX_PARALLEL_DOWNLOADS=5
MAX_DOWNLOADS_PER_USER=3
GLOBAL_MAX_DOWNLOADS=15
DOWNLOAD_DIR=.temp_downloads
```

## 🎮 Ishlatish

### Botni ishga tushirish

```bash
python bot.py
```

### Qanday foydalaniladi?

1. Botga istalgan media linkini yuboring.
2. Bot avtomatik ravishda platformani aniqlaydi.
3. YouTube bo'lsa, sizdan formatni (Video yoki MP3) tanlashni so'raydi.
4. Yuklash va yuborish jarayoni boshlanadi.

## 📁 Loyiha Strukturasi

- `bot.py`: Asosiy bot logikasi va Telegram handlerlar.
- `youtube_handler.py`: yt-dlp interfeysi, Instagram fallback va meta-ma'lumotlar.
- `parallel_downloader.py`: Asinxron parallel yuklash mexanizmi.
- `image_downloader.py`: To'g'ridan-to'g'ri rasm va Instagram OG extraction.
- `utils.py`: Loglar, fayllarni tozalash va sanitizatsiya.
- `config.py`: Markaziy sozlamalar va limitlar.

## 📝 Texnik Eslatmalar

- **Fayl Hajmi**: Playlist yuklashda 50MB limiti mavjud. Bitta videoda cheklov yo'q, lekin 50MB dan oshsa Document bo'lib boradi.
- **Instagram Fallback**: Instagram scrapingni bloklagan holatda bot OG:image va boshqa extraction usullaridan foydalanadi.
- **Tozalash**: Yuklash va yuborish tugagach, vaqtincha fayllar darhol o'chiriladi.

---

**Muallif**: Donegrow  
**AI Yordamchi**: Antigravity AI  
**Versiya**: 2.0.0 (Parallel & Multi-user)
