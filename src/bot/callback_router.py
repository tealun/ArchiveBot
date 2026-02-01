"""
Callback query handlers - Main Router
Handles button clicks and inline keyboard callbacks
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.language_context import get_language_context

# Import all callback handlers
from .callbacks import (
    # Language
    handle_language_callback,
    # Tag
    handle_tag_callback,
    handle_tags_page_callback,
    handle_tag_list_page_callback,
    # Search
    handle_search_page_callback,
    # AI
    handle_ai_view_callback,
    handle_ai_confirm_callback,
    handle_ai_cancel_callback,
    # Trash
    handle_delete_callback,
    handle_trash_restore_callback,
    handle_trash_delete_callback,
    # Note
    handle_note_callback,
    handle_note_view_callback,
    handle_notes_page_callback,
    handle_note_exit_save_callback,
    handle_note_finish_callback,
    handle_note_continue_callback,
    handle_note_add_callback,
    handle_note_edit_callback,
    handle_note_modify_callback,
    handle_note_append_callback,
    handle_note_share_callback,
    handle_note_delete_callback,
    handle_note_quick_edit_callback,
    handle_note_quick_append_callback,
    handle_note_quick_delete_callback,
    handle_note_quick_delete_confirm_callback,
    handle_continuity_callback,
    handle_refine_note_callback,
    # Review
    handle_review_callback,
    # Intent
    handle_short_text_intent_callback,
    handle_long_text_intent_callback,
    # Favorite
    handle_favorite_callback,
    handle_forward_callback,
    # Backup
    handle_backup_create_now_callback,
    handle_backup_keep_callback,
    handle_backup_delete_all_callback,
    # Export
    handle_export_format_callback,
    # Setting
    handle_setting_category_callback,
    handle_setting_item_callback,
    handle_setting_set_callback,
    handle_setting_back_callback,
    handle_setting_input,
)

# Import channel actions handlers
from .callbacks.channel_actions import (
    handle_channel_note,
    handle_channel_delete,
    handle_channel_back,
    handle_channel_archive,
)

# Import note favorite handler
from .callbacks.note_favorite import handle_note_favorite_callback

logger = logging.getLogger(__name__)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    统一处理所有callback query - 路由分发器
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        
        # 尝试立即回应查询，但如果超时不影响后续处理
        try:
            await query.answer()
        except Exception as e:
            # 忽略超时错误，继续处理
            if 'too old' not in str(e).lower():
                logger.warning(f"Failed to answer callback query: {e}")
        
        lang_ctx = get_language_context(update, context)
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
        elif callback_data.startswith('delete:'):
            await handle_delete_callback(update, context)
        elif callback_data.startswith('trash_restore:'):
            await handle_trash_restore_callback(update, context)
        elif callback_data.startswith('trash_delete:'):
            await handle_trash_delete_callback(update, context)
        elif callback_data.startswith('review:'):
            await handle_review_callback(update, context)
        elif callback_data.startswith('note:'):
            await handle_note_callback(update, context)
        elif callback_data.startswith('note_view:'):
            await handle_note_view_callback(update, context)
        elif callback_data.startswith('notes_page:'):
            await handle_notes_page_callback(update, context)
        elif callback_data == 'notes_noop':
            # 不做任何操作（页码显示按钮）
            pass
        elif callback_data.startswith('note_exit_save:'):
            await handle_note_exit_save_callback(update, context)
        elif callback_data == 'note_finish':
            await handle_note_finish_callback(update, context)
        elif callback_data == 'note_continue':
            await handle_note_continue_callback(update, context)
        elif callback_data.startswith('note_add:'):
            await handle_note_add_callback(update, context)
        elif callback_data.startswith('note_edit:'):
            await handle_note_edit_callback(update, context)
        elif callback_data.startswith('note_modify:'):
            await handle_note_modify_callback(update, context)
        elif callback_data.startswith('note_append:'):
            await handle_note_append_callback(update, context)
        elif callback_data.startswith('note_share:'):
            await handle_note_share_callback(update, context)
        elif callback_data.startswith('note_delete:'):
            await handle_note_delete_callback(update, context)
        elif callback_data.startswith('note_quick_edit:'):
            await handle_note_quick_edit_callback(update, context)
        elif callback_data.startswith('note_quick_append:'):
            await handle_note_quick_append_callback(update, context)
        elif callback_data.startswith('note_quick_delete:'):
            await handle_note_quick_delete_callback(update, context)
        elif callback_data.startswith('note_quick_delete_confirm:'):
            await handle_note_quick_delete_confirm_callback(update, context)
        elif callback_data.startswith('continuity:'):
            await handle_continuity_callback(update, context)
        elif callback_data == 'note_close':
            # 关闭笔记查看窗口
            await query.message.delete()
            await query.answer(lang_ctx.t('callback_closed'))
        elif callback_data.startswith('short_text:'):
            await handle_short_text_intent_callback(update, context)
        elif callback_data.startswith('longtxt_note:') or callback_data.startswith('longtxt_chat:'):
            await handle_long_text_intent_callback(update, context)
        elif callback_data.startswith('refine_note:'):
            await handle_refine_note_callback(update, context)
        elif callback_data.startswith('fav:'):
            await handle_favorite_callback(update, context)
        elif callback_data.startswith('forward:'):
            await handle_forward_callback(update, context)
        elif callback_data == 'backup_create_now':
            await handle_backup_create_now_callback(update, context)
        elif callback_data.startswith('backup_keep:'):
            await handle_backup_keep_callback(update, context)
        elif callback_data == 'backup_delete_all':
            await handle_backup_delete_all_callback(update, context)
        elif callback_data.startswith('export_format:'):
            await handle_export_format_callback(update, context)
        elif callback_data.startswith('setting_cat:'):
            await handle_setting_category_callback(update, context)
        elif callback_data.startswith('setting_item:'):
            await handle_setting_item_callback(update, context)
        elif callback_data.startswith('setting_set:'):
            await handle_setting_set_callback(update, context)
        elif callback_data == 'setting_back':
            await handle_setting_back_callback(update, context)
        elif callback_data.startswith('ai_confirm:'):
            await handle_ai_confirm_callback(update, context)
        elif callback_data.startswith('ai_cancel:'):
            await handle_ai_cancel_callback(update, context)
        elif callback_data.startswith('ch_note:'):
            await handle_channel_note(update, context)
        elif callback_data.startswith('ch_del:') or callback_data.startswith('ch_del_note:'):
            await handle_channel_delete(update, context)
        elif callback_data.startswith('ch_back:'):
            await handle_channel_back(update, context)
        elif callback_data.startswith('ch_archive:'):
            await handle_channel_archive(update, context)
        elif callback_data.startswith('note_fav:'):
            await handle_note_favorite_callback(update, context)
        elif callback_data == 'noop':
            # 不做任何操作（日期显示按钮）
            pass
        else:
            logger.warning(f"Unknown callback_data: {callback_data}")
    
    except Exception as e:
        logger.error(f"Error handling callback query: {e}", exc_info=True)
