"""
AI Chat Mode Handler (重构版)
处理AI对话模式的UI交互层 - 薄壳设计
业务逻辑已移至 src/ai/chat_router.py
"""

import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...core.ai_session import get_session_manager
from ...ai.chat_router import (
    should_trigger_ai_chat,
    detect_message_intent,
    process_ai_chat
)
from ...utils.config import get_config
from ...utils.helpers import is_url
from ...utils.message_builder import MessageBuilder
from ...utils.i18n import I18n

logger = logging.getLogger(__name__)


async def handle_ai_chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> bool:
    """
    处理AI对话模式 (重构版 - UI层薄壳)
    
    Args:
        update: Telegram update
        context: Bot context  
        lang_ctx: Language context
        
    Returns:
        bool: 如果处理了AI对话返回True，否则返回False
    """
    message = update.message
    text = message.text.strip() if message.text else ""
    
    # 批次检测：如果消息属于媒体组或可能是批次消息的一部分，不触发AI Chat
    # 这些消息应该由批次处理器统一处理
    if message.media_group_id:
        logger.debug(f"Message belongs to media_group, skip AI chat")
        return False
    
    # 如果消息有媒体附件（图片、视频等），可能是转发+评论的场景
    # 应该让批次处理器处理
    if any([message.photo, message.video, message.document, 
            message.audio, message.voice, message.animation,
            message.sticker, message.contact, message.location]):
        logger.debug(f"Message has media attachment, skip AI chat")
        return False
    
    # 获取配置和会话管理器
    config = get_config()
    ai_config = config.ai
    session_manager = get_session_manager(
        ttl_seconds=ai_config.get('chat_session_ttl_seconds', 600)
    )
    user_id = str(message.from_user.id)
    session = session_manager.get_session(user_id)
    
    # 情况1：用户已在AI会话中
    if session:
        return await _handle_existing_session(
            message, context, lang_ctx, text, 
            session, session_manager, user_id, config
        )
    
    # 情况2：判断是否应触发AI会话
    should_trigger, reason = should_trigger_ai_chat(message, context, config)
    
    if should_trigger:
        return await _handle_auto_trigger(
            message, context, lang_ctx, text,
            session_manager, user_id
        )
    
    # 情况3：5分钟追加连贯性检测（仅对文本消息）
    if await _handle_continuity_check(message, context, lang_ctx):
        return True
    
    # 情况4：URL检测 - 已在should_trigger_ai_chat中处理
    if reason == 'url_detected':
        logger.info(f"Detected URL, processing as link archive: {text[:50]}")
        return False
    
    # 情况5：短文本处理
    from ...utils.helpers import should_create_note
    is_short, note_type = should_create_note(text)
    if is_short:
        return await _handle_short_text(message, context, lang_ctx, text)
    
    return False


async def _handle_existing_session(
    message, context, lang_ctx, text, 
    session, session_manager, user_id, config
) -> bool:
    """
    处理已存在的AI会话 (重构版 - 使用detect_message_intent)
    """
    # 检测消息意图
    intent = detect_message_intent(text, lang_ctx.language, config, has_active_session=True)
    
    # 长文本意图 - 提示用户选择
    if intent['type'] == 'long_text_in_session':
        await _show_long_text_intent_prompt(
            message, lang_ctx, intent['length'], 
            session, session_manager, user_id
        )
        return True
    
    # 正常长度，处理AI对话
    return await _process_ai_message(
        message, context, lang_ctx, session, session_manager, user_id
    )


async def _handle_auto_trigger(
    message, context, lang_ctx, text,
    session_manager, user_id
) -> bool:
    """
    自动触发AI会话 (重构版 - 复用process_ai_chat)
    """
    # 自动创建AI会话
    session = session_manager.create_session(user_id)
    logger.info(f"AI chat session auto-created for user {user_id}")
    
    # 处理AI消息
    return await _process_ai_message(
        message, context, lang_ctx, session, session_manager, user_id
    )


async def _process_ai_message(
    message, context, lang_ctx, session, session_manager, user_id
) -> bool:
    """
    统一的AI消息处理入口 (新增 - 消除重复代码)
    """
    try:
        # 发送AI处理进度提示
        progress_msg = await message.reply_text(f"🤖 {lang_ctx.t('ai_chat_understanding')}")
        
        # 进度更新回调
        async def update_ai_progress(stage: str):
            try:
                await progress_msg.edit_text(f"🤖 {stage}")
            except Exception:
                pass
        
        # 调用统一的AI处理流程
        success, ai_response = await process_ai_chat(
            message, session, context, lang_ctx, update_ai_progress
        )
        
        if not success:
            await message.reply_text(lang_ctx.t('ai_chat_error_session_end'))
            session_manager.clear_session(user_id)
            return False
        
        # 检测是否为资源回复（JSON格式）
        if await _handle_resource_response(
            ai_response, message, context, lang_ctx, 
            progress_msg, session_manager, user_id, session
        ):
            return True
        
        # 检测是否有待确认的写操作（Phase 2）
        if 'pending_confirmation_message' in context.user_data and 'pending_confirmation_id' in context.user_data:
            confirmation_msg = context.user_data.pop('pending_confirmation_message')
            confirmation_id = context.user_data.pop('pending_confirmation_id')
            
            # 显示确认对话框
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ 确认执行" if lang_ctx.language.startswith('zh') else "✅ Confirm",
                        callback_data=f"ai_confirm:{confirmation_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ 取消" if lang_ctx.language.startswith('zh') else "❌ Cancel",
                        callback_data=f"ai_cancel:{confirmation_id}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 删除进度消息，发送确认消息
            try:
                await progress_msg.delete()
            except Exception as e:
                logger.debug(f"Failed to delete progress message: {e}")
            
            await message.reply_text(confirmation_msg, reply_markup=reply_markup)
            logger.info(f"Write operation confirmation sent for {confirmation_id}")
            return True
        
        # 编辑消息为最终回复（正常文本）
        await progress_msg.edit_text(f"🤖 {ai_response}")
        
        # 更新会话（保存上下文）
        session_manager.update_session(user_id, session.get('context', {}))
        
        logger.info(f"AI chat response sent to user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        await message.reply_text(lang_ctx.t('ai_chat_error_session_end'))
        session_manager.clear_session(user_id)
        return False


async def _show_long_text_intent_prompt(
    message, lang_ctx, text_length, session, session_manager, user_id
) -> None:
    """
    显示长文本意图选择提示 (新增 - 提取UI逻辑)
    """
    text = message.text.strip()
    
    # 使用i18n获取文本
    prompt_text = lang_ctx.t('long_text_intent_prompt', length=text_length)
    note_btn_text = lang_ctx.t('long_text_save_note')
    chat_btn_text = lang_ctx.t('long_text_continue_chat')
    
    keyboard = [
        [
            InlineKeyboardButton(note_btn_text, callback_data=f"longtxt_note:{message.message_id}"),
            InlineKeyboardButton(chat_btn_text, callback_data=f"longtxt_chat:{message.message_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(prompt_text, reply_markup=reply_markup)
    
    # 暂存消息内容，等待用户选择
    if 'pending_long_text' not in session.get('context', {}):
        session['context']['pending_long_text'] = {}
    session['context']['pending_long_text'][str(message.message_id)] = text
    session_manager.update_session(user_id, session.get('context', {}))
    
    logger.info(f"Long text detected ({text_length} chars), awaiting user choice")


async def _handle_resource_response(
    ai_response, message, context, lang_ctx,
    progress_msg, session_manager, user_id, session
) -> bool:
    """
    处理资源回复（JSON格式的响应）
    合并版：直接使用MessageBuilder统一处理
    """
    try:
        response_data = json.loads(ai_response)
        if response_data.get('type') != 'resources':
            return False
        
        strategy = response_data.get('strategy')
        resources = response_data.get('items', [])
        count = response_data.get('count', 0)
        
        # 删除进度消息
        try:
            await progress_msg.delete()
        except Exception as e:
            logger.debug(f"Failed to delete progress message: {e}")
        
        # 统一调用资源发送函数
        await _send_resources(message, context, lang_ctx, strategy, resources, count)
        
        # 更新会话
        session_manager.update_session(user_id, session.get('context', {}))
        logger.info(f"AI chat {strategy} resource(s) sent to user {user_id}")
        return True
        
    except (json.JSONDecodeError, ValueError):
        # 不是JSON，正常文本回复
        return False


async def _send_resources(message, context, lang_ctx, strategy: str, resources: list, count: int):
    """
    统一的资源发送函数（合并single和list逻辑）
    """
    if not resources:
        return
    
    # 获取公共数据
    note_manager = context.bot_data.get('note_manager')
    db_storage = context.bot_data.get('db_storage')
    db = db_storage.db if db_storage else None
    
    if strategy == 'single':
        # 单个资源：使用MessageBuilder的完整展示
        resource = resources[0]
        content_type = resource.get('content_type', '')
        notes = note_manager.get_notes(resource.get('id')) if note_manager else []
        
        # 媒体类型
        if content_type in ['photo', 'video', 'audio', 'voice', 'animation']:
            caption = MessageBuilder.format_media_archive_caption(resource, notes, max_length=200)
            result = await MessageBuilder.send_archive_resource(
                context.bot, message.chat_id, resource, caption=caption
            )
            if result:
                buttons = MessageBuilder.build_media_archive_buttons(resource, has_notes=bool(notes))
                await message.reply_text("👆 资源已发送", reply_markup=buttons)
            else:
                await message.reply_text(lang_ctx.t('resource_send_failed'))
        
        # 文本类型
        elif content_type in ['text', 'article']:
            text, reply_markup = MessageBuilder.format_text_archive_reply(resource, notes, db)
            await message.reply_text(text, reply_markup=reply_markup, 
                                    parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
        # 其他类型
        else:
            text, reply_markup = MessageBuilder.format_other_archive_reply(resource, bool(notes))
            await message.reply_text(text, reply_markup=reply_markup,
                                    parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    elif strategy == 'list':
        # 多个资源：使用列表格式
        i18n = I18n(lang_ctx.language)
        list_text = MessageBuilder.format_archive_list(resources, i18n, db_instance=db, with_links=True)
        
        # i18n标题
        header_key = {
            'en': f"🔍 Found {count} resource(s):\n\n",
            'zh-TW': f"🔍 找到 {count} 個資源：\n\n",
            'zh-CN': f"🔍 找到 {count} 个资源：\n\n"
        }.get(lang_ctx.language, f"🔍 找到 {count} 个资源：\n\n")
        
        await message.reply_text(header_key + list_text, parse_mode=ParseMode.HTML, 
                                disable_web_page_preview=True)


async def _handle_continuity_check(message, context, lang_ctx) -> bool:
    """5分钟追加连贯性检测（精简版）"""
    last_note_id = context.user_data.get('last_note_id')
    last_note_time = context.user_data.get('last_note_time')
    
    if not (last_note_id and last_note_time and message.text):
        return False
    
    # 检查5分钟窗口
    time_diff = datetime.now() - last_note_time
    if time_diff.total_seconds() >= 300:
        return False
    
    # 保存待处理文本
    context.user_data['pending_continuity_text'] = message.text
    
    # 计算剩余时间显示
    remaining_seconds = int(300 - time_diff.total_seconds())
    time_str = f"{remaining_seconds // 60}分{remaining_seconds % 60}秒"
    
    # 显示按钮提示
    keyboard = [
        [InlineKeyboardButton(lang_ctx.t('continuity_append'), 
                            callback_data=f"continuity:append:{last_note_id}")],
        [InlineKeyboardButton(lang_ctx.t('continuity_new_note'), callback_data="continuity:new_note"),
         InlineKeyboardButton(lang_ctx.t('continuity_archive'), callback_data="continuity:archive")]
    ]
    
    await message.reply_text(
        lang_ctx.t('continuity_prompt', time=time_str, note_id=last_note_id),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    logger.info(f"Continuity prompt shown for note {last_note_id}")
    return True


async def _handle_short_text(message, context, lang_ctx, text) -> bool:
    """处理短文本（精简版）"""
    from ...utils.helpers import should_create_note
    
    is_short, note_type = should_create_note(text)
    if not is_short:
        return False
    
    config = get_config()
    short_text_threshold = int(config.ai.get('text_thresholds', {}).get('short_text', 50))
    
    # 非常短的文本 - 询问意图
    if len(text) < short_text_threshold:
        context.user_data['pending_short_text'] = text
        
        keyboard = [
            [InlineKeyboardButton(lang_ctx.t('button_save_as_note'), callback_data="short_text:note"),
             InlineKeyboardButton(lang_ctx.t('button_archive_content'), callback_data="short_text:archive")]
        ]
        
        await message.reply_text(lang_ctx.t('short_text_prompt'), 
                                reply_markup=InlineKeyboardMarkup(keyboard))
        logger.info(f"Asking user intent for short text: {text[:30]}")
        return True
    
    # 达到阈值的短文本 - 直接保存为笔记
    note_manager = context.bot_data.get('note_manager')
    if note_manager:
        note_id = note_manager.add_note(None, text)
        if note_id:
            await message.reply_text(lang_ctx.t('short_text_saved_note', note_id=note_id))
            logger.info(f"Short text saved as standalone note: {note_id}")
        else:
            await message.reply_text(lang_ctx.t('note_add_failed'))
    return True
