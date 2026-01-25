"""
Bot commands implementation
Handles /start, /help, /search, /tags, /stats, /language
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.language_context import with_language_context
from ..utils.config import get_config
from ..utils.helpers import format_file_size
from ..core.search_engine import SearchEngine
from ..core.tag_manager import TagManager
from ..storage.database import DatabaseStorage
from ..ai.summarizer import get_ai_summarizer

logger = logging.getLogger(__name__)


@with_language_context
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /start command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        config = get_config()
        
        welcome_msg = lang_ctx.t('welcome')
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.HTML)
        
        logger.info(f"Start command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


@with_language_context
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /help command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        help_msg = lang_ctx.t('help')
        
        await update.message.reply_text(
            help_msg,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Help command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


@with_language_context
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /search command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # Get search query
        query = ' '.join(context.args) if context.args else None
        
        if not query:
            await update.message.reply_text(lang_ctx.t('search_no_keyword'))
            return
        
        # Get search engine from context
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        
        if not search_engine:
            await update.message.reply_text(lang_ctx.t('error_search_engine_not_initialized'))
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(lang_ctx.t('processing'))
        
        # Perform search with pagination
        page_size = 10
        page = 0  # First page
        offset = page * page_size
        search_result = search_engine.search(query, limit=page_size, offset=offset)
        
        # Get total count for pagination
        total_count = search_result.get('total_count', 0)
        
        # Get database instance for checking status
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        
        # Format and send results (with HTML links and per-item keyboards)
        result_text, keyboards_per_item = search_engine.format_results(
            search_result, 
            with_links=True,
            db_instance=db
        )
        
        # Build final keyboard: only pagination buttons (no per-item buttons)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from urllib.parse import quote
        
        keyboard = []
        
        # 分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages > 1:
            nav_row = []
            encoded_query = quote(query)
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"search_page:{encoded_query}:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="search_noop"
            ))
            
            if (page + 1) * page_size < total_count:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"search_page:{encoded_query}:{page+1}"
                ))
            
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
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /tags command - 显示标签按钮矩阵
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        tag_manager: TagManager = context.bot_data.get('tag_manager')
        
        if not tag_manager:
            await update.message.reply_text(lang_ctx.t('error_tag_manager_not_initialized'))
            return
        
        # Get all tags (sorted by count descending)
        tags = tag_manager.get_all_tags(limit=100)
        
        if not tags:
            await update.message.reply_text(lang_ctx.t('tags_empty'))
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
        
        message = lang_ctx.t('tags_button_list_header', count=len(tags))
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
        logger.info(f"Tags command executed: {len(tags)} tags, page {page}")
        
    except Exception as e:
        logger.error(f"Error in tags_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /stats command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        db_storage: DatabaseStorage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await update.message.reply_text(lang_ctx.t('error_database_not_initialized'))
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
        
        message = lang_ctx.t(
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
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /language command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # Get current language name
        current_lang_key = f"language_name_{lang_ctx.language}"
        current_language = lang_ctx.t(current_lang_key)
        
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
            lang_ctx.t('language_select', current_language=current_language),
            reply_markup=reply_markup
        )
        
        logger.info(f"Language command executed")
        
    except Exception as e:
        logger.error(f"Error in language_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


@with_language_context
async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /ai command - 显示AI功能状态
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        config = get_config()
        ai_config = config.ai
        
        status_text = "🤖 **AI 功能状态**\n\n"
        
        # 检查是否启用
        if ai_config.get('enabled', False):
            status_text += "✅ **状态：** 已启用\n\n"
            
            # 获取AI总结器
            summarizer = get_ai_summarizer(ai_config)
            
            if summarizer and summarizer.is_available():
                status_text += "🟢 **服务：** 可用\n\n"
                
                # API配置信息
                api_config = ai_config.get('api', {})
                provider = api_config.get('provider', 'unknown')
                model = api_config.get('model', 'unknown')
                base_url = api_config.get('base_url', 'default')
                
                # 脱敏处理API Key
                api_key = api_config.get('api_key', '')
                if api_key:
                    if len(api_key) > 10:
                        masked_key = api_key[:4] + '****' + api_key[-4:]
                    else:
                        masked_key = '****'
                else:
                    masked_key = '未设置'
                
                status_text += "⚙️ **配置信息：**\n"
                status_text += f"  • 提供商：`{provider}`\n"
                status_text += f"  • 模型：`{model}`\n"
                status_text += f"  • API Key：`{masked_key}`\n"
                status_text += f"  • Base URL：`{base_url}`\n"
                status_text += f"  • 最大Token：`{api_config.get('max_tokens', 1000)}`\n"
                status_text += f"  • 超时时间：`{api_config.get('timeout', 30)}秒`\n"
                status_text += f"  • 温度参数：`{api_config.get('temperature', 0.7)}`\n\n"
                
                # 功能开关
                status_text += "🔧 **功能开关：**\n"
                auto_summarize = ai_config.get('auto_summarize', False)
                auto_tags = ai_config.get('auto_generate_tags', False)
                auto_category = ai_config.get('auto_category', False)
                chat_enabled = ai_config.get('chat', {}).get('enabled', False)
                
                status_text += f"  • 自动摘要：{'✅ 开启' if auto_summarize else '❌ 关闭'}\n"
                status_text += f"  • 自动标签：{'✅ 开启' if auto_tags else '❌ 关闭'}\n"
                status_text += f"  • 自动分类：{'✅ 开启' if auto_category else '❌ 关闭'}\n"
                status_text += f"  • 智能对话：{'✅ 开启' if chat_enabled else '❌ 关闭'}\n\n"
                
                # 使用统计（从数据库获取）
                db_storage = context.bot_data.get('db_storage')
                if db_storage:
                    try:
                        cursor = db_storage.db.execute("""
                            SELECT 
                                COUNT(*) as total,
                                COUNT(CASE WHEN ai_summary IS NOT NULL THEN 1 END) as with_summary,
                                COUNT(CASE WHEN ai_tags IS NOT NULL THEN 1 END) as with_tags,
                                COUNT(CASE WHEN ai_category IS NOT NULL THEN 1 END) as with_category
                            FROM archives
                            WHERE deleted = 0
                        """)
                        stats = cursor.fetchone()
                        
                        total = stats[0]
                        with_summary = stats[1]
                        with_tags = stats[2]
                        with_category = stats[3]
                        
                        status_text += "📊 **使用统计：**\n"
                        status_text += f"  • 总归档数：`{total}`\n"
                        status_text += f"  • AI摘要：`{with_summary}` ({int(with_summary/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI标签：`{with_tags}` ({int(with_tags/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI分类：`{with_category}` ({int(with_category/total*100) if total > 0 else 0}%)\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to get AI usage stats: {e}")
                        status_text += "📊 **使用统计：** 无法获取\n\n"
                
                # 对话会话信息
                if chat_enabled:
                    session_manager = context.bot_data.get('session_manager')
                    if session_manager:
                        user_id = update.effective_user.id
                        session = session_manager.get_session(user_id)
                        if session:
                            status_text += "💬 **对话会话：**\n"
                            status_text += f"  • 状态：活跃\n"
                            status_text += f"  • 消息数：`{session.get('message_count', 0)}`\n"
                            last_time = session.get('last_interaction')
                            if last_time:
                                status_text += f"  • 最后交互：`{last_time}`\n"
                        else:
                            status_text += "💬 **对话会话：** 无活跃会话\n"
                        status_text += "\n"
                
                # 缓存信息
                ai_cache = context.bot_data.get('ai_cache')
                if ai_cache:
                    try:
                        cache_stats = ai_cache.get_stats()
                        status_text += "💾 **缓存统计：**\n"
                        status_text += f"  • 缓存条目：`{cache_stats.get('total_entries', 0)}`\n"
                        status_text += f"  • 命中率：`{cache_stats.get('hit_rate', 0):.1f}%`\n"
                        status_text += f"  • 缓存大小：`{cache_stats.get('size_mb', 0):.2f} MB`\n"
                    except Exception as e:
                        logger.warning(f"Failed to get cache stats: {e}")
                
            else:
                status_text += "🔴 **服务：** 不可用\n\n"
                status_text += "⚠️ AI服务连接失败，请检查配置\n"
        else:
            status_text += "❌ **状态：** 未启用\n\n"
            status_text += "💡 **启用指南：**\n"
            status_text += "1. 编辑 `config/config.yaml`\n"
            status_text += "2. 设置 `ai.enabled: true`\n"
            status_text += "3. 配置API密钥和提供商\n"
            status_text += "4. 重启Bot\n"
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"AI status command executed")
        
    except Exception as e:
        logger.error(f"Error in ai_status_command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 获取AI状态失败: {str(e)}")


@with_language_context
async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /note command - 进入笔记模式
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 检查是否已经在笔记模式中
        if context.user_data.get('note_mode'):
            await update.message.reply_text(
                "⚠️ 您已经在笔记模式中\n"
                "发送 /cancel 可以退出并保存当前笔记"
            )
            return
        
        # 进入笔记模式
        context.user_data['note_mode'] = True
        context.user_data['note_messages'] = []  # 收集的消息
        context.user_data['note_archives'] = []  # 归档的媒体ID
        context.user_data['note_start_time'] = update.message.date
        
        # 设置15分钟后的超时任务
        # 移除之前的超时任务（如果有）
        if 'note_timeout_job' in context.user_data:
            try:
                context.user_data['note_timeout_job'].schedule_removal()
            except:
                pass
        
        # 创建新的超时任务
        from datetime import timedelta
        # 导入handlers中的note_timeout_callback
        from ..bot.handlers import note_timeout_callback
        
        job = context.job_queue.run_once(
            note_timeout_callback,
            when=timedelta(minutes=15),
            data={
                'chat_id': update.effective_chat.id,
                'user_id': update.effective_user.id
            },
            name=f"note_timeout_{update.effective_user.id}"
        )
        context.user_data['note_timeout_job'] = job
        
        await update.message.reply_text(
            "📝 已进入笔记模式\n\n"
            "💬 现在发送的所有消息都会被记录为笔记\n"
            "📎 发送的媒体文件会自动归档并关联到笔记\n\n"
            "⏱️ 15分钟内无新消息将自动生成笔记\n"
            "🚫 发送 /cancel 可立即退出并保存笔记"
        )
        
        logger.info(f"User {update.effective_user.id} entered note mode")
        
    except Exception as e:
        logger.error(f"Error in note_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /cancel command - 退出笔记模式
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 检查是否在笔记模式中
        if not context.user_data.get('note_mode'):
            await update.message.reply_text(
                "⚠️ 您当前不在笔记模式中\n"
                "发送 /note 可以进入笔记模式"
            )
            return
        
        # 导入handlers中的_finalize_note_internal
        from ..bot.handlers import _finalize_note_internal
        
        # 立即生成并保存笔记
        await _finalize_note_internal(context, update.effective_chat.id, reason="manual")
        
        logger.info(f"User {update.effective_user.id} cancelled note mode")
        
    except Exception as e:
        logger.error(f"Error in cancel_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /notes command - 显示所有笔记列表
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 获取note_manager和config
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await update.message.reply_text(lang_ctx.t('note_manager_not_initialized'))
            return
        
        # 获取所有笔记（分页显示）
        page = 0
        page_size = 10
        results = note_manager.get_all_notes(limit=page_size, offset=page * page_size)
        
        if not results:
            await update.message.reply_text(lang_ctx.t('notes_list_empty'))
            return
        
        # 获取配置
        config = get_config()
        
        # 构建输出
        from ..utils.helpers import truncate_text
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        result_text = lang_ctx.t('notes_list_header', count=len(results)) + "\n\n"
        
        keyboard = []
        for idx, note in enumerate(results, 1):
            note_id = note['id']
            created_at = note['created_at']
            content = note['content']
            archive_id = note.get('archive_id')
            
            # 第一行：笔记ID和时间
            result_text += f"📝 笔记ID: #{note_id} | 📅 {created_at}\n"
            
            # 第二行：标题（内容预览）
            content_preview = truncate_text(content, 60)
            note_type = "[自动]" if archive_id else "[手动]"
            result_text += f"💬 {note_type} {content_preview}\n"
            
            # 第三行：所属归档
            if archive_id:
                archive_title = note.get('archive_title', f'归档 #{archive_id}')
                storage_path = note.get('storage_path')
                storage_type = note.get('storage_type')
                
                # 生成跳转链接
                if storage_path and storage_type == 'telegram':
                    parts = storage_path.split(':')
                    if len(parts) >= 2:
                        channel_id = parts[0].replace('-100', '')
                        message_id = parts[1]
                    else:
                        channel_id = str(config.telegram_channel_id).replace('-100', '')
                        message_id = storage_path
                    
                    link = f"https://t.me/c/{channel_id}/{message_id}"
                    result_text += f"📎 所属归档：<a href='{link}'>{archive_title}</a>\n"
                else:
                    result_text += f"📎 所属归档：{archive_title}\n"
            else:
                result_text += f"📎 独立笔记\n"
            
            result_text += "\n"
            
            # 添加查看按钮
            keyboard.append([
                InlineKeyboardButton(
                    f"{idx}. 查看详情",
                    callback_data=f"note_view:{note_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            result_text, 
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        logger.info(f"Notes list command executed")
        
    except Exception as e:
        logger.error(f"Error in notes_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def trash_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /trash command - 管理垃圾箱
    
    Usage:
        /trash - 查看垃圾箱
        /trash restore <id> - 恢复归档
        /trash delete <id> - 永久删除
        /trash empty - 清空垃圾箱
        /trash empty <days> - 清空N天前的归档
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await update.message.reply_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 解析子命令
        if not context.args:
            # 查看垃圾箱
            items = trash_manager.list_trash()
            count = len(items)
            
            if count == 0:
                await update.message.reply_text(lang_ctx.t('trash_empty'))
                return
            
            result_text = lang_ctx.t('trash_list', count=count) + "\n\n"
            
            for item in items[:20]:  # 只显示前20条
                result_text += f"🗑️ ID: #{item['id']}\n"
                result_text += f"📝 {item['title']}\n"
                result_text += f"🏷️ {', '.join(item['tags'][:3])}{'...' if len(item['tags']) > 3 else ''}\n"
                result_text += f"🕐 {lang_ctx.t('deleted_at')}: {item['deleted_at']}\n\n"
            
            if count > 20:
                result_text += lang_ctx.t('trash_more', count=count-20)
            
            await update.message.reply_text(result_text)
            
        elif context.args[0] == 'restore':
            # 恢复归档
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('trash_restore_usage'))
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(lang_ctx.t('invalid_archive_id'))
                return
            
            if trash_manager.restore_archive(archive_id):
                await update.message.reply_text(lang_ctx.t('trash_restore_success', archive_id=archive_id))
            else:
                await update.message.reply_text(lang_ctx.t('trash_restore_failed', archive_id=archive_id))
        
        elif context.args[0] == 'delete':
            # 永久删除
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('trash_delete_usage'))
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(lang_ctx.t('invalid_archive_id'))
                return
            
            if trash_manager.delete_permanently(archive_id):
                await update.message.reply_text(lang_ctx.t('trash_delete_success', archive_id=archive_id))
            else:
                await update.message.reply_text(lang_ctx.t('trash_delete_failed', archive_id=archive_id))
        
        elif context.args[0] == 'empty':
            # 清空垃圾箱
            days_old = None
            if len(context.args) > 1:
                try:
                    days_old = int(context.args[1])
                except ValueError:
                    await update.message.reply_text(lang_ctx.t('invalid_days'))
                    return
            
            count = trash_manager.empty_trash(days_old)
            
            if days_old:
                await update.message.reply_text(lang_ctx.t('trash_empty_success_days', count=count, days=days_old))
            else:
                await update.message.reply_text(lang_ctx.t('trash_empty_success', count=count))
        
        else:
            await update.message.reply_text(lang_ctx.t('trash_invalid_command'))
        
        logger.info(f"Trash command executed: {' '.join(context.args) if context.args else 'list'}")
        
    except Exception as e:
        logger.error(f"Error in trash_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /export command - 导出数据
    
    Usage:
        /export - 导出为Markdown
        /export json - 导出为JSON
        /export csv - 导出为CSV
        /export tag <tag_name> [format] - 按标签导出
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 获取export_manager
        export_manager = context.bot_data.get('export_manager')
        if not export_manager:
            await update.message.reply_text(lang_ctx.t('export_manager_not_initialized'))
            return
        
        # 发送处理中提示
        processing_msg = await update.message.reply_text(lang_ctx.t('export_processing'))
        
        # 解析命令参数
        format_type = 'markdown'  # 默认格式
        tag_name = None
        
        if context.args:
            if context.args[0] == 'tag':
                # 按标签导出
                if len(context.args) < 2:
                    await processing_msg.edit_text(lang_ctx.t('export_tag_usage'))
                    return
                tag_name = context.args[1]
                format_type = context.args[2] if len(context.args) > 2 else 'markdown'
            else:
                # 指定格式
                format_type = context.args[0].lower()
        
        # 验证格式
        if format_type not in ['markdown', 'json', 'csv', 'md']:
            await processing_msg.edit_text(lang_ctx.t('export_invalid_format'))
            return
        
        # 导出数据
        if tag_name:
            # 按标签导出
            data = export_manager.export_archives_by_tag(tag_name, format_type)
            filename = f"archives_tag_{tag_name}"
        else:
            # 全量导出
            if format_type in ['markdown', 'md']:
                data = export_manager.export_to_markdown()
                format_type = 'markdown'
            elif format_type == 'json':
                data = export_manager.export_to_json()
            else:  # csv
                data = export_manager.export_to_csv()
            
            filename = "archives_export"
        
        if not data:
            await processing_msg.edit_text(lang_ctx.t('export_failed'))
            return
        
        # 确定文件扩展名
        if format_type in ['markdown', 'md']:
            ext = 'md'
        elif format_type == 'json':
            ext = 'json'
        else:
            ext = 'csv'
        
        # 生成文件名（带时间戳）
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        full_filename = f"{filename}_{timestamp}.{ext}"
        
        # 发送文件
        from io import BytesIO
        file_data = BytesIO(data.encode('utf-8'))
        file_data.name = full_filename
        
        await update.message.reply_document(
            document=file_data,
            filename=full_filename,
            caption=lang_ctx.t('export_success', filename=full_filename, size=len(data))
        )
        
        # 删除处理中提示
        await processing_msg.delete()
        
        logger.info(f"Export command executed: format={format_type}, tag={tag_name}, size={len(data)}")
        
    except Exception as e:
        logger.error(f"Error in export_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
        except:
            pass


@with_language_context
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /backup command - 备份与恢复
    
    Usage:
        /backup              - 查看备份列表
        /backup create [desc]- 创建备份，可附描述
        /backup restore <file> - 从备份恢复
        /backup delete <file>  - 删除备份
        /backup cleanup [keep] - 只保留最近N个（默认10）
        /backup status       - 查看数据库状态
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        backup_manager = context.bot_data.get('backup_manager')

        if not backup_manager:
            await update.message.reply_text(lang_ctx.t('backup_manager_not_initialized'))
            return

        # 无参数 -> 列表
        if not context.args:
            backups = backup_manager.list_backups()
            if not backups:
                await update.message.reply_text(lang_ctx.t('backup_none'))
                return

            lines = [lang_ctx.t('backup_list_header', count=len(backups))]
            for b in backups[:10]:
                lines.append(lang_ctx.t(
                    'backup_list_item',
                    filename=b.get('filename'),
                    created_at=b.get('created_at'),
                    size=b.get('size'),
                    description=b.get('description', '')
                ))
            if len(backups) > 10:
                lines.append(lang_ctx.t('backup_list_more', count=len(backups) - 10))

            # 添加操作按钮
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton(
                        "💾 保留1份",
                        callback_data="backup_keep:1"
                    ),
                    InlineKeyboardButton(
                        "💾 保留3份",
                        callback_data="backup_keep:3"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🗑️ 全部删除",
                        callback_data="backup_delete_all"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                '\n'.join(lines),
                reply_markup=reply_markup
            )
            return

        subcmd = context.args[0].lower()

        if subcmd == 'create':
            desc = ' '.join(context.args[1:]) if len(context.args) > 1 else ''
            result = backup_manager.create_backup(description=desc)
            if result:
                await update.message.reply_text(lang_ctx.t('backup_created', filename=result))
            else:
                await update.message.reply_text(lang_ctx.t('backup_create_failed'))
            return

        if subcmd == 'restore':
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('backup_restore_usage'))
                return
            filename = context.args[1]
            ok = backup_manager.restore_backup(filename)
            if ok:
                await update.message.reply_text(lang_ctx.t('backup_restored', filename=filename))
            else:
                await update.message.reply_text(lang_ctx.t('backup_restore_failed', filename=filename))
            return

        if subcmd == 'delete':
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('backup_delete_usage'))
                return
            filename = context.args[1]
            ok = backup_manager.delete_backup(filename)
            if ok:
                await update.message.reply_text(lang_ctx.t('backup_deleted', filename=filename))
            else:
                await update.message.reply_text(lang_ctx.t('backup_delete_failed', filename=filename))
            return

        if subcmd == 'cleanup':
            keep = 10
            if len(context.args) > 1:
                try:
                    keep = int(context.args[1])
                except ValueError:
                    await update.message.reply_text(lang_ctx.t('backup_invalid_keep'))
                    return
            deleted = backup_manager.cleanup_old_backups(keep_count=keep)
            await update.message.reply_text(lang_ctx.t('backup_cleanup_done', deleted=deleted, keep=keep))
            return

        if subcmd == 'status':
            stats = backup_manager.get_database_stats()
            if not stats:
                await update.message.reply_text(lang_ctx.t('backup_status_failed'))
                return
            msg = lang_ctx.t(
                'backup_status',
                size=stats.get('size', 0),
                archives=stats.get('archives_count', 0),
                notes=stats.get('notes_count', 0),
                deleted=stats.get('deleted_count', 0),
                last=stats.get('last_archive', 'N/A')
            )
            await update.message.reply_text(msg)
            return

        # 未知子命令
        await update.message.reply_text(lang_ctx.t('backup_invalid_command'))

    except Exception as e:
        logger.error(f"Error in backup_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))


@with_language_context
async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /review command - 活动回顾与统计
    
    Usage:
        /review              - 显示期间选择按钮
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        review_manager = context.bot_data.get('review_manager')

        if not review_manager:
            await update.message.reply_text(lang_ctx.t('review_manager_not_initialized'))
            return

        # 显示期间选择按钮
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📅 {lang_ctx.t('review_period_week')}",
                    callback_data='review:week'
                ),
                InlineKeyboardButton(
                    f"📅 {lang_ctx.t('review_period_month')}",
                    callback_data='review:month'
                )
            ],
            [
                InlineKeyboardButton(
                    f"📅 {lang_ctx.t('review_period_year')}",
                    callback_data='review:year'
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            lang_ctx.t('review_usage'),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in review_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
