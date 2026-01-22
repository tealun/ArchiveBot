"""
Bot commands implementation
Handles /start, /help, /search, /tags, /stats, /language
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.i18n import get_i18n
from ..utils.config import get_config
from ..utils.helpers import format_file_size
from ..core.search_engine import SearchEngine
from ..core.tag_manager import TagManager
from ..storage.database import DatabaseStorage
from ..ai.summarizer import get_ai_summarizer

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        config = get_config()
        
        # Set language from config
        i18n.set_language(config.language)
        
        welcome_msg = i18n.t('welcome')
        await update.message.reply_text(welcome_msg)
        
        logger.info(f"Start command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        help_msg = i18n.t('help')
        
        await update.message.reply_text(
            help_msg,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Help command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /search command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # Get search query
        query = ' '.join(context.args) if context.args else None
        
        if not query:
            await update.message.reply_text(i18n.t('search_no_keyword'))
            return
        
        # Get search engine from context
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        
        if not search_engine:
            await update.message.reply_text("Search engine not initialized")
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(i18n.t('processing'))
        
        # Perform search with pagination
        page_size = 10
        page = 0  # First page
        offset = page * page_size
        search_result = search_engine.search(query, limit=page_size, offset=offset)
        
        # Get total count for pagination
        total_count = search_result.get('total_count', 0)
        
        # Format and send results (with HTML links)
        result_text, results_with_ai = search_engine.format_results(search_result, with_links=True)
        
        # Build keyboard with AI buttons and pagination
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from ..utils.helpers import truncate_text
        from urllib.parse import quote
        
        keyboard = []
        
        # AI解析按钮
        if results_with_ai:
            for item in results_with_ai:
                # 从标题中提取几个字作为引导，例如：🤖 #2《华尔街之狼…》
                title_preview = truncate_text(item['title'], 12)
                button_text = f"🤖 #{item['index']}《{title_preview}》"
                callback_data = f"ai_view:{item['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # 分页按钮
        if total_count > page_size:
            nav_row = []
            total_pages = (total_count + page_size - 1) // page_size
            encoded_query = quote(query)
            
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"search_page:{encoded_query}:{page-1}"))
            
            nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="search_noop"))
            
            if (page + 1) * page_size < total_count:
                nav_row.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"search_page:{encoded_query}:{page+1}"))
            
            if nav_row:
                keyboard.append(nav_row)
        
        # 发送结果
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_msg.edit_text(
                result_text, 
                parse_mode=ParseMode.HTML, 
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        else:
            await processing_msg.edit_text(result_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
        logger.info(f"Search command: query='{query}', results={search_result.get('count', 0)}")
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tags command - 显示标签按钮矩阵
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        tag_manager: TagManager = context.bot_data.get('tag_manager')
        
        if not tag_manager:
            await update.message.reply_text("Tag manager not initialized")
            return
        
        # Get all tags (sorted by count descending)
        tags = tag_manager.get_all_tags(limit=100)
        
        if not tags:
            await update.message.reply_text(i18n.t('tags_empty'))
            return
        
        # 构建按钮矩阵（3列，分页显示）
        page = 0  # 当前页
        page_size = 30  # 每页30个标签
        
        # 获取当前页的标签
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_tags = tags[start_idx:end_idx]
        
        # 构建按钮
        keyboard = []
        row = []
        for i, tag in enumerate(page_tags):
            tag_name = tag.get('tag_name')
            count = tag.get('count', 0)
            
            # 按钮文本：标签名 (数量)
            button_text = f"#{tag_name} ({count})"
            # 回调数据：tag:标签名:页码
            callback_data = f"tag:{tag_name}:0"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            # 每3个按钮一行
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # 添加最后一行（如果有）
        if row:
            keyboard.append(row)
        
        # 添加分页按钮
        nav_row = []
        total_pages = (len(tags) + page_size - 1) // page_size
        
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"tags_page:{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="tags_noop"))
        
        if end_idx < len(tags):
            nav_row.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"tags_page:{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"🏷️ 标签列表 ({len(tags)} 个)\n\n点击标签查看相关内容："
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
        logger.info(f"Tags command executed: {len(tags)} tags, page {page}")
        
    except Exception as e:
        logger.error(f"Error in tags_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        db_storage: DatabaseStorage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await update.message.reply_text("Database storage not initialized")
            return
        
        # Get stats from database
        stats = db_storage.db.get_stats()
        
        # Get database file size
        import os
        db_path = db_storage.db.db_path
        db_size = 0
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
        
        # Format stats
        total_archives = stats.get('total_archives', 0)
        total_tags = stats.get('total_tags', 0)
        total_size = format_file_size(stats.get('total_size', 0))
        db_size_formatted = format_file_size(db_size)
        last_archive = stats.get('last_archive', 'N/A')
        
        message = i18n.t(
            'stats',
            total_archives=total_archives,
            total_tags=total_tags,
            storage_used=total_size,
            db_size=db_size_formatted,
            last_archive=last_archive
        )
        
        await update.message.reply_text(message)
        
        logger.info(f"Stats command executed")
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /language command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # Create language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("English", callback_data="lang_en"),
                InlineKeyboardButton("简体中文", callback_data="lang_zh-CN"),
            ],
            [
                InlineKeyboardButton("繁體中文", callback_data="lang_zh-TW"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            i18n.t('language_select'),
            reply_markup=reply_markup
        )
        
        logger.info(f"Language command executed")
        
    except Exception as e:
        logger.error(f"Error in language_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ai command - 显示AI功能状态
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        config = get_config()
        ai_config = config.ai
        
        status_text = "🤖 *AI功能状态*\n\n"
        
        # 检查是否启用
        if ai_config.get('enabled', False):
            status_text += "✅ 状态: 已启用\n"
            
            # 获取AI总结器
            summarizer = get_ai_summarizer(ai_config)
            
            if summarizer and summarizer.is_available():
                status_text += "✅ 服务: 可用\n\n"
                
                api_config = ai_config.get('api', {})
                provider = api_config.get('provider', 'unknown')
                model = api_config.get('model', 'unknown')
                
                status_text += f"🔧 *配置信息*\n"
                status_text += f"提供商: {provider}\n"
                status_text += f"模型: {model}\n"
                status_text += f"最大令牌: {api_config.get('max_tokens', 1000)}\n"
                status_text += f"超时时间: {api_config.get('timeout', 30)}秒\n\n"
                
                status_text += f"🎯 *功能开关*\n"
                status_text += f"自动总结: {'✅' if ai_config.get('auto_summarize') else '❌'}\n"
                status_text += f"自动标签: {'✅' if ai_config.get('auto_generate_tags') else '❌'}"
            else:
                status_text += "⚠️ 服务: 不可用\n"
                status_text += "请检查API密钥配置是否正确"
        else:
            status_text += "❌ 状态: 未启用\n\n"
            status_text += "💡 *如何启用*\n"
            status_text += "1. 编辑 config/config.yaml\n"
            status_text += "2. 设置 ai.enabled: true\n"
            status_text += "3. 配置 ai.api.provider 和 ai.api.api_key\n"
            status_text += "4. 重启机器人\n\n"
            status_text += "支持的提供商：OpenAI, Claude, Qwen"
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"AI status command executed")
        
    except Exception as e:
        logger.error(f"Error in ai_status_command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 错误：{str(e)}")

