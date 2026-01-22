"""
Callback query handlers
Handles button clicks and inline keyboard callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.i18n import get_i18n
from ..utils.config import get_config
from ..core.tag_manager import TagManager
from ..core.search_engine import SearchEngine
from ..utils.helpers import truncate_text, format_datetime, get_content_type_emoji

logger = logging.getLogger(__name__)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    统一处理所有callback query
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # 路由到具体处理函数
        if callback_data.startswith('lang_'):
            await handle_language_callback(update, context)
        elif callback_data.startswith('tag:'):
            await handle_tag_callback(update, context)
        elif callback_data.startswith('tags_page:'):
            await handle_tags_page_callback(update, context)
        elif callback_data == 'tags_noop':
            # 不做任何操作（页码显示按钮）
            pass
        elif callback_data.startswith('tag_list:'):
            await handle_tag_list_page_callback(update, context)
        elif callback_data.startswith('search_page:'):
            await handle_search_page_callback(update, context)
        elif callback_data == 'search_noop':
            # 不做任何操作（页码显示按钮）
            pass
        elif callback_data.startswith('ai_view:'):
            await handle_ai_view_callback(update, context)
        else:
            logger.warning(f"Unknown callback_data: {callback_data}")
    
    except Exception as e:
        logger.error(f"Error handling callback query: {e}", exc_info=True)


async def handle_tag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理标签点击 - 显示该标签的内容列表
    
    Callback data format: tag:标签名:页码
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析: tag:tag_name:page
        parts = callback_data.split(':', 2)
        tag_name = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
        
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        if not search_engine:
            await query.edit_message_text("Search engine not initialized")
            return
        
        # 搜索该标签的内容
        page_size = 10
        search_result = search_engine.search(
            f"#{tag_name}",
            limit=page_size,
            offset=page * page_size
        )
        
        if search_result.get('count', 0) == 0:
            await query.edit_message_text(f"标签 #{tag_name} 下暂无内容")
            return
        
        # 格式化结果列表
        formatted_results = []
        for idx, archive in enumerate(search_result.get('results', []), page * page_size + 1):
            emoji = get_content_type_emoji(archive.get('content_type', ''))
            title = archive.get('title', 'Untitled')
            title_truncated = truncate_text(title, 40)
            
            # 构建跳转链接
            storage_path = archive.get('storage_path')
            if storage_path:
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    channel_id = parts[0].replace('-100', '')
                    message_id = parts[1]
                    link = f"https://t.me/c/{channel_id}/{message_id}"
                    title_truncated = f"<a href='{link}'>{title_truncated}</a>"
            
            content_type = archive.get('content_type', '')
            archived_at = format_datetime(archive.get('archived_at', ''))
            
            result_text = f"{idx}. {emoji} {title_truncated}\n   📅 {archived_at}"
            formatted_results.append(result_text)
        
        results_text = '\n\n'.join(formatted_results)
        
        # 获取总数（需要再次查询或从数据库获取）
        # 这里简化处理，假设有更多数据
        has_more = search_result.get('count', 0) == page_size
        
        message = f"🏷️ 标签: #{tag_name}\n\n{results_text}"
        
        # 构建分页按钮
        keyboard = []
        nav_row = []
        
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"tag:{tag_name}:{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"📄 {page+1}", callback_data="tags_noop"))
        
        if has_more:
            nav_row.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"tag:{tag_name}:{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        # 返回按钮
        keyboard.append([InlineKeyboardButton("🔙 返回标签列表", callback_data="tags_page:0")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error handling tag callback: {e}", exc_info=True)


async def handle_tags_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理标签列表分页
    
    Callback data format: tags_page:页码
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析页码
        page = int(callback_data.split(':')[1])
        
        tag_manager: TagManager = context.bot_data.get('tag_manager')
        if not tag_manager:
            await query.edit_message_text("Tag manager not initialized")
            return
        
        # 获取所有标签
        tags = tag_manager.get_all_tags(limit=100)
        
        if not tags:
            await query.edit_message_text("暂无标签")
            return
        
        # 构建按钮矩阵
        page_size = 30
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_tags = tags[start_idx:end_idx]
        
        keyboard = []
        row = []
        for i, tag in enumerate(page_tags):
            tag_name = tag.get('tag_name')
            count = tag.get('count', 0)
            
            button_text = f"#{tag_name} ({count})"
            callback_data = f"tag:{tag_name}:0"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        # 分页按钮
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
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error handling tags page callback: {e}", exc_info=True)


async def handle_tag_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle tag list pagination
    
    Callback data format: tag_list:page
    """
    await handle_tags_page_callback(update, context)


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle language selection callback
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        callback_data = query.data
        
        if callback_data.startswith('lang_'):
            language = callback_data[5:]  # Remove 'lang_' prefix
            
            # Set language
            i18n = get_i18n()
            if i18n.set_language(language):
                # Save to config
                config = get_config()
                config.set('bot.language', language)
                config.save()
                
                # Send confirmation
                await query.edit_message_text(i18n.t('language_changed'))
                
                logger.info(f"Language changed to: {language}")
            else:
                await query.edit_message_text(f"Unsupported language: {language}")
        
    except Exception as e:
        logger.error(f"Error handling language callback: {e}", exc_info=True)
        try:
            await query.edit_message_text(f"Error: {e}")
        except:
            pass


async def handle_tag_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle tag list pagination
    
    Callback data format: tag_list:page
    """
    await handle_tags_page_callback(update, context)


async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理搜索结果分页
    
    Callback data format: search_page:encoded_query:page
    """
    from ..core.search_engine import SearchEngine
    from ..utils.helpers import truncate_text
    from urllib.parse import unquote, quote
    from telegram.constants import ParseMode
    
    query = update.callback_query
    
    try:
        # 解析 callback data: search_page:encoded_query:page
        parts = query.data.split(':', 2)
        if len(parts) != 3:
            await query.answer("Invalid callback data", show_alert=True)
            return
        
        encoded_query = parts[1]
        page = int(parts[2])
        search_query = unquote(encoded_query)
        
        # Get search engine
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        if not search_engine:
            await query.answer("Search engine not initialized", show_alert=True)
            return
        
        # Perform search
        page_size = 10
        offset = page * page_size
        search_result = search_engine.search(search_query, limit=page_size, offset=offset)
        
        # Get total count
        total_count = search_result.get('total_count', 0)
        
        # Format results
        result_text, results_with_ai = search_engine.format_results(search_result, with_links=True)
        
        # Build keyboard
        keyboard = []
        
        # AI解析按钮
        if results_with_ai:
            for item in results_with_ai:
                # 计算全局索引（考虑分页偏移）
                global_index = offset + item['index']
                title_preview = truncate_text(item['title'], 12)
                button_text = f"🤖 #{global_index}《{title_preview}》"
                callback_data = f"ai_view:{item['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # 分页按钮
        if total_count > page_size:
            nav_row = []
            total_pages = (total_count + page_size - 1) // page_size
            
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"search_page:{encoded_query}:{page-1}"))
            
            nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="search_noop"))
            
            if (page + 1) * page_size < total_count:
                nav_row.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"search_page:{encoded_query}:{page+1}"))
            
            if nav_row:
                keyboard.append(nav_row)
        
        # 更新消息
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await query.answer()
        await query.edit_message_text(
            result_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        
        logger.info(f"Search page callback: query='{search_query}', page={page}")
        
    except Exception as e:
        logger.error(f"Error handling search page callback: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def handle_ai_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle AI analysis view callback
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # Parse callback data: ai_view:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # Get database storage
        from ..storage.database import DatabaseStorage
        db_storage: DatabaseStorage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await query.answer("Database not available", show_alert=True)
            return
        
        # Get archive
        archive = db_storage.get_archive(archive_id)
        
        if not archive:
            await query.answer("Archive not found", show_alert=True)
            return
        
        # Get AI data
        ai_summary = archive.get('ai_summary', '')
        ai_key_points_json = archive.get('ai_key_points', '')
        ai_category = archive.get('ai_category', '')
        
        # Parse key points JSON
        ai_key_points = []
        if ai_key_points_json:
            try:
                import json
                ai_key_points = json.loads(ai_key_points_json)
            except:
                pass
        
        # Build AI analysis message
        title = archive.get('title', 'Untitled')
        ai_msg = f"📚 <b>{title}</b>\n\n🤖 <b>AI智能分析：</b>\n"
        
        if ai_category:
            ai_msg += f"\n📁 <b>分类：</b>{ai_category}"
        
        if ai_summary:
            ai_msg += f"\n\n📝 <b>摘要：</b>{ai_summary}"
        
        if ai_key_points:
            ai_msg += "\n\n🔑 <b>关键点：</b>"
            for i, point in enumerate(ai_key_points[:3], 1):
                ai_msg += f"\n  {i}. {point}"
        
        if not (ai_summary or ai_key_points or ai_category):
            ai_msg = "该归档暂无AI分析数据"
        
        # Send as new message
        await query.answer()
        await query.message.reply_text(ai_msg, parse_mode=ParseMode.HTML)
        
        logger.info(f"AI view callback: archive_id={archive_id}")
        
    except Exception as e:
        logger.error(f"Error in AI view callback: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)}", show_alert=True)
