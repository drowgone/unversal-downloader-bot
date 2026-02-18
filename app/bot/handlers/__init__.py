import uuid
import os
from telegram import Update, InputMediaVideo, InputMediaAudio, InputMediaPhoto
from telegram.ext import ContextTypes, ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.services.user_service import user_service
from app.db.session import SessionLocal
from app.db.models import Job, JobStatus, SubscriptionType
from app.workers.media_tasks import process_media_job
from app.workers.instagram_tasks import process_instagram_job
from app.services.instagram_service import instagram_service
from app.core.logging import logger
from app.core.config import settings
from app.bot.keyboards import get_format_selection_keyboard, get_quality_keyboard, get_cancel_keyboard
from app.bot.handlers.admin import admin_stats_handler, broadcast_handler

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        user = update.effective_user
        if not user: return
        
        logger.info(f"Start command received from user {user.id} ({user.username})")
        db_user = user_service.get_or_create_user(db, user.id, user.username, user.full_name)
        
        if db_user.subscription_type == SubscriptionType.ADMIN:
            status = "👨‍💻 Admin"
            limit_text = "Unlimited (System Access)"
        else:
            status = "⭐ Premium" if db_user.subscription_type == SubscriptionType.PREMIUM else "🆓 Free"
            limit_text = f"{settings.FREE_DAILY_LIMIT if status == '🆓 Free' else 'Unlimited'}"
        
        await update.message.reply_text(
            f"🚀 **Universal Media Processing Platform**\n\n"
            f"Status: {status}\n"
            f"Daily limit: {limit_text}\n\n"
            "Send any URL to begin processing."
        )
    except Exception as e:
        logger.error(f"Error in start_handler: {e}", exc_info=True)
        await update.message.reply_text("❌ An internal error occurred. Please try again later.")
    finally:
        db.close()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re
    text = update.message.text
    if not text: return
    
    # Extract all URLs
    urls = re.findall(r'(https?://[^\s,]+)', text)
    if not urls:
        return

    db = SessionLocal()
    try:
        user_id = update.effective_user.id
        db_user = user_service.get_or_create_user(db, user_id)
        
        if db_user.is_banned:
            await update.message.reply_text("🚫 Your account has been suspended.")
            return

        for url in urls:
            # Clean URL (remove trailing punctuation often caught by regex)
            url = url.strip('.,;)!?')
            
            # Create job entry
            job_id = str(uuid.uuid4())
            user_service.create_job(db, user_id, job_id, url)

            # Check limits for FREE users
            if db_user.subscription_type == SubscriptionType.FREE:
                if db_user.daily_usage_count >= settings.FREE_DAILY_LIMIT:
                    await update.message.reply_text(f"⚠️ Daily limit reached for {url}. Upgrade to Premium!")
                    continue
            
            # Increment usage
            db_user.daily_usage_count += 1
            db.commit()

            if "instagram.com" in url or "tiktok.com" in url:
                msg = await update.message.reply_text(
                    f"🚀 Starting Instagram/TikTok download...\n🔗 {url}",
                    reply_markup=get_cancel_keyboard(job_id)
                )
                process_instagram_job.delay(user_id, job_id, url)
            else:
                msg = await update.message.reply_text(
                    f"🎯 Select processing format for:\n🔗 {url}",
                    reply_markup=get_format_selection_keyboard(job_id)
                )

            # Start status polling for each job
            context.job_queue.run_repeating(
                update_status_v2, interval=5, first=5,
                data={"job_id": job_id, "user_id": user_id, "chat_id": update.effective_chat.id, "msg_id": msg.message_id},
                name=f"job_{job_id}"
            )
            
    except Exception as e:
        logger.error(f"Error in message_handler: {e}", exc_info=True)
        await update.message.reply_text("❌ Error processing request. Please check the URL.")
    finally:
        db.close()

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(':')
    action = data[0]
    
    if action == "select_format":
        format_type = data[1]
        job_id = data[2]
        await query.edit_message_text(
            f"⚡ Select {format_type.upper()} quality:",
            reply_markup=get_quality_keyboard(format_type, job_id)
        )
        
    elif action == "back_to_format":
        job_id = data[1]
        await query.edit_message_text(
            "🎯 Select processing format:",
            reply_markup=get_format_selection_keyboard(job_id)
        )
        
    elif action == "cancel": 
        job_id = data[1]
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status not in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                from app.workers.celery_app import celery_app
                
                # 1. Revoke main task
                if job.celery_task_id:
                    celery_app.control.revoke(job.celery_task_id, terminate=True)
                
                # 2. Revoke all sub-tasks (playlists)
                items = db.query(MediaItem).filter(MediaItem.job_id == job_id).all()
                for item in items:
                    if item.celery_task_id:
                        celery_app.control.revoke(item.celery_task_id, terminate=True)
                
                user_service.update_job_status(db, job_id, JobStatus.CANCELLED)
                db.commit()
                await query.answer("🚫 Task and all sub-tasks cancelled.")
                await query.edit_message_text(f"🚫 **Job Cancelled**\n🎬 {job.title or 'Media'}")
            else:
                await query.answer("⚠️ Task already finished or not found.")
        finally:
            db.close()
        
    elif action == "start_job":
        format_type = data[1]
        quality = data[2]
        job_id = data[3]
        user_id = update.effective_user.id
        
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                await query.edit_message_text("⚠️ Session expired. Please send the link again.")
                return

            # Check limits here instead of message_handler to allow keyboard showing
            db_user = user_service.get_or_create_user(db, user_id)
            if db_user.subscription_type == SubscriptionType.FREE:
                if db_user.daily_usage_count >= settings.FREE_DAILY_LIMIT:
                    await query.edit_message_text("⚠️ Daily limit reached. Upgrade to Premium!")
                    return
            elif db_user.subscription_type == SubscriptionType.ADMIN:
                # Admins have no limits
                pass

            # Increment usage
            db_user.daily_usage_count += 1
            db.commit()
            
            await query.edit_message_text(
                f"✅ Task queued in high-priority workers. [{format_type.upper()} | {quality}]\n"
                "⏳ Initializing processing engine...",
                reply_markup=get_cancel_keyboard(job_id)
            )
            
            # Explicitly route to 'media' queue
            process_media_job.apply_async(
                args=[user_id, job_id, job.url, format_type, quality],
                queue="media"
            )
            
            # Start status polling
            context.job_queue.run_repeating(
                update_status_v2, interval=5, first=5,
                data={"job_id": job_id, "user_id": user_id, "chat_id": update.effective_chat.id, "msg_id": query.message.message_id},
                name=f"job_{job_id}"
            )
        finally:
            db.close()

async def update_status_v2(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    job_id = job_data["job_id"]
    chat_id = job_data["chat_id"]
    
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            context.job.schedule_removal()
            return

        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.DOWNLOADING: "📥",
            JobStatus.CONVERTING: "🔄",
            JobStatus.COMPRESSING: "🗜️",
            JobStatus.UPLOADING: "☁️",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
            JobStatus.CANCELLED: "🚫"
        }.get(job.status, "❓")

        progress_bar = ""
        details = ""
        if job.total_items > 1:
            # Playlist progress
            pct = (job.completed_items / job.total_items) * 100 if job.total_items > 0 else 0
            filled = int(pct / 10)
            progress_bar = f"📦 Processed: {job.completed_items} / {job.total_items}\n[{'●' * filled}{'○' * (10 - filled)}] {int(pct)}%"
            
            if job.failed_items > 0:
                details = f"\n⚠️ Failed: {job.failed_items} items"
        elif job.status == JobStatus.DOWNLOADING:
            # Single file progress
            pct = job.download_percentage if job.download_percentage is not None else 0
            filled = int(pct / 10)
            progress_bar = f"[{'●' * filled}{'○' * (10 - filled)}] {pct}%"
            details = f"\n⚡ Speed: {job.current_speed or 'N/A'} | ETA: {job.eta or 'N/A'}"

        text = (
            f"{status_emoji} **Job Status: {job.status.value.upper()}**\n"
            f"🎬 Title: {job.title or 'Extracting...'}\n\n"
            f"{progress_bar}"
            f"{details}"
        )

        if job.status == JobStatus.COMPLETED:
            context.job.schedule_removal()
            if job.s3_url:
                text += f"\n\n📦 **Large File Ready!**\n🔗 [Download from Cloud]({job.s3_url})\n_(Link expires in 24h)_"
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
            elif job.storage_path and os.path.exists(job.storage_path):
                # Send file logic
                if job.media_type == 'carousel':
                    # Find all files in the same directory
                    job_dir = os.path.dirname(job.storage_path)
                    files = [os.path.join(job_dir, f) for f in os.listdir(job_dir) if os.path.isfile(os.path.join(job_dir, f))]
                    
                    if len(files) > 1:
                        from telegram import InputMediaPhoto, InputMediaVideo
                        media_group = []
                        for f in sorted(files)[:10]: # TG limit
                            if f.lower().endswith(('.mp4', '.mov', '.avi')):
                                media_group.append(InputMediaVideo(open(f, 'rb')))
                            else:
                                media_group.append(InputMediaPhoto(open(f, 'rb')))
                        
                        await context.bot.send_media_group(chat_id=chat_id, media=media_group, caption=f"✅ {job.title or 'Media'} processed.")
                    else:
                        await context.bot.send_document(chat_id=chat_id, document=open(job.storage_path, 'rb'), caption=f"✅ {job.title or 'Media'} processed.")
                else:
                    await context.bot.send_document(
                        chat_id=chat_id, 
                        document=open(job.storage_path, 'rb'),
                        caption=f"✅ {job.title or 'Media'} processed successfully."
                    )
            return

        if job.status == JobStatus.FAILED:
            context.job.schedule_removal()
            text += f"\n\n⚠️ Error: {job.error_message}"
            await context.bot.edit_message_text(chat_id=chat_id, message_id=job_data.get("msg_id"), text=text, parse_mode="Markdown")
            return

        # Update existing message if possible
        msg_id = job_data.get("msg_id")
        if msg_id:
            try:
                # Add cancel button for active states
                reply_markup = None
                if job.status in [JobStatus.PENDING, JobStatus.DOWNLOADING, JobStatus.CONVERTING]:
                    reply_markup = get_cancel_keyboard(job_id)

                await context.bot.edit_message_text(
                    chat_id=chat_id, 
                    message_id=msg_id, 
                    text=text, 
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "Message is not modified" not in str(e):
                    logger.error(f"Failed to edit status message: {e}")

    except Exception as e:
        logger.error(f"Status update failed: {e}")
    finally:
        db.close()
