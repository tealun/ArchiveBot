"""
AI Chat Mode Handler
处理AI对话模式相关逻辑
"""

import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...core.ai_session import get_session_manager
from ...ai.chat_router import handle_chat_message
from ...utils.config import get_config
from ...utils.helpers import is_url, should_create_note
from ...utils.message_builder import MessageBuilder
from ...utils.i18n import I18n

logger = logging.getLogger(__name__)


async def handle_ai_chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> bool:
    """
    处理AI对话模式
    
    Args:
        update: Telegram update
        context: Bot context  
        lang_ctx: Language context
        
    Returns:
        bool: 如果处理了AI对话返回True，否则返回False
    """
    message = update.message
    
    # 只处理文本消息且非转发消息
    if not message.text or message.forward_origin:
        return False
    
    text = message.text.strip()
    
    # 检查是否有其他特殊模式正在进行
    has_other_mode = (
        context.user_data.get('waiting_note_for_archive') or
        context.user_data.get('note_modify_mode') or
        context.user_data.get('note_append_mode') or
        (context.user_data.get('refine_note_context') and 
         context.user_data['refine_note_context'].get('waiting_for_instruction'))
    )
    
    if has_other_mode:
        return False
    
    # 获取配置
    config = get_config()
    ai_config = config.ai
    
    # 检查AI模式是否启用
    chat_enabled = bool(ai_config.get('chat_enabled', False))
    if not chat_enabled:
        return False
    
    # 从配置获取文本阈值
    text_thresholds = ai_config.get('text_thresholds', {})
    short_text_threshold = int(text_thresholds.get('short_text', 50))
    
    # 获取会话管理器
    session_manager = get_session_manager(
        ttl_seconds=ai_config.get('chat_session_ttl_seconds', 600)
    )
    user_id = str(message.from_user.id)
    session = session_manager.get_session(user_id)
    
    # 情况1：用户已在AI会话中
    if session:
        return await _handle_existing_session(
            message, context, lang_ctx, text, 
            session, session_manager, user_id, text_thresholds
        )
    
    # 情况2：检查是否应自动触发AI会话（短消息且无media）
    if (len(text) < short_text_threshold and 
        not message.media_group_id and
        not message.photo and 
        not message.document and 
        not message.video and
        not message.audio):
        
        return await _handle_auto_trigger(
            message, context, lang_ctx, text,
            session_manager, user_id
        )
    
    # 情况3：5分钟追加连贯性检测（仅对文本消息）
    if await _handle_continuity_check(message, context, lang_ctx):
        return True
    
    # 情况4：URL检测 - 不处理，让其归档
    if is_url(text):
        logger.info(f"Detected URL, processing as link archive: {text[:50]}")
        return False
    
    # 情况5：短文本处理
    return await _handle_short_text(message, context, lang_ctx, text, short_text_threshold)


async def _handle_existing_session(
    message, context, lang_ctx, text, 
    session, session_manager, user_id, text_thresholds
) -> bool:
    """处理已存在的AI会话"""
    
    # 检查是否为长文本（可能是笔记意图）
    long_text_threshold = int(text_thresholds.get('note_chinese', 150))
    
    if len(text) >= long_text_threshold:
        # 长文本，提示用户选择意图
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
        
        await message.reply_text(prompt_text, reply_markup=reply_markup)
        
        # 暂存消息内容，等待用户选择
        if 'pending_long_text' not in session.get('context', {}):
            session['context']['pending_long_text'] = {}
        session['context']['pending_long_text'][str(message.message_id)] = text
        session_manager.update_session(user_id, session.get('context', {}))
        
        logger.info(f"Long text detected ({len(text)} chars), awaiting user choice")
        return True
    
    # 正常长度，处理消息
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
        
        # 调用AI处理（使用'auto'让AI自动判断回复语言）
        ai_response = await handle_chat_message(text, session, context, 'auto', update_ai_progress)
        
        # 检测是否为资源回复（JSON格式）
        if await _handle_resource_response(
            ai_response, message, context, lang_ctx, 
            progress_msg, session_manager, user_id, session
        ):
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


async def _handle_auto_trigger(
    message, context, lang_ctx, text,
    session_manager, user_id
) -> bool:
    """自动触发AI会话"""
    
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
        if await _handle_resource_response(
            ai_response, message, context, lang_ctx,
            progress_msg, session_manager, user_id, session
        ):
            return True
        
        # 编辑消息为最终回复
        await progress_msg.edit_text(f"🤖 {ai_response}")
        
        # 更新会话
        session_manager.update_session(user_id, session.get('context', {}))
        
        logger.info(f"AI chat auto-triggered for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        await message.reply_text(lang_ctx.t('ai_chat_error'))
        session_manager.clear_session(user_id)
        return False


async def _handle_resource_response(
    ai_response, message, context, lang_ctx,
    progress_msg, session_manager, user_id, session
) -> bool:
    """处理资源回复（JSON格式的响应）"""
    
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
        except:
            pass
        
        if strategy == 'single' and resources:
            # 单个资源
            await _send_single_resource(message, context, lang_ctx, resources[0])
        
        elif strategy == 'list' and resources:
            # 多个资源列表
            await _send_resource_list(message, context, lang_ctx, resources, count)
        
        # 更新会话
        session_manager.update_session(user_id, session.get('context', {}))
        logger.info(f"AI chat {strategy} resource(s) sent to user {user_id}")
        return True
        
    except (json.JSONDecodeError, ValueError):
        # 不是JSON，正常文本回复
        return False


async def _send_single_resource(message, context, lang_ctx, resource):
    """发送单个资源"""
    
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


async def _send_resource_list(message, context, lang_ctx, resources, count):
    """发送资源列表"""
    
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
    
    await message.reply_text(
        header + list_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def _handle_continuity_check(message, context, lang_ctx) -> bool:
    """5分钟追加连贯性检测（仅对文本消息）"""
    
    last_note_id = context.user_data.get('last_note_id')
    last_note_time = context.user_data.get('last_note_time')
    
    if not (last_note_id and last_note_time and message.text):
        return False
    
    # 计算时间差
    time_diff = datetime.now() - last_note_time
    
    # 如果在5分钟窗口内
    if time_diff.total_seconds() >= 300:  # 5分钟 = 300秒
        return False
    
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
    return True


async def _handle_short_text(message, context, lang_ctx, text, short_text_threshold) -> bool:
    """处理短文本"""
    
    # 判断是否是短文字
    is_short, note_type = should_create_note(text)
    
    if not is_short:
        return False
    
    # 如果非常短（<short_text_threshold字符），询问用户意图
    if len(text) < short_text_threshold:
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
        return True
    
    # 达到笔记阈值的短文本，直接保存为笔记
    note_manager = context.bot_data.get('note_manager')
    if note_manager:
        note_id = note_manager.add_note(None, text)
        if note_id:
            await message.reply_text(lang_ctx.t('short_text_saved_note', note_id=note_id))
            logger.info(f"Short text saved as standalone note: {note_id}")
        else:
            await message.reply_text(lang_ctx.t('note_add_failed'))
    return True
