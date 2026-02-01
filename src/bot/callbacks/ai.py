"""
Ai callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...storage.database import DatabaseStorage

@with_language_context
async def handle_ai_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
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
            except Exception as e:
                logger.debug(f"Failed to parse AI key points JSON: {e}")
        
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

    except Exception as e:
        logger.error(f"Error in AI view callback: {e}", exc_info=True)
        await query.answer("Error showing AI analysis", show_alert=True)


@with_language_context
async def handle_ai_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle AI write operation confirmation callback (Phase 2)
    
    Callback data format: ai_confirm:confirmation_id
    """
    query = update.callback_query
    
    try:
        # Parse callback data
        confirmation_id = query.data.split(':', 1)[1]
        
        # Get pending action
        pending_actions = context.user_data.get('pending_actions', {})
        action_data = pending_actions.get(confirmation_id)
        
        if not action_data:
            await query.answer(lang_ctx.t('confirmation_expired'), show_alert=True)
            await query.message.delete()
            return
        
        # Extract action info
        action_type = action_data.get('action_type')
        params = action_data.get('params', {})
        language = action_data.get('language', lang_ctx.language)
        
        # Execute action using executor
        from ...ai.operations.executor import execute_confirmed_action
        
        success, result_message = await execute_confirmed_action(
            action_type=action_type,
            action_params=params,
            context=context,
            language=language
        )
        
        # Clear pending action
        del pending_actions[confirmation_id]
        
        # Update message
        await query.answer(lang_ctx.t('action_executed') if success else lang_ctx.t('action_failed'))
        await query.message.edit_text(
            f"{result_message}",
            reply_markup=None
        )
        
        logger.info(f"✓ AI write operation confirmed and executed: {action_type}")
        
    except Exception as e:
        logger.error(f"Error handling AI confirm callback: {e}", exc_info=True)
        await query.answer(f"{lang_ctx.t('error_occurred')}", show_alert=True)


@with_language_context
async def handle_ai_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle AI write operation cancellation callback (Phase 2)
    
    Callback data format: ai_cancel:confirmation_id
    """
    query = update.callback_query
    
    try:
        # Parse callback data
        confirmation_id = query.data.split(':', 1)[1]
        
        # Get pending action
        pending_actions = context.user_data.get('pending_actions', {})
        action_data = pending_actions.get(confirmation_id)
        
        if not action_data:
            await query.answer(lang_ctx.t('confirmation_expired'), show_alert=True)
            await query.message.delete()
            return
        
        # Clear pending action
        del pending_actions[confirmation_id]
        
        # Log audit event
        from ...ai.chat_router import _log_audit_event
        _log_audit_event(
            'write_cancelled',
            action_data.get('action_type'),
            action_data.get('params', {}),
            context,
            lang_ctx.language,
            'User cancelled operation'
        )
        
        # Update message
        cancel_msg = "✅ 操作已取消" if lang_ctx.language.startswith('zh') else "✅ Operation cancelled"
        await query.answer(cancel_msg)
        await query.message.edit_text(
            f"{cancel_msg}",
            reply_markup=None
        )
        
        logger.info(f"✓ AI write operation cancelled: {action_data.get('action_type')}")
        
    except Exception as e:
        logger.error(f"Error handling AI cancel callback: {e}", exc_info=True)
        await query.answer(f"{lang_ctx.t('error_occurred')}", show_alert=True)
