"""
Note commands
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

from ...core.note_manager import NoteManager

@with_language_context
async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /note command - 进入笔记模式
    
    支持命令后直接跟文本：/note 这是第一条笔记
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 检查是否已经在笔记模式中
        if context.user_data.get('note_mode'):
            await send_or_update_reply(
                update,
                context,
                "⚠️ 您已经在笔记模式中\n"
                "发送 /cancel 可以退出并保存当前笔记",
                'note'
            )
            return
        
        # 进入笔记模式
        context.user_data['note_mode'] = True
        context.user_data['note_messages'] = []  # 收集的消息
        context.user_data['note_archives'] = []  # 归档的媒体ID
        context.user_data['note_start_time'] = update.message.date
        
        # 检查命令后是否有文本内容
        command_text = update.message.text or ""
        # 提取命令后的文本（支持 /note 或 /n）
        first_message = None
        if command_text.startswith('/note '):
            first_message = command_text[6:].strip()  # 去掉 "/note "
        elif command_text.startswith('/n '):
            first_message = command_text[3:].strip()  # 去掉 "/n "
        
        # 如果有文本，作为第一条笔记（使用元组格式与其他消息保持一致）
        if first_message:
            import time
            context.user_data['note_messages'].append((
                time.time(),                # 时间戳
                update.message.message_id,  # 消息ID
                first_message               # 完整文本
            ))
            logger.info(f"Note mode: recorded first message from command: {first_message[:50]}")
        
        # 设置15分钟后的超时任务
        # 移除之前的超时任务（如果有）
        if 'note_timeout_job' in context.user_data:
            try:
                context.user_data['note_timeout_job'].schedule_removal()
            except Exception as e:
                logger.debug(f"Failed to remove previous timeout job: {e}")
        
        # 创建新的超时任务
        from datetime import timedelta
        # 导入handlers中的note_timeout_callback
        from ..handlers.note_mode import note_timeout_callback
        
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
        
        # 构建回复消息
        reply_parts = ["📝 已进入笔记模式\n"]
        
        if first_message:
            reply_parts.append(f"✅ 已记录第一条内容 (1 条)\n")
        
        reply_parts.extend([
            "💬 现在发送的所有消息都会被记录为笔记",
            "📎 发送的媒体文件会自动归档并关联到笔记\n",
            "⏱️ 15分钟内无新消息将自动生成笔记",
            "🚫 发送 /cancel 可立即退出并保存笔记"
        ])
        
        await send_or_update_reply(update, context, '\n'.join(reply_parts), 'note')
        
        logger.info(f"User {update.effective_user.id} entered note mode")
        
    except Exception as e:
        logger.error(f"Error in note_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'note')


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
            await send_or_update_reply(
                update,
                context,
                "⚠️ 您当前不在笔记模式中\n"
                "发送 /note 可以进入笔记模式",
                'cancel'
            )
            return
        
        # 导入handlers中的_finalize_note_internal
        from ..handlers import _finalize_note_internal
        
        # 立即生成并保存笔记
        await _finalize_note_internal(context, update.effective_chat.id, update.effective_user.id, reason="manual")
        
        logger.info(f"User {update.effective_user.id} cancelled note mode")
        
    except Exception as e:
        logger.error(f"Error in cancel_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'cancel')


@intercept_in_note_mode
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
            await send_or_update_reply(update, context, lang_ctx.t('note_manager_not_initialized'), 'notes')
            return
        
        # 获取所有笔记（分页显示）
        page = 0
        page_size = 10
        
        # 获取总数
        total_count = note_manager.get_notes_count()
        
        # 获取当前页笔记
        results = note_manager.get_all_notes(limit=page_size, offset=page * page_size)
        
        # 获取配置
        config = get_config()
        
        # 使用 MessageBuilder 格式化笔记列表
        from ...utils.message_builder import MessageBuilder
        result_text, reply_markup = MessageBuilder.format_notes_list(
            notes=results,
            config=config,
            lang_ctx=lang_ctx,
            page=page,
            total_count=total_count
        )
        
        await send_or_update_reply(
            update,
            context,
            result_text,
            'notes',
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        logger.info(f"Notes list command executed")
        
    except Exception as e:
        logger.error(f"Error in notes_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'notes')
