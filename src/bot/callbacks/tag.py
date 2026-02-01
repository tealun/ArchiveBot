"""
Tag callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.tag_manager import TagManager
from ...core.search_engine import SearchEngine
from ...utils.helpers import truncate_text, format_datetime, get_content_type_emoji

@with_language_context
async def handle_tag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
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
            await query.edit_message_text(lang_ctx.t('callback_tag_no_content', tag=tag_name))
            return
        
        # 使用MessageBuilder统一格式化列表
        from ...utils.message_builder import MessageBuilder
        
        # 获取数据库实例用于查询状态
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        
        archives = search_result.get('results', [])
        
        # 添加tags字段（如果没有）
        for archive in archives:
            if 'tags' not in archive:
                tag_manager = context.bot_data.get('tag_manager')
                if tag_manager:
                    archive['tags'] = tag_manager.get_archive_tags(archive.get('id'))
                else:
                    archive['tags'] = []
        
        results_text = MessageBuilder.format_archive_list(
            archives,
            lang_ctx,
            db_instance=db,
            with_links=True
        )
        
        # 获取总数
        total_count = search_result.get('total_count', search_result.get('count', 0))
        
        message = lang_ctx.t('callback_tag_header', tag=tag_name) + f"\n\n{results_text}"
        
        # 构建按钮布局：只包含分页和返回按钮
        keyboard = []
        
        # 构建分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        # 只有多于1页时才显示分页按钮
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"tag:{tag_name}:{page-1}"
                ))
            
            # 显示当前页码
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="tags_noop"
            ))
            
            if page + 1 < total_pages:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"tag:{tag_name}:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        # 返回按钮
        keyboard.append([InlineKeyboardButton(
            lang_ctx.t('button_back_to_tags'),
            callback_data="tags_page:0"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error handling tag callback: {e}", exc_info=True)


@with_language_context
async def handle_tags_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
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
        
        # 分页按钮 - 只在多页时显示
        total_pages = (len(tags) + page_size - 1) // page_size
        
        # 只有多于1页时才显示分页按钮
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"tags_page:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="tags_noop"
            ))
            
            if end_idx < len(tags):
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"tags_page:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = lang_ctx.t('tags_button_list_header', count=len(tags))
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error handling tags page callback: {e}", exc_info=True)


async def handle_tag_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle tag list pagination
    
    Callback data format: tag_list:page
    """
    await handle_tags_page_callback(update, context)
