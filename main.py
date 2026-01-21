"""
ArchiveBot - Personal Content Archiving System for Telegram
Main entry point
"""

import sys
import signal
import logging
from functools import wraps
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import get_config
from src.utils.logger import setup_logging
from src.utils.i18n import get_i18n
from src.models.database import init_database
from src.storage.database import DatabaseStorage
from src.storage.telegram import TelegramStorage
from src.core.tag_manager import TagManager
from src.core.storage_manager import StorageManager
from src.core.search_engine import SearchEngine

from src.bot import commands, handlers, callbacks
from src.ai.summarizer import get_ai_summarizer

logger = logging.getLogger(__name__)


def owner_only(func):
    """
    Decorator to restrict command/handler to bot owner only
    
    Args:
        func: Handler function
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(update: Update, context):
        config = get_config()
        owner_id = config.owner_id
        user_id = update.effective_user.id
        
        if user_id != owner_id:
            i18n = get_i18n()
            await update.message.reply_text(i18n.t('unauthorized'))
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return
        
        return await func(update, context)
    
    return wrapper


async def error_handler(update: Update, context) -> None:
    """
    Handle errors in the bot
    
    Args:
        update: Telegram update
        context: Bot context
    """
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    try:
        i18n = get_i18n()
        if update and update.effective_message:
            await update.effective_message.reply_text(
                i18n.t('error_occurred', error=str(context.error))
            )
    except Exception as e:
        logger.error(f"Error sending error message: {e}")


def main():
    """
    Main entry point for ArchiveBot
    """
    db = None  # Initialize for finally block
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if db:
            db.close()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config = get_config()
        
        # Setup logging
        setup_logging(
            level=config.get('logging.level', 'INFO'),
            log_file=config.get('logging.file'),
            console=config.get('logging.console', True)
        )
        
        logger.info("=" * 50)
        logger.info("ArchiveBot Starting...")
        logger.info("=" * 50)
        
        # Initialize i18n
        i18n = get_i18n(config.language)
        logger.info(f"Language: {i18n.get_language_name()}")
        
        # Initialize database
        db_path = config.database_path
        logger.info(f"Database: {db_path}")
        db = init_database(db_path)
        
        # Log database info
        stats = db.get_stats()
        logger.info(f"Database stats: {stats['total_archives']} archives, {stats['total_tags']} tags")
        
        # Initialize storage and managers
        db_storage = DatabaseStorage(db)
        tag_manager = TagManager(db_storage)
        
        # Create application
        application = Application.builder().token(config.bot_token).build()
        
        # Initialize Telegram storage if channel is configured
        telegram_storage = None
        if config.telegram_storage_enabled:
            telegram_storage = TelegramStorage(
                bot=application.bot,
                channel_id=config.telegram_channel_id
            )
            logger.info(f"Telegram storage enabled: channel_id={config.telegram_channel_id}")
        else:
            logger.warning("Telegram storage not configured - files will be stored as references only")
        
        storage_manager = StorageManager(db_storage, tag_manager, telegram_storage)
        search_engine = SearchEngine(db_storage)
        
        # Initialize AI summarizer if enabled
        ai_summarizer = None
        if config.ai.get('enabled', False):
            try:
                ai_summarizer = get_ai_summarizer(config.ai)
                if ai_summarizer and ai_summarizer.is_available():
                    logger.info(f"AI summarizer initialized: {config.ai.get('api', {}).get('provider', 'unknown')}")
                else:
                    logger.warning("AI summarizer initialization failed - check API configuration")
            except Exception as e:
                logger.error(f"Failed to initialize AI summarizer: {e}")
        else:
            logger.info("AI features disabled")
        
        logger.info("All components initialized successfully")
        
        # Store managers in bot_data for access in handlers
        application.bot_data['db_storage'] = db_storage
        application.bot_data['database'] = db  # Add database reference
        application.bot_data['tag_manager'] = tag_manager
        application.bot_data['storage_manager'] = storage_manager
        application.bot_data['search_engine'] = search_engine
        application.bot_data['ai_summarizer'] = ai_summarizer
        # Store managers in bot_data for access in handlers
        application.bot_data['db_storage'] = db_storage
        application.bot_data['tag_manager'] = tag_manager
        application.bot_data['storage_manager'] = storage_manager
        application.bot_data['search_engine'] = search_engine
        
        # Register command handlers (with owner check)
        application.add_handler(CommandHandler("start", owner_only(commands.start_command)))
        application.add_handler(CommandHandler("help", owner_only(commands.help_command)))
        application.add_handler(CommandHandler("search", owner_only(commands.search_command)))
        application.add_handler(CommandHandler("tags", owner_only(commands.tags_command)))
        application.add_handler(CommandHandler("summarize", owner_only(commands.summarize_command)))
        application.add_handler(CommandHandler("ai", owner_only(commands.ai_status_command)))
        application.add_handler(CommandHandler("stats", owner_only(commands.stats_command)))
        application.add_handler(CommandHandler("language", owner_only(commands.language_command)))
        
        # Register callback handlers
        application.add_handler(CallbackQueryHandler(
            owner_only(callbacks.handle_language_callback),
            pattern='^lang_'
        ))
        
        # Register message handlers (with owner check)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            owner_only(handlers.handle_message)
        ))
        application.add_handler(MessageHandler(
            filters.PHOTO,
            owner_only(handlers.handle_photo)
        ))
        application.add_handler(MessageHandler(
            filters.VIDEO,
            owner_only(handlers.handle_video)
        ))
        application.add_handler(MessageHandler(
            filters.Document.ALL,
            owner_only(handlers.handle_document)
        ))
        application.add_handler(MessageHandler(
            filters.AUDIO,
            owner_only(handlers.handle_audio)
        ))
        application.add_handler(MessageHandler(
            filters.VOICE,
            owner_only(handlers.handle_voice)
        ))
        application.add_handler(MessageHandler(
            filters.ANIMATION,
            owner_only(handlers.handle_animation)
        ))
        application.add_handler(MessageHandler(
            filters.Sticker.ALL,
            owner_only(handlers.handle_sticker)
        ))
        application.add_handler(MessageHandler(
            filters.CONTACT,
            owner_only(handlers.handle_contact)
        ))
        application.add_handler(MessageHandler(
            filters.LOCATION,
            owner_only(handlers.handle_location)
        ))
        
        # Register error handler
        application.add_error_handler(error_handler)
        
        logger.info("All handlers registered")
        logger.info(f"Bot owner ID: {config.owner_id}")
        logger.info("Bot is ready! Starting polling...")
        
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except FileNotFoundError as e:
        print(f"\n❌ Configuration Error:\n{e}\n")
        print("Please copy config/config.template.yaml to config/config.yaml and configure it.")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Configuration Error:\n{e}\n")
        print("Please check your configuration in config/config.yaml")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up resources
        if db:
            try:
                db.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
        logger.info("ArchiveBot shutdown complete")


if __name__ == "__main__":
    main()
