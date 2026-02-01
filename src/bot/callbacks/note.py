"""
Note callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.note_manager import NoteManager
from ...utils.helpers import truncate_text

@with_language_context
async def handle_note_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle note button click - 查看归档的关联笔记
    
    Callback data format: note:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: note:archive_id
        archive_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            logger.error("Note manager not initialized")
            return
        
        # 获取该归档的所有笔记
        notes = note_manager.get_notes(archive_id)
        
        if not notes:
            # 没有笔记时，直接设置等待状态并提示用户输入
            await query.answer("📝 请回复此消息输入笔记")
            
            # 设置等待状态
            context.user_data['waiting_note_for_archive'] = archive_id
            
            # 发送提示消息
            from ...utils.message_builder import MessageBuilder
            prompt_text = MessageBuilder.format_note_input_prompt(archive_id, 'add')
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=prompt_text,
                reply_to_message_id=query.message.message_id
            )
            logger.info(f"User waiting to add note for archive {archive_id}")
            return
        
        # 获取归档信息
        db_storage = context.bot_data.get('db_storage')
        archive = None
        if db_storage:
            archive = db_storage.get_archive(archive_id)
        
        # 使用MessageBuilder格式化笔记显示
        from ...utils.message_builder import MessageBuilder
        
        if len(notes) == 1:
            notes_text, reply_markup = MessageBuilder.format_note_detail_reply(notes[0], archive)
        else:
            # 多条笔记，显示列表
            notes_text, reply_markup = MessageBuilder.format_note_list_multi(notes, archive_id, lang_ctx)
        
        # 先answer，然后发送笔记内容
        await query.answer()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=notes_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
        logger.info(f"Displayed {len(notes)} notes for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle note view button click - 查看笔记详情
    
    Callback data format: note_view:note_id
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: note_view:note_id
        note_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        
        if not note_manager:
            await query.answer(lang_ctx.t('note_manager_not_initialized'), show_alert=True)
            logger.error("Note manager not initialized")
            return
        
        # 获取笔记详情
        note = note_manager.get_note(note_id)
        
        if not note:
            await query.answer("笔记不存在", show_alert=True)
            return
        
        # 获取关联的存档信息（如果需要）
        archive_id = note.get('archive_id')
        archive = None
        if archive_id:
            db_storage = context.bot_data.get('db_storage')
            if db_storage:
                archive = db_storage.get_archive(archive_id)
        
        # 使用MessageBuilder构建详情
        from ...utils.message_builder import MessageBuilder
        detail_text, reply_markup = MessageBuilder.format_note_detail_reply(note, archive)
        
        # Answer并发送详情
        await query.answer()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=detail_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        
        logger.info(f"Displayed note detail for note_id={note_id}")
        
    except Exception as e:
        logger.error(f"Error handling note view callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_exit_save_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle note exit and save button click - 退出笔记模式并保存，然后执行命令
    
    Callback data format: note_exit_save:/command
    """
    query = update.callback_query
    
    try:
        # 解析命令
        parts = query.data.split(':', 1)
        command = parts[1] if len(parts) > 1 else None
        
        # 导入handlers中的_finalize_note_internal
        from ..handlers.note_mode import _finalize_note_internal
        
        # 保存笔记
        await _finalize_note_internal(context, update.effective_chat.id, update.effective_user.id, reason="command")
        
        await query.answer("✅ 笔记已保存")
        await query.message.delete()
        
        # 执行命令（如果有）
        if command:
            logger.info(f"Executing pending command after note mode: {command}")
            
            # 导入命令分发器
            from ..commands import dispatch_command_after_note
            
            # 执行命令
            success = await dispatch_command_after_note(command, update, context)
            
            if not success:
                # 如果执行失败，提示用户重新输入
                await query.message.reply_text(
                    lang_ctx.t('command_execution_failed', command=command)
                )
        
        logger.info("Note mode exited with save and command executed")
        
    except Exception as e:
        logger.error(f"Error handling note exit save callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle note finish button click - 结束笔记记录并保存
    
    Callback data format: note_finish
    """
    query = update.callback_query
    
    try:
        # 导入handlers中的_finalize_note_internal
        from ..handlers.note_mode import _finalize_note_internal
        
        # 保存笔记
        await _finalize_note_internal(context, update.effective_chat.id, update.effective_user.id, reason="manual")
        
        await query.answer("✅ 笔记已保存")
        
        # 删除原消息（包含按钮）
        try:
            await query.message.delete()
        except Exception:
            pass  # 消息可能已被删除
        
        logger.info("Note mode finished via button")
        
    except Exception as e:
        logger.error(f"Error handling note finish callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_continue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle note continue button click - 继续记录笔记，忽略命令
    
    Callback data format: note_continue
    """
    query = update.callback_query
    
    try:
        # 清除待处理的命令
        if 'pending_command' in context.user_data:
            del context.user_data['pending_command']
        
        await query.answer("✍️ 继续记录笔记")
        await query.message.delete()
        
        await query.message.reply_text(
            "✍️ 已继续笔记模式\n\n"
            "💬 继续发送消息进行记录"
        )
        
        logger.info("User chose to continue note mode")
        
    except Exception as e:
        logger.error(f"Error handling note continue callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle add note button click - 提示用户输入笔记内容
    
    Callback data format: note_add:archive_id
    """
    query = update.callback_query
    
    try:
        archive_id = int(query.data.split(':')[1])
        
        # 设置用户状态，等待笔记输入
        context.user_data['waiting_note_for_archive'] = archive_id
        
        await query.answer("📝 请回复此消息输入笔记")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💬 请回复此消息输入笔记内容\n\n将为归档 #{archive_id} 添加笔记",
            reply_to_message_id=query.message.message_id
        )
        
        logger.info(f"User waiting to add note for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note add callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle edit note button click - 显示修改和追加选项
    
    Callback data format: note_edit:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 显示修改和追加选项
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("✏️ 修改笔记", callback_data=f"note_modify:{archive_id}:{note_id}")],
            [InlineKeyboardButton("➕ 追加笔记", callback_data=f"note_append:{archive_id}:{note_id}")],
            [InlineKeyboardButton("✖️ 取消", callback_data=f"note_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        from ...utils.message_builder import MessageBuilder
        prompt_text = MessageBuilder.format_note_input_prompt(archive_id, 'edit_menu')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=prompt_text,
            reply_markup=reply_markup
        )
        
        logger.info(f"Showing edit options for note {note_id}")
        
    except Exception as e:
        logger.error(f"Error handling note edit callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_modify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle modify note - 复制笔记内容供用户修改
    
    Callback data format: note_modify:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 获取笔记内容
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 获取笔记
        notes = note_manager.get_notes(archive_id)
        note_content = None
        for note in notes:
            if note['id'] == note_id:
                note_content = note['content']
                break
        
        if not note_content:
            await query.answer("笔记不存在", show_alert=True)
            return
        
        # 设置等待状态（修改模式）
        context.user_data['waiting_note_for_archive'] = archive_id
        context.user_data['note_modify_mode'] = True
        context.user_data['note_id_to_modify'] = note_id
        
        await query.answer("📋 笔记内容已发送")
        
        # 发送当前笔记内容供用户复制修改
        from ...utils.message_builder import MessageBuilder
        prompt_text = MessageBuilder.format_note_input_prompt(archive_id, 'modify', note_content)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=prompt_text,
            reply_to_message_id=query.message.message_id
        )
        
        logger.info(f"User modifying note {note_id} for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note modify callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_append_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle append note - 追加内容到现有笔记
    
    Callback data format: note_append:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 设置等待状态（追加模式）
        context.user_data['waiting_note_for_archive'] = archive_id
        context.user_data['note_append_mode'] = True
        context.user_data['note_id_to_append'] = note_id
        
        await query.answer("➕ 请输入要追加的内容")
        
        from ...utils.message_builder import MessageBuilder
        prompt_text = MessageBuilder.format_note_input_prompt(archive_id, 'append')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=prompt_text,
            reply_to_message_id=query.message.message_id
        )
        
        logger.info(f"User appending to note {note_id} for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note append callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle share note - 发送格式化的笔记供用户转发分享
    
    Callback data format: note_share:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 获取笔记内容
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 获取笔记
        notes = note_manager.get_notes(archive_id)
        note_content = None
        note_created_at = None
        for note in notes:
            if note['id'] == note_id:
                note_content = note['content']
                note_created_at = note['created_at']
                break
        
        if not note_content:
            await query.answer("笔记不存在", show_alert=True)
            return
        
        # 获取存档信息（用于显示标题等）
        db_storage = context.bot_data.get('db_storage')
        archive_info = None
        if db_storage:
            archive_info = db_storage.get_archive(archive_id)
        
        # 构建分享消息
        from ...utils.message_builder import MessageBuilder
        archive_title = archive_info.get('title') if archive_info else None
        share_text = MessageBuilder.format_note_share(
            note_content, note_created_at, archive_id, archive_title
        )
        
        await query.answer("📤 笔记已发送，可直接转发")
        
        # 发送格式化的笔记消息
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=share_text
        )
        
        logger.info(f"Shared note {note_id} from archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note share callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle delete note button click
    
    Callback data format: note_delete:note_id
    """
    query = update.callback_query
    
    try:
        note_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 删除笔记
        success = note_manager.delete_note(note_id)
        
        if success:
            await query.answer("✅ 笔记已删除")
            # 删除显示笔记的消息
            try:
                await query.message.delete()
            except Exception as e:
                logger.debug(f"Failed to delete note message: {e}")
            logger.info(f"Deleted note {note_id}")
        else:
            await query.answer("❌ 删除失败", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling note delete callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_quick_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle quick edit button click - 编辑笔记
    返回笔记纯文本，等待下一条消息替换内容
    
    Callback data format: note_quick_edit:note_id
    """
    query = update.callback_query
    
    try:
        note_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 获取笔记内容
        note = note_manager.get_note(note_id)
        if not note:
            await query.answer("❌ 笔记不存在", show_alert=True)
            return
        
        # 设置编辑模式
        context.user_data['note_edit_mode'] = True
        context.user_data['note_id_to_edit'] = note_id
        
        # 返回笔记纯文本（易于复制）
        await query.answer("✏️ 进入编辑模式")
        
        # 发送纯文本笔记内容
        from ...utils.message_builder import MessageBuilder
        prompt_text = MessageBuilder.format_note_input_prompt(0, 'quick_edit', note['content'])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=prompt_text
        )
        
        logger.info(f"User entered edit mode for note {note_id}")
        
    except Exception as e:
        logger.error(f"Error handling note quick edit: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_quick_append_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle quick append button click - 追加笔记
    等待下一条消息追加到笔记末尾
    
    Callback data format: note_quick_append:note_id
    """
    query = update.callback_query
    
    try:
        note_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 检查笔记是否存在
        note = note_manager.get_note(note_id)
        if not note:
            await query.answer("❌ 笔记不存在", show_alert=True)
            return
        
        # 设置追加模式
        context.user_data['note_append_mode'] = True
        context.user_data['note_id_to_append'] = note_id
        
        await query.answer("➕ 进入追加模式")
        
        # 提示用户
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="💬 请发送要追加的内容"
        )
        
        logger.info(f"User entered append mode for note {note_id}")
        
    except Exception as e:
        logger.error(f"Error handling note quick append: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_quick_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle quick delete button click - 删除笔记确认
    
    Callback data format: note_quick_delete:note_id
    """
    query = update.callback_query
    
    try:
        note_id = int(query.data.split(':')[1])
        
        # 显示确认对话框
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认删除", callback_data=f"note_quick_delete_confirm:{note_id}"),
                InlineKeyboardButton("❌ 取消", callback_data="note_close")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ 确认要删除笔记 #{note_id} 吗？\n\n删除后可在回收站中恢复",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error handling note quick delete: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_quick_delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle confirmed delete - 执行删除
    
    Callback data format: note_quick_delete_confirm:note_id
    """
    query = update.callback_query
    
    try:
        note_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 执行软删除
        success = note_manager.delete_note(note_id)
        
        if success:
            await query.answer("✅ 笔记已删除")
            await query.edit_message_text(
                f"✅ 笔记 #{note_id} 已删除\n\n💡 可在回收站中恢复"
            )
            logger.info(f"Deleted note {note_id}")
        else:
            await query.answer("❌ 删除失败", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling note quick delete confirm: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_continuity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle continuity callback - 5分钟追加连贯性
    
    Callback data formats:
    - continuity:append:note_id - 追加到笔记
    - continuity:new_note - 创建新笔记
    - continuity:archive - 正常归档
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        action = parts[1]
        
        # 获取待处理文本
        pending_text = context.user_data.get('pending_continuity_text')
        if not pending_text:
            await query.answer("❌ 未找到待处理文本", show_alert=True)
            return
        
        if action == 'append':
            # 追加到笔记
            note_id = int(parts[2])
            
            note_manager = context.bot_data.get('note_manager')
            if not note_manager:
                await query.answer("笔记管理器未初始化", show_alert=True)
                return
            
            # 获取笔记内容
            note = note_manager.get_note(note_id)
            if not note:
                await query.answer("❌ 笔记不存在", show_alert=True)
                return
            
            # 追加内容
            new_content = f"{note['content']}\n\n---\n\n{pending_text}"
            success = note_manager.update_note(note_id, new_content)
            
            if success:
                await query.answer("✅ 已追加到笔记")
                await query.edit_message_text(
                    f"✅ 内容已追加到笔记 #{note_id}"
                )
                
                # 更新时间窗口
                from datetime import datetime
                context.user_data['last_note_id'] = note_id
                context.user_data['last_note_time'] = datetime.now()
                
                logger.info(f"Continuity: appended to note {note_id}")
            else:
                await query.answer("❌ 追加失败", show_alert=True)
        
        elif action == 'new_note':
            # 创建新笔记
            note_manager = context.bot_data.get('note_manager')
            if not note_manager:
                await query.answer("笔记管理器未初始化", show_alert=True)
                return
            
            # 创建笔记
            note_id = note_manager.add_note(None, pending_text)
            
            if note_id:
                await query.answer("✅ 已创建新笔记")
                await query.edit_message_text(
                    f"✅ 笔记已保存\n📝 笔记 #{note_id}"
                )
                
                # 更新时间窗口
                from datetime import datetime
                context.user_data['last_note_id'] = note_id
                context.user_data['last_note_time'] = datetime.now()
                
                logger.info(f"Continuity: created new note {note_id}")
            else:
                await query.answer("❌ 创建失败", show_alert=True)
        
        elif action == 'archive':
            # 正常归档流程
            await query.answer("📦 进入归档流程")
            await query.message.delete()
            
            # 清除pending_continuity_text，让消息进入正常归档流程
            # 由于回调无法触发handle_message，需要告知用户重新发送
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💡 请重新发送消息以进行归档"
            )
            
            logger.info("Continuity: user chose normal archive")
        
        # 清除待处理文本
        context.user_data.pop('pending_continuity_text', None)
        
    except Exception as e:
        logger.error(f"Error handling continuity callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_refine_note_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle refine note button click - prompts user for refinement instructions
    
    Callback data format: refine_note:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # Parse archive_id from callback data
        archive_id = int(query.data.split(':')[1])
        
        # Check if AI is available
        ai_summarizer = context.bot_data.get('ai_summarizer')
        if not ai_summarizer or not ai_summarizer.is_available():
            await query.answer("❌ AI功能未启用", show_alert=True)
            return
        
        # Get existing notes
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        notes = note_manager.get_notes(archive_id)
        if not notes:
            await query.answer("❌ 该归档没有笔记", show_alert=True)
            return
        
        # Store context for next message
        context.user_data['refine_note_context'] = {
            'archive_id': archive_id,
            'notes': notes,
            'waiting_for_instruction': True
        }
        
        # Format existing notes
        notes_text = "\n\n".join([f"📝 {note['content']}" for note in notes])
        
        # HTML转义
        import html
        notes_text_escaped = html.escape(truncate_text(notes_text, 200))
        
        # Prompt user for refinement instructions
        await query.edit_message_text(
            f"✨ <b>精炼笔记</b>\n\n"
            f"当前笔记：\n{notes_text_escaped}\n\n"
            f"📨 请告诉我你想怎么改？\n\n"
            f"例如：\n"
            f"• 缩短\n"
            f"• 展开\n"
            f"• 改写成要点\n"
            f"• 翻译成英文\n"
            f"• 其他指令...",
            parse_mode=ParseMode.HTML
        )
        
        await query.answer("💡 请发送你的指令")
        logger.info(f"User requested note refinement for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling refine note callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_notes_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理笔记列表分页
    
    Callback data format: notes_page:页码
    """
    query = update.callback_query
    
    try:
        # 解析页码
        page = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 获取总数
        total_count = note_manager.get_notes_count()
        
        # 获取当前页笔记
        page_size = 10
        notes = note_manager.get_all_notes(limit=page_size, offset=page * page_size)
        
        if not notes:
            await query.answer("没有更多笔记了", show_alert=True)
            return
        
        # 获取配置
        config = get_config()
        
        # 格式化笔记列表
        from ...utils.message_builder import MessageBuilder
        result_text, reply_markup = MessageBuilder.format_notes_list(
            notes=notes,
            config=config,
            lang_ctx=lang_ctx,
            page=page,
            total_count=total_count
        )
        
        # 更新消息
        await query.answer()
        await query.edit_message_text(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        logger.info(f"Notes page {page} displayed")
        
    except Exception as e:
        logger.error(f"Error handling notes page callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)
