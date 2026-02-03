"""
Message handlers - Main Entry Point
Handles incoming messages for archiving
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.language_context import get_language_context
from .message_aggregator import MessageAggregator
from ..core.ai_session import get_session_manager
from ..ai.chat_router import handle_chat_message
from ..core.analyzer import ContentAnalyzer
from ..core.storage_manager import StorageManager
from ..utils.helpers import format_file_size, truncate_text

# Import handlers from handlers package
from .handlers import (
    _handle_note_mode_message,
    handle_note_edit_mode,
    handle_note_append_mode,
    handle_waiting_note,
    handle_note_refine,
    handle_ai_chat_mode,
    _cleanup_user_data,
    _batch_callback
)

logger = logging.getLogger(__name__)

# 全局消息聚合器
_message_aggregator: Optional[MessageAggregator] = None


def get_message_aggregator() -> MessageAggregator:
    """Get or create message aggregator"""
    global _message_aggregator
    if _message_aggregator is None:
        _message_aggregator = MessageAggregator(batch_window_ms=200, max_batch_size=100)
    return _message_aggregator


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming message for archiving (with batch detection)
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        message = update.message
        lang_ctx = get_language_context(update, context)
        
        # ==================== 第一阶段：1000ms预等待（最高优先级） ====================
        # 快速过滤转发场景：注册等待期后延迟1000ms
        # 如果期间有转发消息到达，直接交给批次处理
        from .handlers.forward_detector import get_forward_detector
        detector = get_forward_detector()
        user_id = str(message.from_user.id)
        
        # 只对纯文本消息（无媒体附件）启动等待期
        if message.text and not any([
            message.photo, message.video, message.document,
            message.audio, message.voice, message.animation,
            message.sticker, message.contact, message.location,
            message.media_group_id
        ]):
            # 注册等待期
            await detector.register_text_message(user_id, message.text)
            
            # 第一阶段：1000ms延迟，检查快速转发
            import asyncio
            await asyncio.sleep(1.0)  # 1000ms
            
            # 检查延迟期间是否检测到转发
            forward_status = detector.get_forward_status(user_id)
            if forward_status and forward_status.get('forwarded_detected'):
                # 检测到转发消息，取消文本处理，交给批次流程
                logger.info(f"[Stage1] Forward detected within 1000ms for user {user_id}, skipping text processing")
                detector.cancel_wait(user_id)
                return
            
            logger.debug(f"[Stage1] No forward detected after 1000ms, continuing to stage 2 for user {user_id}")
        # ========================================================================
            
            logger.debug(f"No forward detected after delay, continuing text processing for user {user_id}")
        # ====================================================================
        
        # 优先检查：配置输入模式
        from .callbacks.setting import handle_setting_input
        if await handle_setting_input(update, context):
            # 清理等待期（已处理完成）
            detector.cancel_wait(user_id)
            return
        
        # 优先检查：笔记模式
        if context.user_data.get('note_mode'):
            await _handle_note_mode_message(update, context, lang_ctx)
            return
        
        # 检查快速编辑模式
        if context.user_data.get('note_edit_mode'):
            note_id = context.user_data.get('note_id_to_edit')
            if note_id and message.text:
                note_manager = context.bot_data.get('note_manager')
                if note_manager:
                    # 更新笔记内容
                    success = note_manager.update_note(note_id, message.text)
                    if success:
                        await message.reply_text(f"✅ 笔记 #{note_id} 已更新")
                        logger.info(f"Quick edited note {note_id}")
                        
                        # 更新时间窗口
                        context.user_data['last_note_id'] = note_id
                        context.user_data['last_note_time'] = datetime.now()
                    else:
                        await message.reply_text("❌ 更新失败")
                
                # 清除编辑模式
                context.user_data.pop('note_edit_mode', None)
                context.user_data.pop('note_id_to_edit', None)
            return
        
        # 检查快速追加模式
        if context.user_data.get('note_append_mode'):
            note_id = context.user_data.get('note_id_to_append')
            if note_id and message.text:
                note_manager = context.bot_data.get('note_manager')
                if note_manager:
                    # 获取现有笔记内容
                    note = note_manager.get_note(note_id)
                    if note:
                        # 追加内容
                        new_content = f"{note['content']}\n\n---\n\n{message.text}"
                        success = note_manager.update_note(note_id, new_content)
                        if success:
                            await message.reply_text(f"✅ 内容已追加到笔记 #{note_id}")
                            logger.info(f"Quick appended to note {note_id}")
                            
                            # 更新时间窗口
                            context.user_data['last_note_id'] = note_id
                            context.user_data['last_note_time'] = datetime.now()
                        else:
                            await message.reply_text("❌ 追加失败")
                    else:
                        await message.reply_text("❌ 笔记不存在")
                
                # 清除追加模式
                context.user_data.pop('note_append_mode', None)
                context.user_data.pop('note_id_to_append', None)
            return
        
        # 检查是否在等待添加笔记
        if context.user_data.get('waiting_note_for_archive'):
            archive_id = context.user_data.get('waiting_note_for_archive')
            
            if message.text:
                note_manager = context.bot_data.get('note_manager')
                if note_manager:
                    # 检查是修改模式还是追加模式
                    if context.user_data.get('note_modify_mode'):
                        # 修改模式：删除旧笔记，添加新笔记
                        note_id_to_modify = context.user_data.get('note_id_to_modify')
                        if note_id_to_modify:
                            # 删除旧笔记
                            note_manager.delete_note(note_id_to_modify)
                            # 添加新笔记
                            new_note_id = note_manager.add_note(archive_id, message.text)
                            if new_note_id:
                                await message.reply_text(lang_ctx.t('note_modified', archive_id=archive_id))
                                logger.info(f"Modified note {note_id_to_modify} -> {new_note_id} for archive {archive_id}")
                            else:
                                await message.reply_text(lang_ctx.t('note_add_failed'))
                        # 清除修改模式标记
                        context.user_data.pop('note_modify_mode', None)
                        context.user_data.pop('note_id_to_modify', None)
                    elif context.user_data.get('note_append_mode'):
                        # 追加模式：获取现有笔记，追加内容后更新
                        note_id_to_append = context.user_data.get('note_id_to_append')
                        if note_id_to_append:
                            # 获取现有笔记
                            notes = note_manager.get_notes(archive_id)
                            old_content = None
                            for note in notes:
                                if note['id'] == note_id_to_append:
                                    old_content = note['content']
                                    break
                            
                            if old_content:
                                # 删除旧笔记
                                note_manager.delete_note(note_id_to_append)
                                # 添加追加后的笔记
                                new_content = f"{old_content}\n\n---\n\n{message.text}"
                                new_note_id = note_manager.add_note(archive_id, new_content)
                                if new_note_id:
                                    await message.reply_text(lang_ctx.t('note_appended', archive_id=archive_id))
                                    logger.info(f"Appended to note {note_id_to_append} -> {new_note_id} for archive {archive_id}")
                                else:
                                    await message.reply_text(lang_ctx.t('note_add_failed'))
                        # 清除追加模式标记
                        context.user_data.pop('note_append_mode', None)
                        context.user_data.pop('note_id_to_append', None)
                    else:
                        # 普通添加模式
                        note_id = note_manager.add_note(archive_id, message.text)
                        if note_id:
                            # 提取标题：使用笔记文本的前 50 个字符
                            note_title = message.text[:50] if message.text else None
                            
                            # 转发笔记到Telegram频道
                            from ...utils.note_storage_helper import forward_note_to_channel, update_archive_message_buttons
                            storage_path = await forward_note_to_channel(
                                context=context,
                                note_id=note_id,
                                note_content=message.text,
                                note_title=note_title,
                                note_manager=note_manager
                            )
                            
                            # 更新存档消息按钮
                            if archive_id:
                                await update_archive_message_buttons(context, archive_id)
                            
                            await message.reply_text(lang_ctx.t('note_added_to_archive', archive_id=archive_id, note_id=note_id))
                            logger.info(f"Added note {note_id} to archive {archive_id}, forwarded to channel: {storage_path}")
                        else:
                            await message.reply_text(lang_ctx.t('note_add_failed_error'))
                else:
                    await message.reply_text(lang_ctx.t('note_manager_uninitialized'))
                
                # 清除等待状态（使用pop避免KeyError）
                context.user_data.pop('waiting_note_for_archive', None)
                context.user_data.pop('note_modify_mode', None)
                context.user_data.pop('note_id_to_modify', None)
                context.user_data.pop('note_append_mode', None)
                context.user_data.pop('note_id_to_append', None)
                
                # 内存保护：定期清理user_data中的临时数据
                _cleanup_user_data(context.user_data)
                return
        
        # 检查是否在等待笔记精炼指令
        refine_context = context.user_data.get('refine_note_context')
        if refine_context and refine_context.get('waiting_for_instruction'):
            if message.text:
                instruction = message.text.strip()
                archive_id = refine_context['archive_id']
                notes = refine_context['notes']
                
                # 组合所有笔记内容
                notes_text = "\n\n".join([note['content'] for note in notes])
                
                # 使用AI精炼笔记
                ai_summarizer = context.bot_data.get('ai_summarizer')
                if ai_summarizer and ai_summarizer.is_available():
                    try:
                        await message.reply_text(lang_ctx.t('ai_refining_note'))
                        
                        # 构造提示词
                        refine_prompt = f"""请根据用户的指令修改以下笔记：

原始笔记：
{notes_text}

用户指令：{instruction}

请输出修改后的笔记内容，保持简洁清晰。"""
                        
                        # 调用AI（summarize_content只接受content, url, language, context参数）
                        # 使用context传递额外信息
                        refined_context = {
                            'content_type': 'note_refinement',
                            'instruction': instruction
                        }
                        refined_result = await ai_summarizer.summarize_content(
                            content=refine_prompt,
                            language=lang_ctx.language,
                            context=refined_context
                        )
                        
                        # 提取总结内容
                        refined_content = refined_result.get('summary') if refined_result.get('success') else None
                        
                        if refined_content:
                            # 删除旧笔记
                            note_manager = context.bot_data.get('note_manager')
                            if note_manager:
                                for note in notes:
                                    note_manager.delete_note(note['id'])
                                
                                # 添加精炼后的笔记
                                new_note_id = note_manager.add_note(archive_id, refined_content)
                                
                                if new_note_id:
                                    await message.reply_text(
                                        lang_ctx.t('ai_refine_note_success', archive_id=archive_id, content=truncate_text(refined_content, 300)),
                                        parse_mode=ParseMode.MARKDOWN
                                    )
                                    logger.info(f"Refined notes for archive {archive_id}")
                                else:
                                    await message.reply_text(lang_ctx.t('ai_refine_note_save_failed'))
                            else:
                                await message.reply_text(lang_ctx.t('note_manager_uninitialized'))
                        else:
                            await message.reply_text(lang_ctx.t('ai_refine_note_failed'))
                            
                    except Exception as e:
                        logger.error(f"Error refining note: {e}", exc_info=True)
                        await message.reply_text(lang_ctx.t('ai_refine_note_error', error=str(e)))
                else:
                    await message.reply_text(lang_ctx.t('ai_feature_disabled'))
                
                # 清除等待状态
                context.user_data.pop('refine_note_context', None)
                # 清理其他可能的临时数据
                context.user_data.pop('waiting_note_for_archive', None)
                context.user_data.pop('note_modify_mode', None)
                context.user_data.pop('note_id_to_modify', None)
                context.user_data.pop('note_append_mode', None)
                context.user_data.pop('note_id_to_append', None)
                return

        
        # AI Chat Mode - 处理AI对话（已提取到独立模块）
        if await handle_ai_chat_mode(update, context, lang_ctx):
            return
        
        # 正常归档流程
        aggregator = get_message_aggregator()
        
        # 使用聚合器处理（自动检测批量）
        async def callback(messages: List[Message], merged_caption: Optional[str], source_info: Optional[Dict], is_forwarded: bool):
            await _batch_callback(messages, merged_caption, source_info, is_forwarded, update, context)
        
        await aggregator.process_message(message, callback)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        lang_ctx = get_language_context(update, context)
        try:
            await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
        except Exception as reply_err:
            logger.error(f"Failed to send error message: {reply_err}")


# Import and re-export media handlers from handlers package
from .handlers import (
    handle_photo,
    handle_video,
    handle_document,
    handle_audio,
    handle_voice,
    handle_animation,
    handle_sticker,
    handle_contact,
    handle_location
)
