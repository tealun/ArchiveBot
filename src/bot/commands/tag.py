"""
Tag commands
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

from ...core.tag_manager import TagManager

@intercept_in_note_mode
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
            await send_or_update_reply(update, context, lang_ctx.t('error_tag_manager_not_initialized'), 'tags')
            return
        
        # Get all tags (sorted by count descending)
        tags = tag_manager.get_all_tags(limit=100)
        
        if not tags:
            await send_or_update_reply(update, context, lang_ctx.t('tags_empty'), 'tags')
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
        
        await send_or_update_reply(update, context, message, 'tags', reply_markup=reply_markup)
        
        logger.info(f"Tags command executed: {len(tags)} tags, page {page}")
        
    except Exception as e:
        logger.error(f"Error in tags_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'tags')
