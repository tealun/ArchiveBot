"""
Search callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.search_engine import SearchEngine
from ...utils.helpers import truncate_text

@with_language_context
async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
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
        
        # 获取数据库实例
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        
        # Format results (第二个返回值现在是空列表)
        result_text, _ = search_engine.format_results(search_result, with_links=True, db_instance=db)
        
        # Build keyboard: 只包含分页按钮（状态信息已内联在文本中）
        keyboard = []
        
        # 分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages > 1:
            nav_row = []
            
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
