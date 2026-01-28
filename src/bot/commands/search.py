"""
Search commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config
from ...utils.helpers import send_or_update_reply
from .note_mode_interceptor import intercept_in_note_mode

logger = logging.getLogger(__name__)

from ...core.search_engine import SearchEngine
from ...utils.helpers import format_file_size

@intercept_in_note_mode
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
            await send_or_update_reply(update, context, lang_ctx.t('search_no_keyword'), 'search')
            return
        
        # Get search engine from context
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        
        if not search_engine:
            await send_or_update_reply(update, context, lang_ctx.t('error_search_engine_not_initialized'), 'search')
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
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'search')
