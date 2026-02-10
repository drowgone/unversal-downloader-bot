"""
YouTube MP3 Telegram Bot - Parallel Version
"""
import os
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode, ChatAction

from config import BOT_TOKEN, MESSAGES, MAX_FILE_SIZE_MB, MAX_PARALLEL_DOWNLOADS, AUDIO_PLATFORMS, MAX_DOWNLOADS_PER_USER, GLOBAL_MAX_DOWNLOADS
from youtube_handler import YouTubeHandler
from parallel_downloader import ParallelDownloader
from image_downloader import download_image, is_direct_image_url
from utils import (
    logger,
    is_valid_youtube_url,
    is_valid_media_url,
    detect_platform,
    get_platform_emoji,
    format_file_size,
    get_file_size,
    cleanup_file,
    cleanup_directory
)


class TelegramBot:
    """Telegram Bot asosiy klassi"""
    
    def __init__(self):
        if not BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN topilmadi! .env faylni tekshiring.")
        
        self.youtube_handler = YouTubeHandler()
        self.parallel_downloader = ParallelDownloader(max_workers=MAX_PARALLEL_DOWNLOADS)
        
        # Multi-user concurrency control
        self._global_semaphore = asyncio.Semaphore(GLOBAL_MAX_DOWNLOADS)
        self._user_semaphores: dict[int, asyncio.Semaphore] = {}
        self._user_active_tasks: dict[int, int] = {}
        
        # Timeoutlarni sezilarli darajada oshirish (600 soniya = 10 daqiqa)
        self.app = Application.builder() \
            .token(BOT_TOKEN) \
            .read_timeout(600) \
            .write_timeout(600) \
            .connect_timeout(600) \
            .pool_timeout(600) \
            .build()
        
        # Handlerlarni qo'shish
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler qo'shish
        self.app.add_error_handler(self.error_handler)
    
    def _get_user_semaphore(self, user_id: int) -> asyncio.Semaphore:
        """Foydalanuvchi uchun semaphore olish (lazy init)"""
        if user_id not in self._user_semaphores:
            self._user_semaphores[user_id] = asyncio.Semaphore(MAX_DOWNLOADS_PER_USER)
        return self._user_semaphores[user_id]
    
    def _track_user_task(self, user_id: int, delta: int):
        """Foydalanuvchining faol task'larini kuzatish"""
        self._user_active_tasks[user_id] = self._user_active_tasks.get(user_id, 0) + delta
        if self._user_active_tasks[user_id] <= 0:
            self._user_active_tasks.pop(user_id, None)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Kutilmagan xatoliklarni qayta ishlash"""
        logger.error(f"Update {update} xatolikka sabab bo'ldi: {context.error}")
        # Foydalanuvchiga xabar yuborishga harakat qilamiz (agar iloji bo'lsa)
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text("⚠️ Kutilmagan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            except: pass
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start command handler"""
        message = MESSAGES['start']
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help command handler"""
        await update.message.reply_text(MESSAGES['help'], parse_mode=ParseMode.MARKDOWN)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xabarlarni qayta ishlash - Bir nechta URLlarni parallel ishlash"""
        text = update.message.text
        user = update.effective_user
        
        # URLlarni ajratib olish
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        
        if not urls:
            logger.warning(f"URL topilmadi: {text} (User: {user.id})")
            return

        logger.info(f"Yangi xabar: User {user.id} (@{user.username}) -> {len(urls)} ta URL aniqlandi")
        
        # Har bir URL uchun alohida parallel task ishga tushiramiz
        for url in urls:
            asyncio.create_task(self.handle_single_url(update, context, url))

    async def handle_single_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        """Bitta URLni boshidan oxirigacha qayta ishlash"""
        user_id = update.effective_user.id
        
        if not is_valid_media_url(url):
            logger.warning(f"Noto'g'ri URL: {url} (User: {user_id})")
            # Har bir xato uchun alohida xabar yubormaslik uchun (spam bo'lmasligi uchun) 
            # faqat bitta bo'lsa javob beramiz
            return
        
        # 1. Havolani tekshirish bosqichi
        check_msg = await update.message.reply_text(MESSAGES['checking'])
        
        # Kichik pauza (UX uchun)
        await asyncio.sleep(0.5)
        
        platform = detect_platform(url)
        platform_emoji = get_platform_emoji(platform)
        
        # Platformani aniqlash va bildirish
        await check_msg.edit_text(
            f"{MESSAGES['checking']}\n\n{MESSAGES['platform_detected'].format(emoji=platform_emoji, platform=platform.capitalize())}",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Rasm tekshirish
            if is_direct_image_url(url):
                await check_msg.edit_text("📸 Rasm yuklab olinmoqda...")
                file_path, error_code = download_image(url, f"image_{user_id}")
                if file_path:
                    with open(file_path, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            read_timeout=600,
                            write_timeout=600
                        )
                    cleanup_file(file_path)
                    await check_msg.delete()
                else:
                    await check_msg.edit_text(MESSAGES.get(error_code, MESSAGES['error'].format(error_code)))
                return

            # YouTube bitta video bo'lsa sifat tanlash
            if platform == 'youtube':
                info = self.youtube_handler.get_playlist_info(url)
                if info and info['type'] == 'video' and info['count'] == 1:
                    # Sifat tugmalari (64 byte limitni hisobga olgan holda faqat ID va Sifat yuboramiz)
                    video_id = info.get('id')
                    if not video_id:
                         # Agar ID bo'lmasa (kamdan-kam) URLdan foydalanishga majburmiz, lekin qisqartirib
                         video_id = url
                    
                    keyboard = []
                    formats = info.get('formats', [])
                    
                    # Audio tugmasi
                    row = [InlineKeyboardButton("🎵 MP3", callback_data=f"au|{video_id}")]
                    
                    # Video sifatlari
                    for fmt in formats:
                        height = fmt['height']
                        # callback_data: q|sifat|video_id
                        row.append(InlineKeyboardButton(f"🎬 {height}p", callback_data=f"q|{height}|{video_id}"))
                        if len(row) >= 2:
                            keyboard.append(row)
                            row = []
                    if row: keyboard.append(row)
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await check_msg.edit_text(MESSAGES['choose_format'], reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                    return
                elif info and info['type'] == 'playlist':
                    # Playlist bo'lsa darhol yuklash (audio)
                    await self.process_download(check_msg, update, context, url, platform, is_playlist=True)
                    return
            
            # Boshqa platformalar (Instagram, TikTok, etc) - darhol yuklash (video)
            await self.process_download(check_msg, update, context, url, platform, is_playlist=False)

        except Exception as e:
            logger.error(f"Xatolik ({url}): {e}")
            await check_msg.edit_text(MESSAGES['error'].format(str(e)))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tugmalarni bosishni qayta ishlash"""
        query = update.callback_query
        await query.answer()
        
        data = query.data.split('|')
        mode = data[0] # au or q
        user_id = query.from_user.id
        
        if mode == 'q':
            # Dinamik video sifat tanlangan
            height = data[1]
            video_id = data[2]
            
            # URLni tiklash
            url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
            # Formatni tiklash
            format_id = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            
            logger.info(f"Sifat tanlandi: User {user_id} -> Height: {height}, URL: {url}")
            await query.edit_message_text(MESSAGES['downloading_video'])
            await self.process_download(query.message, update, context, url, 'youtube', is_playlist=False, force_audio=False, format_id=format_id)
        
        elif mode == 'au':
            # Audio (MP3) tanlangan
            video_id = data[1]
            url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
            
            logger.info(f"Audio tanlandi: User {user_id} -> URL: {url}")
            await query.edit_message_text(MESSAGES['downloading_audio'])
            await self.process_download(query.message, update, context, url, 'youtube', is_playlist=False, force_audio=True)
        
        else:
            logger.error(f"Noma'lum callback mode: {mode}")

    async def process_download(self, status_msg, update, context, url, platform, is_playlist=False, force_audio=None, format_id=None):
        """Yuklash jarayonini boshqarish (multi-user safe)"""
        user_id = update.effective_user.id
        user_semaphore = self._get_user_semaphore(user_id)
        is_audio_platform = (platform in AUDIO_PLATFORMS) if force_audio is None else force_audio
        
        # Fayl hajmi cheklovi: Playlist bo'lsa 50MB, bitta bo'lsa cheklovsiz (None)
        from config import MAX_FILE_SIZE_BYTES
        max_size_limit = MAX_FILE_SIZE_BYTES if is_playlist else None
        
        # Agar semaphore band bo'lsa, navbat xabarini ko'rsatish
        if user_semaphore.locked():
            active_count = self._user_active_tasks.get(user_id, 0)
            await status_msg.edit_text(
                f"⏳ Navbatda kutmoqdasiz...\n"
                f"📊 Sizda hozir {active_count} ta yuklanish jarayonda.\n"
                f"🔄 Navbat bo'shaganda avtomatik boshlanadi."
            )
        
        # Per-user va global semaphore'larni birlashtirish
        async with user_semaphore:
            async with self._global_semaphore:
                self._track_user_task(user_id, 1)
                logger.info(f"[User {user_id}] Yuklanish boshlandi. Faol: {self._user_active_tasks.get(user_id, 0)} | Global: {GLOBAL_MAX_DOWNLOADS - self._global_semaphore._value}/{GLOBAL_MAX_DOWNLOADS}")
                try:
                    await self._do_download(status_msg, update, context, url, platform, is_playlist, is_audio_platform, max_size_limit, format_id, user_id)
                finally:
                    self._track_user_task(user_id, -1)
                    logger.info(f"[User {user_id}] Yuklanish tugadi. Faol: {self._user_active_tasks.get(user_id, 0)}")
    
    async def _do_download(self, status_msg, update, context, url, platform, is_playlist, is_audio_platform, max_size_limit, format_id, user_id):
        """Haqiqiy yuklash jarayoni (semaphore ichida chaqiriladi)"""
        
        try:
            playlist_info = self.youtube_handler.get_playlist_info(url)
            if not playlist_info:
                await status_msg.edit_text(MESSAGES['not_available'])
                return
            
            video_count = playlist_info['count']
            playlist_title = playlist_info['title']
            
            # Media turini aniqlash
            media_type_code = playlist_info.get('type', 'video')
            
            if media_type_code == 'photo':
                media_label = "rasm"
            else:
                media_label = "audio" if is_audio_platform else "video"
            
            if is_playlist:
                await status_msg.edit_text(
                    f"📂 *Playlist:* {playlist_title}\nJami: {video_count} ta {media_label}\n🚀 Yuklash boshlandi...",
                    parse_mode=ParseMode.MARKDOWN
                )

            async def progress_callback(index, total, title, status):
                # Parallel workerlardan kelayotgan progress xabarini o'chirib turamiz 
                # (chunki u success_count bilan ziddiyatga kelyapti)
                pass

            # Natijalarni asinxron generator orqali bittalab olish
            success_count = 0
            async for result in self.parallel_downloader.download_multiple(
                self.youtube_handler,
                playlist_info['videos'],
                progress_callback,
                download_video=not is_audio_platform,
                format_id=format_id,
                max_size_bytes=max_size_limit,
                user_id=user_id
            ):
                file_path, error_code, video_title = result
                
                if not file_path:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"❌ {video_title[:30]}: {MESSAGES.get(error_code, error_code)}"
                    )
                    continue

                try:
                    # Yuborishda Retry mexanizmi
                    max_retries = 3
                    sent_successfully = False
                    
                    for attempt in range(1, max_retries + 1):
                        try:
                            logger.info(f"📤 Yuborish boshlandi (Urinish {attempt}/{max_retries}): {video_title[:50]}...")
                            
                            if media_type_code == 'photo':
                                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
                                with open(file_path, 'rb') as f:
                                    await context.bot.send_photo(
                                        chat_id=update.effective_chat.id,
                                        photo=f,
                                        caption=video_title[:1024],
                                        read_timeout=600,
                                        write_timeout=600
                                    )
                            else:
                                action = ChatAction.UPLOAD_VIDEO if not is_audio_platform else ChatAction.UPLOAD_VOICE
                                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=action)
                                
                                file_size = get_file_size(file_path)
                                file_size_mb = file_size / (1024 * 1024)
                                logger.info(f"💾 Fayl hajmi: {format_file_size(file_size)} MB")

                                try:
                                    with open(file_path, 'rb') as f:
                                        if is_audio_platform:
                                            await context.bot.send_audio(
                                                chat_id=update.effective_chat.id,
                                                audio=f,
                                                title=video_title,
                                                filename=f"{video_title}.mp3",
                                                read_timeout=600,
                                                write_timeout=600
                                            )
                                        else:
                                            await context.bot.send_video(
                                                chat_id=update.effective_chat.id,
                                                video=f,
                                                caption=video_title[:1024],
                                                read_timeout=600,
                                                write_timeout=600
                                            )
                                except Exception as send_err:
                                    # Video/Audio sifatida yuborib bo'lmasa, document sifatida yuboramiz
                                    logger.warning(f"⚠️ Video/Audio yuborib bo'lmadi ({file_size_mb:.1f}MB), document sifatida yuborilmoqda...")
                                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                                    with open(file_path, 'rb') as f:
                                        await context.bot.send_document(
                                            chat_id=update.effective_chat.id,
                                            document=f,
                                            caption=f"📎 {video_title[:900]}",
                                            filename=f"{video_title}.{'mp3' if is_audio_platform else 'mp4'}",
                                            read_timeout=600,
                                            write_timeout=600
                                        )
                            
                            success_count += 1
                            sent_successfully = True
                            logger.info(f"✅ Muvaffaqiyatli yuborildi: {video_title[:50]}")
                            break # Muvaffaqiyatli bo'lsa loopdan chiqish
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Yuborishda xatolik (Urinish {attempt}): {e}")
                            if attempt == max_retries:
                                logger.error(f"❌ Faylni yuborib bo'lmadi: {video_title}")
                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text=f"❌ {video_title[:30]}: Yuborishda xatolik (Timeout/Network)"
                                )
                            else:
                                await asyncio.sleep(2) # Qayta urinishdan oldin kutish
                    
                    # Har bir yuborilgan fayldan so'ng statusni yangilash
                    if sent_successfully and video_count > 1:
                        try:
                            await status_msg.edit_text(
                                f"⏳ *Yuborilmoqda:* {success_count}/{video_count}\n🎬 {video_title[:30]}...",
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except: pass
                        
                except Exception as e:
                    logger.error(f"Yuborishda kutilmagan xato: {e}")
                finally:
                    # Har qanday holatda ham faylni o'chiramiz
                    cleanup_file(file_path)

            if video_count > 1:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ Tugadi!\n📤 Muvaffaqiyatli: {success_count}\n❌ Xatolik: {video_count - success_count}"
                )
            await status_msg.delete()

        except Exception as e:
            logger.error(f"Protsessda xato: {e}")
            try:
                await status_msg.edit_text(MESSAGES['error'].format(str(e)))
            except: pass

    def run(self):
        """Botni ishga tushirish"""
        try:
            logger.info("Bot ishga tushmoqda... (Stop: Ctrl+C)")
            self.app.run_polling(close_loop=False) # Loopni PTB yopib qo'ymasligi uchun
        except KeyboardInterrupt:
            logger.info("Bot foydalanuvchi tomonidan to'xtatildi (SIGINT)")
        except SystemExit:
            logger.info("Bot tizim tomonidan to'xtatildi (SIGTERM)")
        except Exception as e:
            logger.error(f"Bot ishga tushirishda kutilmagan xatolik: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            logger.info("Bot to'xtadi.")


if __name__ == '__main__':
    TelegramBot().run()
