from app.bot.handlers import start_handler, message_handler, callback_handler
from app.bot.handlers.admin import admin_stats_handler, broadcast_handler, ban_handler, unban_handler, search_user_handler, list_users_handler
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app.db.session import engine, Base
from app.core.config import settings
from app.core.logging import logger

def main():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Starting Telegram Bot...")
    
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", admin_stats_handler))
    app.add_handler(CommandHandler("broadcast", broadcast_handler))
    app.add_handler(CommandHandler("ban", ban_handler))
    app.add_handler(CommandHandler("unban", unban_handler))
    app.add_handler(CommandHandler("search", search_user_handler))
    app.add_handler(CommandHandler("users", list_users_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Run the bot
    app.run_polling()

if __name__ == "__main__":
    main()
