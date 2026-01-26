"""
Note commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

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
        
        # 检查命令后是否有文本内容
        command_text = update.message.text or ""
        # 提取命令后的文本（支持 /note 或 /n）
        first_message = None
        if command_text.startswith('/note '):
            first_message = command_text[6:].strip()  # 去掉 "/note "
        elif command_text.startswith('/n '):
            first_message = command_text[3:].strip()  # 去掉 "/n "
        
        # 如果有文本，作为第一条笔记
        if first_message:
            context.user_data['note_messages'].append(first_message)
            logger.info(f"Note mode: recorded first message from command: {first_message[:50]}")
        
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
        
        await update.message.reply_text('\n'.join(reply_parts))
        
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
        await _finalize_note_internal(context, update.effective_chat.id, update.effective_user.id, reason="manual")
        
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
