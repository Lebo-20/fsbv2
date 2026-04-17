import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot.config import BOT_TOKEN, LOG_FILE
from bot.handlers.command import start_handler, history_handler
from bot.handlers.callback import mp_nav_cb
from bot.handlers.message import reels_handler

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def main():
    if not BOT_TOKEN:
        print("MOHON ISI BOT_TOKEN di file .env!")
        return

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register Handlers
    application.add_handler(CommandHandler('start', start_handler))
    application.add_handler(CommandHandler('history', history_handler))
    
    from bot.handlers.command import search_handler, add_catalog_handler
    application.add_handler(CommandHandler('cari', search_handler))
    application.add_handler(CommandHandler('add_catalog', add_catalog_handler))
    
    # Admin Commands
    from bot.handlers.command import upload_drama, stats_handler, broadcast_handler, unban_handler
    application.add_handler(CommandHandler('upload_drama', upload_drama))
    application.add_handler(CommandHandler('stats', stats_handler))
    application.add_handler(CommandHandler('broadcast', broadcast_handler))
    application.add_handler(CommandHandler('unban', unban_handler))

    # Update Command (git pull + restart)
    from bot.updater import update_handler
    application.add_handler(CommandHandler('update', update_handler))

    application.add_handler(CallbackQueryHandler(mp_nav_cb, pattern='^(nav_|list_|adm_|buy_req_|show_cat_)'))
    application.add_handler(MessageHandler((filters.TEXT | filters.VIDEO | filters.Document.VIDEO | filters.PHOTO) & (~filters.COMMAND), reels_handler))

    async def global_logger(update, context):
        logging.info(f"RAW UPDATE DUMP: {update.to_dict()}")
    from telegram.ext import TypeHandler
    from telegram import Update
    application.add_handler(TypeHandler(Update, global_logger), group=-1)

    from bot.saweria import check_saweria_payments
    application.job_queue.run_repeating(check_saweria_payments, interval=15, first=5)

    print("--- Xiao Reels Bot Modular STARTED ---")
    application.run_polling()

if __name__ == '__main__':
    main()
