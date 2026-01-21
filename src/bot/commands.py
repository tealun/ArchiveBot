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
        
        # Perform search
        search_result = search_engine.search(query, limit=10)
        
        # Format and send results
        result_text = search_engine.format_results(search_result)
        
        await processing_msg.edit_text(result_text)
        
        logger.info(f"Search command: query='{query}', results={search_result.get('count', 0)}")
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tags command
    
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
        
        # Get all tags
        tags = tag_manager.get_all_tags(limit=50)
        
        if not tags:
            await update.message.reply_text(i18n.t('tags_empty'))
            return
        
        # Format tags
        tag_lines = []
        for tag in tags:
            tag_name = tag.get('tag_name')
            count = tag.get('count', 0)
            tag_lines.append(f"#{tag_name} ({count})")
        
        tags_text = '\n'.join(tag_lines)
        
        message = i18n.t('tags_list', count=len(tags), tags=tags_text)
        
        await update.message.reply_text(message)
        
        logger.info(f"Tags command executed: {len(tags)} tags")
        
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
        
        # Format stats
        total_archives = stats.get('total_archives', 0)
        total_tags = stats.get('total_tags', 0)
        total_size = format_file_size(stats.get('total_size', 0))
        last_archive = stats.get('last_archive', 'N/A')
        
        message = i18n.t(
            'stats',
            total_archives=total_archives,
            total_tags=total_tags,
            storage_used=total_size,
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


async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /summarize command - AI总结最近归档内容
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        config = get_config()
        
        # 检查AI是否启用
        if not config.ai.get('enabled', False):
            await update.message.reply_text("⚠️ AI功能未启用\n\n请在配置文件中启用AI功能并配置API密钥。")
            return
        
        # 获取AI总结器
        summarizer = get_ai_summarizer(config.ai)
        
        if not summarizer or not summarizer.is_available():
            await update.message.reply_text("⚠️ AI服务不可用\n\n请检查API配置是否正确。")
            return
        
        # 获取要总结的归档ID（从回复消息或参数）
        archive_id = None
        if update.message.reply_to_message:
            # 从回复消息的文本中提取ID
            reply_text = update.message.reply_to_message.text or ""
            import re
            match = re.search(r'ID[：:]\s*(\d+)', reply_text)
            if match:
                archive_id = int(match.group(1))
        elif context.args:
            try:
                archive_id = int(context.args[0])
            except ValueError:
                pass
        
        if not archive_id:
            await update.message.reply_text(
                "📝 使用方法：\n\n"
                "1. 回复一条归档消息，然后发送 /summarize\n"
                "2. 或者使用 /summarize <归档ID>"
            )
            return
        
        # 发送处理中消息
        processing_msg = await update.message.reply_text("🤖 AI正在分析中...")
        
        # 从数据库获取归档内容
        db: DatabaseStorage = context.bot_data.get('database')
        archive = db.get_archive(archive_id)
        
        if not archive:
            await processing_msg.edit_text(f"❌ 未找到归档 #{archive_id}")
            return
        
        # 准备内容
        content = archive.get('content', '') or ''
        if archive.get('link_metadata'):
            metadata = archive['link_metadata']
            content = f"{metadata.get('title', '')}\n\n{metadata.get('description', '')}\n\n{content}"
        
        if not content.strip():
            await processing_msg.edit_text("❌ 归档内容为空，无法生成摘要")
            return
        
        # 生成AI摘要
        result = await summarizer.summarize_content(content, archive.get('url'))
        
        if not result.get('success'):
            error_msg = result.get('error', '未知错误')
            await processing_msg.edit_text(f"❌ AI总结失败：{error_msg}")
            return
        
        # 格式化并显示结果
        provider = result.get('provider', 'AI').upper()
        summary_text = f"🤖 *AI总结* (by {provider})\n\n"
        summary_text += f"📋 *核心观点*\n{result.get('summary', '无')}\n\n"
        
        if result.get('key_points'):
            summary_text += "🔑 *关键要点*\n"
            for i, point in enumerate(result['key_points'], 1):
                summary_text += f"{i}. {point}\n"
            summary_text += "\n"
        
        if result.get('suggested_tags'):
            tags = ', '.join(f"#{tag}" for tag in result['suggested_tags'])
            summary_text += f"🏷️ *建议标签*\n{tags}\n\n"
        
        if result.get('category'):
            summary_text += f"📁 *分类*\n{result['category']}\n\n"
        
        summary_text += f"📎 原归档: #{archive_id}"
        
        await processing_msg.edit_text(
            summary_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"AI summary generated for archive #{archive_id}")
        
    except Exception as e:
        logger.error(f"Error in summarize_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ 错误：{str(e)}")
        except:
            pass


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
                status_text += f"自动标签: {'✅' if ai_config.get('auto_generate_tags') else '❌'}\n\n"
                
                status_text += "📝 *可用命令*\n"
                status_text += "/summarize - 生成AI摘要\n"
                status_text += "/ai - 查看状态"
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

