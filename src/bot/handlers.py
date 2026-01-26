"""
Message handlers - Main Entry Point
Handles incoming messages for archiving
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.language_context import get_language_context
from .message_aggregator import MessageAggregator
from ..core.ai_session import get_session_manager
from ..ai.chat_router import handle_chat_message

# Import helper functions from submodules
from .handlers import (
    _cleanup_user_data,
    _process_single_message,
    _batch_callback,
    _handle_note_mode_message,
    _finalize_note_internal,
    _is_media_message,
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
                            await message.reply_text(lang_ctx.t('note_added_to_archive', archive_id=archive_id, note_id=note_id))
                            logger.info(f"Added note {note_id} to archive {archive_id}")
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
                        
                        # 调用AI
                        refined_content = await ai_summarizer.summarize_content(
                            content=refine_prompt,
                            content_type='note_refinement',
                            max_tokens=500,
                            language=lang_ctx.language
                        )
                        
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

        
        # AI Chat Mode - 如果用户已在AI会话中，优先处理
        # 但是，如果用户正在进行其他特殊模式操作（笔记编辑/追加等），则跳过AI Chat
        if message.text and not message.forward_origin:
            text = message.text.strip()
            
            # 检查是否有其他特殊模式正在进行
            # 这些模式已经在上面处理并return了，但为了安全，这里再检查一次
            has_other_mode = (
                context.user_data.get('waiting_note_for_archive') or
                context.user_data.get('note_modify_mode') or
                context.user_data.get('note_append_mode') or
                (context.user_data.get('refine_note_context') and 
                 context.user_data['refine_note_context'].get('waiting_for_instruction'))
            )
            
            if not has_other_mode:
                from ..utils.config import get_config
                config = get_config()
                ai_config = config.ai
                
                # 检查AI模式是否启用
                chat_enabled = bool(ai_config.get('chat_enabled', False))
                
                # 从配置获取文本阈值
                text_thresholds = ai_config.get('text_thresholds', {})
                short_text_threshold = int(text_thresholds.get('short_text', 50))
            
                if chat_enabled:
                # 检查是否已有活跃会话
                    session_manager = get_session_manager(
                        ttl_seconds=ai_config.get('chat_session_ttl_seconds', 600)
                    )
                    user_id = str(message.from_user.id)
                    session = session_manager.get_session(user_id)
                
                    if session:
                        # 用户已在AI会话中，检查是否为长文本（可能是笔记意图）
                        # 使用note阈值作为长文本判断标准
                        long_text_threshold = int(text_thresholds.get('note_chinese', 150))
                    
                        if len(text) >= long_text_threshold:
                            # 长文本，提示用户选择意图
                            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        
                            if lang_ctx.language == 'en':
                                prompt_text = f"📝 You sent {len(text)} characters. What do you want to do?"
                                note_btn_text = "📝 Save as Note"
                                chat_btn_text = "💬 Continue Chat"
                            elif lang_ctx.language in ['zh-TW', 'zh-HK', 'zh-MO']:
                                prompt_text = f"📝 您發送了 {len(text)} 個字符。您想做什麼？"
                                note_btn_text = "📝 記錄為筆記"
                                chat_btn_text = "💬 繼續對話"
                            else:
                                prompt_text = f"📝 您发送了 {len(text)} 个字符。您想做什么？"
                                note_btn_text = "📝 记录为笔记"
                                chat_btn_text = "💬 继续对话"
                        
                            keyboard = [
                                [
                                    InlineKeyboardButton(note_btn_text, callback_data=f"longtxt_note:{message.message_id}"),
                                    InlineKeyboardButton(chat_btn_text, callback_data=f"longtxt_chat:{message.message_id}")
                                ]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                        
                            await message.reply_text(
                                prompt_text,
                                reply_markup=reply_markup
                            )
                        
                            # 暂存消息内容，等待用户选择
                            if 'pending_long_text' not in session.get('context', {}):
                                session['context']['pending_long_text'] = {}
                            session['context']['pending_long_text'][str(message.message_id)] = text
                            session_manager.update_session(user_id, session.get('context', {}))
                        
                            logger.info(f"Long text detected ({len(text)} chars), awaiting user choice")
                            return
                    
                        # 正常长度，处理消息
                        try:
                            # 发送AI处理进度提示
                            progress_msg = await message.reply_text(f"🤖 {lang_ctx.t('ai_chat_understanding')}")
                        
                            # 包装handle_chat_message，添加进度回调
                            async def update_ai_progress(stage: str):
                                try:
                                    await progress_msg.edit_text(f"🤖 {stage}")
                                except Exception:
                                    pass
                        
                            # Stage 1: 理解需求
                            await update_ai_progress(lang_ctx.t('ai_chat_analyzing'))
                        
                            # 调用AI处理（内部有3个阶段）
                            # 使用'auto'让AI自动判断回复语言，不受界面语言约束
                            ai_response = await handle_chat_message(text, session, context, 'auto', update_ai_progress)
                        
                            # 检测是否为资源回复（JSON格式）
                            import json
                            try:
                                response_data = json.loads(ai_response)
                                if response_data.get('type') == 'resources':
                                    # 资源回复模式
                                    from ..utils.message_builder import MessageBuilder
                                    from ..utils.i18n import I18n
                                
                                    strategy = response_data.get('strategy')
                                    resources = response_data.get('items', [])
                                    count = response_data.get('count', 0)
                                
                                    # 删除进度消息
                                    try:
                                        await progress_msg.delete()
                                    except:
                                        pass
                                
                                    if strategy == 'single' and resources:
                                        # 单个资源，根据类型决定发送方式
                                        resource = resources[0]
                                        content_type = resource.get('content_type', '')
                                        
                                        # 获取笔记
                                        note_manager = context.bot_data.get('note_manager')
                                        notes = []
                                        if note_manager:
                                            notes = note_manager.get_notes(resource.get('id'))
                                        
                                        # 媒体类型：发送实体+caption+按钮
                                        if content_type in ['photo', 'video', 'audio', 'voice', 'animation']:
                                            # 构建caption
                                            caption = MessageBuilder.format_media_archive_caption(resource, notes, max_length=200)
                                            
                                            # 发送资源
                                            result = await MessageBuilder.send_archive_resource(
                                                context.bot,
                                                message.chat_id,
                                                resource,
                                                caption=caption
                                            )
                                            
                                            if result:
                                                # 发送操作按钮
                                                buttons = MessageBuilder.build_media_archive_buttons(resource, has_notes=bool(notes))
                                                await message.reply_text(
                                                    "👆 资源已发送",
                                                    reply_markup=buttons
                                                )
                                            else:
                                                await message.reply_text(lang_ctx.t('resource_send_failed') if hasattr(lang_ctx, 't') else "发送资源失败")
                                        
                                        # 文本类型：使用文本存档格式
                                        elif content_type in ['text', 'article']:
                                            db_storage = context.bot_data.get('db_storage')
                                            db = db_storage.db if db_storage else None
                                            text, reply_markup = MessageBuilder.format_text_archive_reply(resource, notes, db)
                                            await message.reply_text(
                                                text,
                                                reply_markup=reply_markup,
                                                parse_mode=ParseMode.HTML,
                                                disable_web_page_preview=True
                                            )
                                        
                                        # 其他类型：使用其他存档格式
                                        else:
                                            has_notes = bool(notes)
                                            text, reply_markup = MessageBuilder.format_other_archive_reply(resource, has_notes)
                                            await message.reply_text(
                                                text,
                                                reply_markup=reply_markup,
                                                parse_mode=ParseMode.HTML,
                                                disable_web_page_preview=True
                                            )
                                
                                    elif strategy == 'list' and resources:
                                        # 多个资源，显示列表
                                        db_storage = context.bot_data.get('db_storage')
                                        db = db_storage.db if db_storage else None
                                    
                                        i18n = I18n(lang_ctx.language if hasattr(lang_ctx, 'language') else 'zh-CN')
                                        list_text = MessageBuilder.format_archive_list(
                                            resources,
                                            i18n,
                                            db_instance=db,
                                            with_links=True
                                        )
                                    
                                        # 添加标题
                                        if lang_ctx.language == 'en':
                                            header = f"🔍 Found {count} resource(s):\n\n"
                                        elif lang_ctx.language == 'zh-TW':
                                            header = f"🔍 找到 {count} 個資源：\n\n"
                                        else:
                                            header = f"🔍 找到 {count} 个资源：\n\n"
                                    
                                        final_text = header + list_text
                                    
                                        await message.reply_text(
                                            final_text,
                                            parse_mode=ParseMode.HTML,
                                            disable_web_page_preview=True
                                        )
                                
                                    # 更新会话
                                    session_manager.update_session(user_id, session.get('context', {}))
                                    logger.info(f"AI chat {strategy} resource(s) sent to user {user_id}")
                                    return
                                
                            except (json.JSONDecodeError, ValueError):
                                # 不是JSON，正常文本回复
                                pass
                        
                            # 编辑消息为最终回复（正常文本）
                            await progress_msg.edit_text(f"🤖 {ai_response}")
                        
                            # 更新会话（保存上下文）
                            session_manager.update_session(user_id, session.get('context', {}))
                        
                            logger.info(f"AI chat response sent to user {user_id}")
                            return
                        
                        except Exception as e:
                            logger.error(f"AI chat error: {e}", exc_info=True)
                            await message.reply_text(lang_ctx.t('ai_chat_error_session_end'))
                            session_manager.clear_session(user_id)
                            # 继续正常归档流程
                
                    # 检查是否应自动触发AI会话（短消息且无media）
                    elif (len(text) < short_text_threshold and 
                          not message.media_group_id and
                          not message.photo and 
                          not message.document and 
                          not message.video and
                          not message.audio):
                    
                        # 自动创建AI会话
                        session = session_manager.create_session(user_id)
                        logger.info(f"AI chat session auto-created for user {user_id}")
                    
                        try:
                            # 发送AI处理进度提示
                            progress_msg = await message.reply_text(f"🤖 {lang_ctx.t('ai_chat_understanding')}")
                        
                            # 进度更新回调
                            async def update_ai_progress(stage: str):
                                try:
                                    await progress_msg.edit_text(f"🤖 {stage}")
                                except Exception:
                                    pass
                        
                            # Stage 1: 理解需求
                            await update_ai_progress(lang_ctx.t('ai_chat_analyzing'))
                        
                            # 使用'auto'让AI自动判断回复语言
                            ai_response = await handle_chat_message(text, session, context, 'auto', update_ai_progress)
                        
                            # 检测是否为资源回复（JSON格式）
                            import json
                            try:
                                response_data = json.loads(ai_response)
                                if response_data.get('type') == 'resources':
                                    # 资源回复模式（同上）
                                    from ..utils.message_builder import MessageBuilder
                                    from ..utils.i18n import I18n
                                
                                    strategy = response_data.get('strategy')
                                    resources = response_data.get('items', [])
                                    count = response_data.get('count', 0)
                                
                                    try:
                                        await progress_msg.delete()
                                    except:
                                        pass
                                
                                    if strategy == 'single' and resources:
                                        # 单个资源，根据类型决定发送方式
                                        resource = resources[0]
                                        content_type = resource.get('content_type', '')
                                        
                                        # 获取笔记
                                        note_manager = context.bot_data.get('note_manager')
                                        notes = []
                                        if note_manager:
                                            notes = note_manager.get_notes(resource.get('id'))
                                        
                                        # 媒体类型：发送实体+caption+按钮
                                        if content_type in ['photo', 'video', 'audio', 'voice', 'animation']:
                                            caption = MessageBuilder.format_media_archive_caption(resource, notes, max_length=200)
                                            result = await MessageBuilder.send_archive_resource(
                                                context.bot,
                                                message.chat_id,
                                                resource,
                                                caption=caption
                                            )
                                            
                                            if result:
                                                buttons = MessageBuilder.build_media_archive_buttons(resource, has_notes=bool(notes))
                                                await message.reply_text("👆 资源已发送", reply_markup=buttons)
                                            else:
                                                await message.reply_text("发送资源失败")
                                        
                                        # 文本类型：使用文本存档格式
                                        elif content_type in ['text', 'article']:
                                            db_storage = context.bot_data.get('db_storage')
                                            db = db_storage.db if db_storage else None
                                            text, reply_markup = MessageBuilder.format_text_archive_reply(resource, notes, db)
                                            await message.reply_text(
                                                text,
                                                reply_markup=reply_markup,
                                                parse_mode=ParseMode.HTML,
                                                disable_web_page_preview=True
                                            )
                                        
                                        # 其他类型：使用其他存档格式
                                        else:
                                            has_notes = bool(notes)
                                            text, reply_markup = MessageBuilder.format_other_archive_reply(resource, has_notes)
                                            await message.reply_text(
                                                text,
                                                reply_markup=reply_markup,
                                                parse_mode=ParseMode.HTML,
                                                disable_web_page_preview=True
                                            )
                                
                                    elif strategy == 'list' and resources:
                                        db_storage = context.bot_data.get('db_storage')
                                        db = db_storage.db if db_storage else None
                                    
                                        i18n = I18n(lang_ctx.language if hasattr(lang_ctx, 'language') else 'zh-CN')
                                        list_text = MessageBuilder.format_archive_list(
                                            resources,
                                            i18n,
                                            db_instance=db,
                                            with_links=True
                                        )
                                    
                                        if lang_ctx.language == 'en':
                                            header = f"🔍 Found {count} resource(s):\n\n"
                                        elif lang_ctx.language == 'zh-TW':
                                            header = f"🔍 找到 {count} 個資源：\n\n"
                                        else:
                                            header = f"🔍 找到 {count} 个资源：\n\n"
                                    
                                        await message.reply_text(
                                            header + list_text,
                                            parse_mode=ParseMode.HTML,
                                            disable_web_page_preview=True
                                        )
                                
                                    session_manager.update_session(user_id, session.get('context', {}))
                                    logger.info(f"AI chat auto-triggered, {strategy} resource(s) sent")
                                    return
                                
                            except (json.JSONDecodeError, ValueError):
                                pass
                        
                            # 编辑消息为最终回复
                            await progress_msg.edit_text(f"🤖 {ai_response}")
                        
                            # 更新会话
                            session_manager.update_session(user_id, session.get('context', {}))
                        
                            logger.info(f"AI chat auto-triggered for user {user_id}")
                            return
                        
                        except Exception as e:
                            logger.error(f"AI chat error: {e}", exc_info=True)
                            await message.reply_text(lang_ctx.t('ai_chat_error'))
                            session_manager.clear_session(user_id)
                            # 继续正常归档流程
            
            # 5分钟追加连贯性检测（仅对文本消息）
            last_note_id = context.user_data.get('last_note_id')
            last_note_time = context.user_data.get('last_note_time')
            
            if last_note_id and last_note_time and message.text:
                # 计算时间差
                time_diff = datetime.now() - last_note_time
                
                # 如果在5分钟窗口内
                if time_diff.total_seconds() < 300:  # 5分钟 = 300秒
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    # 保存当前消息文本
                    context.user_data['pending_continuity_text'] = message.text
                    
                    # 提示用户选择
                    keyboard = [
                        [
                            InlineKeyboardButton("➕ 追加上一条笔记", callback_data=f"continuity:append:{last_note_id}"),
                        ],
                        [
                            InlineKeyboardButton("📝 创建新笔记", callback_data="continuity:new_note"),
                            InlineKeyboardButton("📦 正常归档", callback_data="continuity:archive")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # 计算剩余时间
                    remaining_seconds = int(300 - time_diff.total_seconds())
                    remaining_minutes = remaining_seconds // 60
                    remaining_secs = remaining_seconds % 60
                    
                    await message.reply_text(
                        f"💡 检测到您在 {remaining_minutes}分{remaining_secs}秒 前保存了笔记 #{last_note_id}\n\n"
                        f"这条消息是否要追加到该笔记？",
                        reply_markup=reply_markup
                    )
                    logger.info(f"Continuity prompt shown for note {last_note_id}")
                    return
            
            # 检测是否是 URL（单独的链接应该归档而非做笔记）
            from ..utils.helpers import is_url
            if is_url(text):
                # URL 作为链接归档，不走短文本笔记逻辑
                logger.info(f"Detected URL, processing as link archive: {text[:50]}")
                # 继续执行归档流程（不 return）
            else:
                # 判断是否是短文字
                from ..utils.helpers import should_create_note
                is_short, note_type = should_create_note(text)
                
                if is_short:
                    # 如果非常短（<short_text_threshold字符），询问用户意图
                    if len(text) < short_text_threshold:
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        
                        # 保存待处理文本到用户数据
                        context.user_data['pending_short_text'] = text
                        
                        keyboard = [
                            [
                                InlineKeyboardButton("📝 保存为笔记", callback_data="short_text:note"),
                                InlineKeyboardButton("📦 归档为内容", callback_data="short_text:archive")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await message.reply_text(
                            lang_ctx.t('short_text_prompt'),
                            reply_markup=reply_markup
                        )
                        logger.info(f"Asking user intent for short text: {text[:30]}")
                        return
                    
                    # 达到笔记阈值的短文本，直接保存为笔记
                    note_manager = context.bot_data.get('note_manager')
                    if note_manager:
                        note_id = note_manager.add_note(None, text)
                        if note_id:
                            await message.reply_text(lang_ctx.t('short_text_saved_note', note_id=note_id))
                            logger.info(f"Short text saved as standalone note: {note_id}")
                        else:
                            await message.reply_text(lang_ctx.t('note_add_failed'))
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
        except:
            pass
