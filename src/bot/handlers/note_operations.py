"""
Note operations handlers
处理笔记相关的各种操作
"""

import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_note_edit_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    处理快速编辑模式
    
    Returns:
        bool: 如果处理了编辑模式返回True，否则返回False
    """
    if not context.user_data.get('note_edit_mode'):
        return False
    
    message = update.message
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
    
    return True


async def handle_note_append_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    处理快速追加模式
    
    Returns:
        bool: 如果处理了追加模式返回True，否则返回False
    """
    if not context.user_data.get('note_append_mode'):
        return False
    
    message = update.message
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
    
    return True


async def handle_waiting_note(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> bool:
    """
    处理等待添加笔记状态
    
    Returns:
        bool: 如果处理了等待笔记状态返回True，否则返回False
    """
    if not context.user_data.get('waiting_note_for_archive'):
        return False
    
    message = update.message
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
    
    return True
