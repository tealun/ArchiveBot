"""
Note mode handlers
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import get_language_context
from ...utils.helpers import format_file_size, truncate_text

logger = logging.getLogger(__name__)

from ...core.note_manager import NoteManager


async def _handle_note_mode_message(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理笔记模式中的消息
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        message = update.message
        
        # 注意：命令拦截已由 note_mode_interceptor 装饰器处理
        # 这里只处理非命令的普通消息
        
        # 重置超时计时器 - 改进：强制从scheduler删除旧任务
        if 'note_timeout_job' in context.user_data:
            old_job = context.user_data['note_timeout_job']
            try:
                # 尝试从scheduler中移除
                old_job.schedule_removal()
                logger.debug(f"Removed old note timeout job for user {update.effective_user.id}")
            except Exception as e:
                logger.debug(f"Failed to remove note timeout job: {e}")
            
            # 额外保险：直接从scheduler的jobs中删除（如果存在）
            try:
                if context.job_queue and old_job.name:
                    current_jobs = context.job_queue.get_jobs_by_name(old_job.name)
                    for job in current_jobs:
                        job.schedule_removal()
                    if current_jobs:
                        logger.debug(f"Force removed {len(current_jobs)} stale jobs from scheduler")
            except Exception as e:
                logger.debug(f"Failed to force remove jobs: {e}")
        
        # 创建新的超时任务
        from datetime import timedelta
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
        logger.debug(f"Created new note timeout job for user {update.effective_user.id}, will trigger at {job.next_t}")
        
        # 检查消息类型
        if message.text:
            # 文本消息：添加到笔记内容
            # 使用(timestamp, message_id, text)元组存储，确保可以按顺序排序
            note_messages = context.user_data.get('note_messages', [])
            
            # 内存保护：限制消息数量，防止内存溢出
            MAX_NOTE_MESSAGES = 100  # 最多100条消息
            if len(note_messages) >= MAX_NOTE_MESSAGES:
                await message.reply_text(
                    f"⚠️ 已达到笔记消息上限（{MAX_NOTE_MESSAGES}条）\n"
                    f"请使用 /cancel 保存当前笔记",
                    reply_to_message_id=message.message_id
                )
                return
            
            # 不截断，完整保存消息
            # 使用message_id作为排序依据（Telegram保证message_id递增）
            import time
            note_messages.append((
                time.time(),           # 时间戳
                message.message_id,    # 消息ID（用于排序）
                message.text           # 完整文本（不截断）
            ))
            
            context.user_data['note_messages'] = note_messages
            
            # 添加"结束记录"按钮
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[
                InlineKeyboardButton("🔚 结束记录并保存", callback_data="note_finish")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 显示字符数统计
            total_chars = sum(len(msg[2]) for msg in note_messages)
            await message.reply_text(
                f"✅ 已记录 ({len(note_messages)} 条，共{total_chars}字符)",
                reply_to_message_id=message.message_id,
                reply_markup=reply_markup
            )
            
            logger.debug(f"Note mode: recorded text message ({len(note_messages)} total, {total_chars} chars)")
        
        elif _is_media_message(message):
            # 媒体消息：先归档
            storage_manager = context.bot_data.get('storage_manager')
            
            if storage_manager:
                # 内存保护：限制归档数量
                note_archives = context.user_data.get('note_archives', [])
                MAX_NOTE_ARCHIVES = 20  # 最多20个归档
                
                if len(note_archives) >= MAX_NOTE_ARCHIVES:
                    await message.reply_text(
                        f"⚠️ 已达到笔记归档上限（{MAX_NOTE_ARCHIVES}个）\n"
                        f"请使用 /cancel 保存当前笔记",
                        reply_to_message_id=message.message_id
                    )
                    return
                
                # 使用现有的_process_single_message处理归档
                success, result_msg, archive_id, _ = await _process_single_message(
                    message, context
                )
                
                if success and archive_id:
                    note_archives.append(archive_id)
                    context.user_data['note_archives'] = note_archives
                    
                    caption = message.caption or ""
                    if caption:
                        note_messages = context.user_data.get('note_messages', [])
                        # 使用相同的元组格式存储媒体的caption
                        import time
                        note_messages.append((
                            time.time(),
                            message.message_id,
                            f"[媒体] {caption}"
                        ))
                        context.user_data['note_messages'] = note_messages
                    
                    # 添加"结束记录"按钮
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [[
                        InlineKeyboardButton("🔚 结束记录并保存", callback_data="note_finish")
                    ]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await message.reply_text(
                        f"✅ 媒体已归档 (#{archive_id})\n"
                        f"📊 已归档：{len(note_archives)} 个",
                        reply_to_message_id=message.message_id,
                        reply_markup=reply_markup
                    )
                    logger.info(f"Note mode: archived media as #{archive_id}")
                else:
                    await message.reply_text(
                        "❌ 媒体归档失败",
                        reply_to_message_id=message.message_id
                    )
            else:
                await message.reply_text(
                    "❌ 存储管理器未初始化",
                    reply_to_message_id=message.message_id
                )
        else:
            await message.reply_text(
                "⚠️ 不支持的消息类型",
                reply_to_message_id=message.message_id
            )
        
    except Exception as e:
        logger.error(f"Error handling note mode message: {e}", exc_info=True)
        await message.reply_text(f"❌ 处理失败: {str(e)}")


async def note_timeout_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    笔记模式超时回调 - 15分钟无新消息自动生成笔记
    避免循环导入，直接在handlers中定义
    
    Args:
        context: Bot context
    """
    try:
        job_data = context.job.data
        chat_id = job_data['chat_id']
        user_id = job_data['user_id']
        
        # 详细日志：记录触发信息
        from datetime import datetime
        trigger_time = datetime.now()
        logger.info(f"Note timeout callback triggered for user {user_id} at {trigger_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Job data: chat_id={chat_id}, user_id={user_id}, job_name={context.job.name}")
        
        # 使用application.user_data来访问用户数据
        # context.user_data在job中可能为空，需要通过user_id访问
        # 注意：user_id可能是str或int，统一转换为int
        user_id_int = int(user_id) if isinstance(user_id, str) else user_id
        
        # application.user_data的key是整数类型的user_id
        if user_id_int not in context.application.user_data:
            logger.warning(f"Note timeout callback: user {user_id_int} has no user_data, possibly already cleaned up")
            return
        
        user_data = context.application.user_data[user_id_int]
        
        # 检查用户是否还在笔记模式
        if not user_data.get('note_mode'):
            logger.info(f"Note timeout callback: user {user_id_int} not in note mode, skipping (already exited)")
            return
        
        # 记录详细状态
        message_count = len(user_data.get('note_messages', []))
        archive_count = len(user_data.get('note_archives', []))
        note_start_time = user_data.get('note_start_time')
        
        logger.info(f"Processing note timeout for user {user_id_int}:")
        logger.info(f"  - Messages: {message_count}")
        logger.info(f"  - Archives: {archive_count}")
        logger.info(f"  - Start time: {note_start_time}")
        logger.info(f"  - Trigger time: {trigger_time}")
        
        # 生成并保存笔记（传递user_data确保数据访问正确）
        await _finalize_note_internal(context, chat_id, user_id_int, reason="timeout")
        
        logger.info(f"Note mode timeout completed for user {user_id_int}")
        
    except Exception as e:
        logger.error(f"Error in note timeout callback: {e}", exc_info=True)


async def _finalize_note_internal(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, reason: str = "manual") -> None:
    """
    完成笔记记录，生成并保存笔记（内部版本，减少内存占用）
    
    Args:
        context: Bot context
        chat_id: Chat ID
        user_id: User ID（用于访问user_data，必须是int类型）
        reason: 退出原因 (manual, timeout, command)
    """
    try:
        # 确保user_id是整数类型
        user_id_int = int(user_id) if isinstance(user_id, str) else user_id
        
        # 在job回调中，context.user_data可能为空，需要从application.user_data获取
        if reason == "timeout":
            if user_id_int not in context.application.user_data:
                logger.warning(f"User {user_id_int} not found in application.user_data")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="📝 笔记模式已超时\n\n⚠️ 未找到用户数据"
                )
                return
            user_data = context.application.user_data[user_id_int]
        else:
            user_data = context.user_data
        
        messages = user_data.get('note_messages', [])
        archives = user_data.get('note_archives', [])
        
        logger.debug(f"Finalizing note for user {user_id_int}: {len(messages)} messages, {len(archives)} archives, reason={reason}")
        
        if not messages:
            await context.bot.send_message(
                chat_id=chat_id,
                text="📝 笔记模式已退出\n\n⚠️ 未记录到任何消息"
            )
            # 清理数据
            if reason == "timeout":
                user_data_to_clean = context.application.user_data.get(user_id_int, {})
            else:
                user_data_to_clean = context.user_data
            
            keys_to_remove = ['note_mode', 'note_messages', 'note_archives', 'note_start_time', 'note_timeout_job', 'pending_command']
            for key in keys_to_remove:
                user_data_to_clean.pop(key, None)
            
            return
        else:
            # 使用智能排序（处理Telegram分片消息可能乱序）
            from ...utils.helpers import smart_sort_messages
            ai_summarizer = context.bot_data.get('ai_summarizer')
            
            sorted_messages = await smart_sort_messages(messages, ai_summarizer)
            
            # 合并所有文本消息（只取text部分）
            note_content = '\n\n'.join(msg[2] for msg in sorted_messages)
            
            logger.info(f"Note content assembled: {len(sorted_messages)} messages, {len(note_content)} total chars")
            
            # 生成AI标题（如果AI可用）
            note_title = None
            ai_summarizer = context.bot_data.get('ai_summarizer')
            if ai_summarizer and ai_summarizer.is_available():
                try:
                    # 获取用户语言设置
                    from ...utils.config import get_config
                    config = get_config()
                    user_language = user_data.get('language', config.get('bot.language', 'zh-CN'))
                    
                    # 使用AI生成标题（32字以内）
                    note_title = await ai_summarizer.generate_title_from_text(
                        note_content, 
                        max_length=32,
                        language=user_language
                    )
                    logger.info(f"Generated AI title for note: {note_title}")
                except Exception as e:
                    logger.warning(f"Failed to generate AI title: {e}")
            
            # 先保存笔记以获得note_id（不带storage_path）
            note_manager = context.bot_data.get('note_manager')
            if not note_manager:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ 笔记管理器未初始化"
                )
                return
            
            # 如果有归档，关联第一个归档
            archive_id = archives[0] if archives else None
            note_id = note_manager.add_note(
                archive_id, 
                note_content, 
                title=note_title,
                storage_path=None  # 先不设置，等转发后再更新
            )
            
            if not note_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ 笔记保存失败"
                )
                return
            
            # 转发笔记到Telegram频道（使用统一的公共函数）
            from ...utils.note_storage_helper import forward_note_to_channel, update_archive_message_buttons
            storage_path = await forward_note_to_channel(
                context=context,
                note_id=note_id,
                note_content=note_content,
                note_title=note_title,
                note_manager=note_manager
            )
            
            # 更新原始存档消息的按钮（如果有关联存档）
            if archive_id:
                await update_archive_message_buttons(context, archive_id)
            
            # 构建成功反馈消息
            reason_map = {
                'manual': '手动退出',
                'timeout': '超时自动保存',
                'command': '命令触发'
            }
            reason_text = reason_map.get(reason, '未知原因')
            
            # 构建简洁的结果消息
            result_parts = [
                f"✅ 笔记已保存",
                f"📝 笔记 #{note_id}"
            ]
            
            if note_title:
                result_parts.append(f"📌 {note_title}")
            
            result_parts.append(f"📊 文本: {len(messages)} | 媒体: {len(archives)}")
            
            if archive_id:
                result_parts.append(f"📎 关联: #{archive_id}")
            
            # 添加频道链接（使用HTML格式）
            if storage_path:
                result_parts.append(f'🔗 <a href="{storage_path}">查看频道消息</a>')
            
            result_parts.append(f"🔚 {reason_text}")
            
            # 构建编辑/追加/转发/删除按钮
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("➕ 追加", callback_data=f"note_quick_append:{note_id}"),
                    InlineKeyboardButton("✏️ 编辑", callback_data=f"note_quick_edit:{note_id}"),
                ],
                [
                    InlineKeyboardButton("📤 转发", callback_data=f"note_share:{note_id}"),
                    InlineKeyboardButton("🗑️ 删除", callback_data=f"note_quick_delete:{note_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text='\n'.join(result_parts),
                parse_mode='HTML',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            
            # 保存笔记ID和保存时间到user_data，用于5分钟窗口检测
            if reason != "timeout":
                context.user_data['last_note_id'] = note_id
                context.user_data['last_note_time'] = datetime.now()
        
        # 立即清除所有笔记模式相关数据，释放内存
        # 根据reason决定清除哪个user_data
        if reason == "timeout":
            # 确保user_id_int已定义
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            if user_id_int in context.application.user_data:
                user_data_to_clean = context.application.user_data[user_id_int]
            else:
                logger.warning(f"Cannot clean user_data for user {user_id_int}: not found in application.user_data")
                return
        else:
            user_data_to_clean = context.user_data
        
        keys_to_remove = ['note_mode', 'note_messages', 'note_archives', 'note_start_time', 'note_timeout_job', 'pending_command']
        for key in keys_to_remove:
            user_data_to_clean.pop(key, None)
        
        logger.info(f"Note finalized and cleaned up for user {user_id}, reason={reason}")
        
    except Exception as e:
        logger.error(f"Error finalizing note: {e}", exc_info=True)
        # 确保即使出错也清理内存
        try:
            for key in ['note_mode', 'note_messages', 'note_archives', 'note_start_time', 'note_timeout_job', 'pending_command']:
                context.user_data.pop(key, None)
        except Exception as cleanup_err:
            logger.debug(f"Failed to cleanup user_data: {cleanup_err}")
