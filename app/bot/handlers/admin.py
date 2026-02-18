from telegram import Update
from telegram.ext import ContextTypes
from app.db.session import SessionLocal
from app.db.models import User, Job, Analytics, SubscriptionType
from sqlalchemy import func

from app.core.config import settings
from app.core.logging import logger

async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in settings.ADMIN_IDS:
        return

    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        total_jobs = db.query(Job).count()
        premium_users = db.query(User).filter(User.subscription_type == SubscriptionType.PREMIUM).count()
        
        # Most popular platform
        popular = db.query(Analytics.platform, func.count(Analytics.id).label('count')).group_by(Analytics.platform).order_by(func.count(Analytics.id).desc()).first()
        
        platform_name = popular[0] if popular else "N/A"

        await update.message.reply_text(
            f"📊 **Enterprise Dashboard**\n\n"
            f"👥 Total Users: {total_users}\n"
            f"⭐ Premium: {premium_users}\n"
            f"📦 Total Jobs: {total_jobs}\n"
            f"🔥 Top Platform: {platform_name}\n"
        )
    finally:
        db.close()

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in settings.ADMIN_IDS:
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: `/broadcast [message text]`", parse_mode="Markdown")
        return

    broadcast_msg = " ".join(context.args)
    db = SessionLocal()
    try:
        users = db.query(User).all()
        count = 0
        for user in users:
            try:
                await context.bot.send_message(chat_id=user.id, text=f"📢 **Global Announcement**\n\n{broadcast_msg}", parse_mode="Markdown")
                count += 1
            except Exception as e:
                logger.error(f"Broadcast failed for user {user.id}: {e}")
        
        await update.message.reply_text(f"✅ Broadcast sent to {count} users.")
    finally:
        db.close()

async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in settings.ADMIN_IDS: return

    if not context.args:
        await update.message.reply_text("❌ Usage: `/ban [user_id]`")
        return

    try:
        target_id = int(context.args[0])
        db = SessionLocal()
        user = db.query(User).filter(User.id == target_id).first()
        if user:
            user.is_banned = True
            db.commit()
            await update.message.reply_text(f"🚫 User {target_id} has been banned.")
        else:
            await update.message.reply_text("❌ User not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        db.close()

async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in settings.ADMIN_IDS: return

    if not context.args:
        await update.message.reply_text("❌ Usage: `/unban [user_id]`")
        return

    try:
        target_id = int(context.args[0])
        db = SessionLocal()
        user = db.query(User).filter(User.id == target_id).first()
        if user:
            user.is_banned = False
            db.commit()
            await update.message.reply_text(f"✅ User {target_id} has been unbanned.")
        else:
            await update.message.reply_text("❌ User not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        db.close()

async def search_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in settings.ADMIN_IDS: return

    if not context.args:
        await update.message.reply_text("❌ Usage: `/search [username]`")
        return

    username = context.args[0].replace("@", "").strip()
    db = SessionLocal()
    try:
        # Search by username (case-insensitive)
        users = db.query(User).filter(User.username.ilike(f"%{username}%")).all()
        
        if not users:
            await update.message.reply_text(f"🔍 No users found matching: {username}")
            return

        text = f"🔍 **Search Results for '{username}':**\n\n"
        for u in users:
            status = "🚫 Banned" if u.is_banned else "✅ Active"
            text += f"👤 **{u.full_name or 'N/A'}**\n"
            text += f"🆔 ID: `{u.id}`\n"
            text += f"🔗 User: @{u.username or 'N/A'}\n"
            text += f"💎 Type: {u.subscription_type.value}\n"
            text += f"🚦 Status: {status}\n\n"
        
        if len(text) > 4096:
            text = text[:4080] + "..."
            
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text(f"❌ Error during search: {e}")
    finally:
        db.close()

async def list_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id
    if admin_id not in settings.ADMIN_IDS: return

    db = SessionLocal()
    try:
        # Get 20 most recent users
        users = db.query(User).order_by(User.last_usage_date.desc()).limit(20).all()
        
        if not users:
            await update.message.reply_text("� No users found in the database.")
            return

        text = "� **20 Most Recent Users:**\n\n"
        for u in users:
            status_icon = "🚫" if u.is_banned else "✅"
            username = f"@{u.username}" if u.username else "No Username"
            text += f"{status_icon} `{u.id}` | {username} | {u.subscription_type.value}\n"
        
        text += "\n� Use `/search [username]` for details\n"
        text += "💡 Use `/ban [id]` to suspend"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"List users error: {e}")
        await update.message.reply_text(f"❌ Error listing users: {e}")
    finally:
        db.close()
