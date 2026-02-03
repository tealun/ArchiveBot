"""
ArchiveBot - Personal Content Archiving System for Telegram
Main entry point
"""

import sys
import signal
import logging
from functools import wraps
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file before importing config
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
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
from src.core.note_manager import NoteManager
from src.core.trash_manager import TrashManager
from src.core.export_manager import ExportManager
from src.core.backup_manager import BackupManager
from src.core.review_manager import ReviewManager
from src.core.ai_data_cache import AIDataCache

from src.bot import commands
from src.bot import message_handlers as handlers
from src.bot import callback_router as callbacks
from src.bot.unknown_command import handle_unknown_command
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
        
        # Check if effective_user exists
        if not update.effective_user:
            logger.warning("Update has no effective_user, skipping authorization check")
            return
        
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
    # Import network error types
    from telegram.error import NetworkError
    try:
        import httpx
        network_errors = (NetworkError, httpx.ReadError, httpx.ConnectError, httpx.TimeoutException)
    except ImportError:
        network_errors = (NetworkError,)
    
    # Downgrade network errors to WARNING level (temporary issues with auto-retry)
    if isinstance(context.error, network_errors):
        logger.warning(f"Network error (will auto-retry): {context.error.__class__.__name__}")
    else:
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
        note_manager = NoteManager(db)
        backup_manager = BackupManager(
            db_path=config.database_path,
            backup_dir="data/backups"
        )
        
        # Create application with network configuration
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=10.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=10.0
        )
        application = Application.builder().token(config.bot_token).request(request).build()
        
        # Initialize Telegram storage if channel is configured
        telegram_storage = None
        if config.telegram_storage_enabled:
            # 构建telegram配置（从环境变量或YAML获取）
            telegram_config = {
                'enabled': True,
                'channel_id': config.get('storage.telegram.channels.default') or config.telegram_channel_id,  # 向后兼容
                'channels': {
                    'default': config.get('storage.telegram.channels.default'),
                    'text': config.get('storage.telegram.channels.text'),
                    'ebook': config.get('storage.telegram.channels.ebook'),
                    'document': config.get('storage.telegram.channels.document'),
                    'image': config.get('storage.telegram.channels.image'),
                    'media': config.get('storage.telegram.channels.media'),
                    'note': config.get('storage.telegram.channels.note'),
                },
                'type_mapping': config.get('storage.telegram.type_mapping', {})
            }
            
            telegram_storage = TelegramStorage(
                bot=application.bot,
                config=telegram_config
            )
            
            # 获取配置的频道数量
            channels_count = len([v for v in telegram_config['channels'].values() if v])
            if channels_count > 0:
                logger.info(f"Telegram storage enabled: {channels_count} channels configured")
            else:
                logger.info(f"Telegram storage enabled: single channel mode (channel_id={telegram_config['channel_id']})")
        else:
            logger.warning("Telegram storage not configured - files will be stored as references only")
        
        storage_manager = StorageManager(db_storage, tag_manager, telegram_storage)
        search_engine = SearchEngine(db_storage)
        trash_manager = TrashManager(db, telegram_storage)
        export_manager = ExportManager(db, note_manager, tag_manager)
        review_manager = ReviewManager(db_storage, tag_manager)
        
        # Initialize AI data cache for efficient data gathering (传入config以支持排除过滤)
        ai_data_cache = AIDataCache(db_storage, config)
        
        # 将缓存实例传递给需要的管理器（事件驱动失效）
        storage_manager.set_ai_cache(ai_data_cache)
        trash_manager.set_ai_cache(ai_data_cache)
        
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
        application.bot_data['telegram_storage'] = telegram_storage  # Add telegram storage for note forwarding
        application.bot_data['note_manager'] = note_manager
        application.bot_data['trash_manager'] = trash_manager
        application.bot_data['export_manager'] = export_manager
        application.bot_data['backup_manager'] = backup_manager
        application.bot_data['review_manager'] = review_manager
        application.bot_data['tag_manager'] = tag_manager
        application.bot_data['storage_manager'] = storage_manager
        application.bot_data['search_engine'] = search_engine
        application.bot_data['ai_summarizer'] = ai_summarizer
        application.bot_data['ai_data_cache'] = ai_data_cache  # AI数据缓存
        
        # Register command handlers (with owner check)
        application.add_handler(CommandHandler("start", owner_only(commands.start_command)))
        application.add_handler(CommandHandler("help", owner_only(commands.help_command)))
        application.add_handler(CommandHandler(["search", "s"], owner_only(commands.search_command)))
        application.add_handler(CommandHandler(["tags", "t"], owner_only(commands.tags_command)))
        application.add_handler(CommandHandler("ai", owner_only(commands.ai_status_command)))
        application.add_handler(CommandHandler(["stats", "st"], owner_only(commands.stats_command)))
        application.add_handler(CommandHandler(["language", "la"], owner_only(commands.language_command)))
        application.add_handler(CommandHandler(["setting", "set"], owner_only(commands.setting_command)))
        application.add_handler(CommandHandler(["note", "n"], owner_only(commands.note_command)))  # /n as short alias
        application.add_handler(CommandHandler("notes", owner_only(commands.notes_command)))
        application.add_handler(CommandHandler("cancel", owner_only(commands.cancel_command)))
        application.add_handler(CommandHandler("trash", owner_only(commands.trash_command)))
        application.add_handler(CommandHandler("export", owner_only(commands.export_command)))
        application.add_handler(CommandHandler("backup", owner_only(commands.backup_command)))
        application.add_handler(CommandHandler("review", owner_only(commands.review_command)))
        application.add_handler(CommandHandler(["rand", "r"], owner_only(commands.rand_command)))
        application.add_handler(CommandHandler("restart", owner_only(commands.restart_command)))
        
        # Register callback handlers (统一处理)
        application.add_handler(CallbackQueryHandler(
            owner_only(callbacks.handle_callback_query)
        ))
        
        # Register unknown command handler (must be before message handlers)
        from telegram.ext import MessageHandler
        application.add_handler(MessageHandler(
            filters.COMMAND,
            owner_only(handle_unknown_command)
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
        
        # 配置自动备份定时任务
        async def auto_backup_job(context: ContextTypes.DEFAULT_TYPE):
            """自动备份任务"""
            try:
                backup_mgr = context.bot_data.get('backup_manager')
                if not backup_mgr:
                    logger.warning("Backup manager not found in auto backup job")
                    return
                
                # 检查是否需要备份（基于配置的间隔）
                backup_interval = config.get('backup.auto_interval_hours', 168)
                if backup_mgr.auto_backup_check(interval_hours=backup_interval):
                    logger.info(f"Auto backup triggered (interval: {backup_interval}h)")
                    filename = backup_mgr.create_backup(description="Auto backup")
                    if filename:
                        logger.info(f"✓ Auto backup created: {filename}")
                    else:
                        logger.error("✗ Auto backup failed")
                else:
                    logger.debug(f"Auto backup skipped (last backup < {backup_interval}h ago)")
            except Exception as e:
                logger.error(f"Error in auto backup job: {e}", exc_info=True)
        
        # 内存清理任务
        async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
            """定期清理任务：释放未使用的内存"""
            try:
                # 清理AI会话
                from src.core.ai_session import get_session_manager
                session_mgr = get_session_manager()
                session_mgr.cleanup_expired()
                
                # 清理AI缓存（如果启用）
                ai_sum = context.bot_data.get('ai_summarizer')
                if ai_sum and hasattr(ai_sum, 'cache') and ai_sum.cache:
                    ai_sum.cache.cleanup()
                
                logger.debug("Memory cleanup completed")
            except Exception as e:
                logger.error(f"Error in cleanup job: {e}", exc_info=True)
        
        # 添加定时任务
        job_queue = application.job_queue
        if job_queue:
            # 自动备份：启动后1分钟首次检查，然后每天检查一次（配置168h=7天备份一次）
            job_queue.run_once(auto_backup_job, when=60)
            job_queue.run_repeating(auto_backup_job, interval=86400, first=60)  # 每24小时检查
            logger.info("✓ Auto backup scheduler started (check: daily, backup: every 7 days per config)")
            
            # 内存清理：启动后5分钟，然后每30分钟
            job_queue.run_once(cleanup_job, when=300)
            job_queue.run_repeating(cleanup_job, interval=1800, first=300)
            logger.info("✓ Memory cleanup scheduler started (interval: 30 minutes)")
        else:
            logger.warning("JobQueue not available - auto backup and cleanup disabled")
        
        # 设置机器人命令菜单（多语言支持）- 通过 job_queue 延迟执行避免 event loop 冲突
        from telegram import BotCommand
        
        async def set_bot_commands_job(context: ContextTypes.DEFAULT_TYPE):
            """设置机器人命令菜单任务 - 为所有支持的语言设置"""
            try:
                # 定义多语言命令菜单
                commands_config = {
                    None: [  # 默认语言（未设置时）- 使用英文
                        BotCommand("start", "Start bot"),
                        BotCommand("help", "Show help"),
                        BotCommand("search", "Search archives (/s)"),
                        BotCommand("note", "Add note (/n)"),
                        BotCommand("notes", "View notes"),
                        BotCommand("tags", "List tags (/t)"),
                        BotCommand("stats", "Show statistics (/st)"),
                        BotCommand("setting", "System settings (/set)"),
                        BotCommand("review", "Review archives"),
                        BotCommand("trash", "Trash bin"),
                        BotCommand("export", "Export data"),
                        BotCommand("backup", "Backup management"),
                        BotCommand("ai", "AI status"),
                        BotCommand("language", "Change language (/la)"),
                        BotCommand("restart", "Restart system"),
                    ],
                    "zh": [  # 简体中文 (Telegram使用 'zh' 作为中文语言代码)
                        BotCommand("start", "开始使用"),
                        BotCommand("help", "查看帮助"),
                        BotCommand("search", "搜索归档 (简写: /s)"),
                        BotCommand("note", "添加笔记 (简写: /n)"),
                        BotCommand("notes", "查看笔记"),
                        BotCommand("tags", "标签列表 (简写: /t)"),
                        BotCommand("stats", "统计信息 (简写: /st)"),
                        BotCommand("setting", "系统配置 (简写: /set)"),
                        BotCommand("review", "存档回顾"),
                        BotCommand("trash", "垃圾箱"),
                        BotCommand("export", "导出数据"),
                        BotCommand("backup", "备份管理"),
                        BotCommand("ai", "AI状态"),
                        BotCommand("language", "切换语言 (简写: /la)"),
                        BotCommand("restart", "重启系统"),
                    ],
                    "en": [  # 英语
                        BotCommand("start", "Start bot"),
                        BotCommand("help", "Show help"),
                        BotCommand("search", "Search archives (/s)"),
                        BotCommand("note", "Add note (/n)"),
                        BotCommand("notes", "View notes"),
                        BotCommand("tags", "List tags (/t)"),
                        BotCommand("stats", "Show statistics (/st)"),
                        BotCommand("setting", "System settings (/set)"),
                        BotCommand("review", "Review archives"),
                        BotCommand("trash", "Trash bin"),
                        BotCommand("export", "Export data"),
                        BotCommand("backup", "Backup management"),
                        BotCommand("ai", "AI status"),
                        BotCommand("language", "Change language (/la)"),
                        BotCommand("restart", "Restart system"),
                    ],
                    "ja": [  # 日语
                        BotCommand("start", "ボット初期化"),
                        BotCommand("help", "ヘルプ表示"),
                        BotCommand("search", "アーカイブ検索 (/s)"),
                        BotCommand("note", "ノート追加 (/n)"),
                        BotCommand("notes", "ノート表示"),
                        BotCommand("tags", "タグ一覧 (/t)"),
                        BotCommand("stats", "統計情報 (/st)"),
                        BotCommand("setting", "システム設定 (/set)"),
                        BotCommand("review", "アーカイブレビュー"),
                        BotCommand("trash", "ゴミ箱"),
                        BotCommand("export", "データエクスポート"),
                        BotCommand("backup", "バックアップ管理"),
                        BotCommand("ai", "AIステータス"),
                        BotCommand("language", "言語変更 (/la)"),
                        BotCommand("restart", "システム再起動"),
                    ],
                    "ko": [  # 韩语
                        BotCommand("start", "봇 초기화"),
                        BotCommand("help", "도움말 표시"),
                        BotCommand("search", "아카이브 검색 (/s)"),
                        BotCommand("note", "노트 추가 (/n)"),
                        BotCommand("notes", "노트 표시"),
                        BotCommand("tags", "태그 목록 (/t)"),
                        BotCommand("stats", "통계 표시 (/st)"),
                        BotCommand("setting", "시스템 설정 (/set)"),
                        BotCommand("review", "아카이브 리뷰"),
                        BotCommand("trash", "휴지통"),
                        BotCommand("export", "데이터 내보내기"),
                        BotCommand("backup", "백업 관리"),
                        BotCommand("ai", "AI 상태"),
                        BotCommand("language", "언어 변경 (/la)"),
                        BotCommand("restart", "시스템 재시작"),
                    ],
                    "es": [  # 西班牙语
                        BotCommand("start", "Inicializar bot"),
                        BotCommand("help", "Mostrar ayuda"),
                        BotCommand("search", "Buscar archivos (/s)"),
                        BotCommand("note", "Añadir nota (/n)"),
                        BotCommand("notes", "Ver notas"),
                        BotCommand("tags", "Lista de etiquetas (/t)"),
                        BotCommand("stats", "Mostrar estadísticas (/st)"),
                        BotCommand("setting", "Configuración (/set)"),
                        BotCommand("review", "Revisar archivos"),
                        BotCommand("trash", "Papelera"),
                        BotCommand("export", "Exportar datos"),
                        BotCommand("backup", "Gestión de copias"),
                        BotCommand("ai", "Estado de IA"),
                        BotCommand("language", "Cambiar idioma (/la)"),
                        BotCommand("restart", "Reiniciar sistema"),
                    ],
                }
                
                # 为所有支持的语言设置命令菜单
                success_count = 0
                for language_code, commands in commands_config.items():
                    try:
                        # 根据 language_code 是否为 None 决定调用方式
                        if language_code is None:
                            # 默认语言：不传 language_code 参数
                            await context.bot.set_my_commands(commands=commands)
                        else:
                            # 特定语言：传递 language_code 参数
                            await context.bot.set_my_commands(
                                commands=commands,
                                language_code=language_code
                            )
                        lang_name = language_code if language_code else "default"
                        logger.info(f"✓ Commands set for language: {lang_name} ({len(commands)} commands)")
                        success_count += 1
                    except Exception as e:
                        lang_name = language_code if language_code else "default"
                        logger.error(f"Failed to set commands for {lang_name}: {e}")
                
                logger.info(f"✓ Bot commands menu configured for {success_count}/{len(commands_config)} languages")
                
                # 为 owner 用户设置个人命令菜单（基于配置的语言）
                try:
                    owner_id = context.bot_data.get('owner_id')
                    bot_language = config.get('bot.language', 'zh-CN')
                    
                    if owner_id:
                        from telegram import BotCommandScopeChat
                        
                        # 根据配置语言选择命令
                        lang_map = {
                            'zh-CN': 'zh',
                            'zh-TW': 'zh',
                            'en': 'en',
                            'ja': 'ja',
                            'ko': 'ko',
                            'es': 'es',
                        }
                        telegram_lang = lang_map.get(bot_language, 'zh')
                        owner_commands = commands_config.get(telegram_lang, commands_config.get('zh'))
                        
                        scope = BotCommandScopeChat(chat_id=owner_id)
                        await context.bot.set_my_commands(
                            commands=owner_commands,
                            scope=scope,
                            language_code=telegram_lang
                        )
                        logger.info(f"✓ Owner ({owner_id}) commands set to {telegram_lang}")
                except Exception as owner_error:
                    logger.warning(f"Failed to set owner commands: {owner_error}")
                
            except Exception as e:
                logger.error(f"Failed to set bot commands: {e}")
        
        # 检查并发送重启完成通知
        async def check_restart_notification(context: ContextTypes.DEFAULT_TYPE):
            """检查是否需要发送重启完成通知"""
            try:
                from src.bot.commands.restart import load_restart_state, clear_restart_state
                from src.utils.i18n import get_i18n
                from datetime import datetime
                from telegram.constants import ParseMode
                
                state = load_restart_state()
                if state:
                    chat_id = state.get('chat_id')
                    language = state.get('language', 'en')
                    
                    # 获取 i18n 实例
                    i18n = get_i18n(language)
                    
                    # 获取当前时间
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    restart_complete_msg = i18n.t('restart_complete', time=current_time)
                    
                    # 发送重启完成消息
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=restart_complete_msg,
                        parse_mode=ParseMode.HTML
                    )
                    
                    logger.info(f"✓ Restart complete notification sent to chat {chat_id}")
                    
                    # 清除重启状态文件
                    clear_restart_state()
            except Exception as e:
                logger.error(f"Failed to send restart notification: {e}", exc_info=True)
        
        # 使用 post_init 在 bot 初始化后设置命令菜单
        async def post_init_callback(app: Application) -> None:
            """在 bot 初始化后执行的回调"""
            logger.info("Bot initialized, setting up commands menu...")
            if app.job_queue:
                app.job_queue.run_once(set_bot_commands_job, when=5)
                logger.info("✓ Bot commands setup scheduled (will execute in 5 seconds)")
                
                # 检查是否需要发送重启完成通知
                app.job_queue.run_once(check_restart_notification, when=3)
                logger.info("✓ Restart notification check scheduled")
        
        application.post_init = post_init_callback
        
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
