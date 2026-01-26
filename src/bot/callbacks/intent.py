"""
Intent callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.ai_session import get_session_manager
from ...ai.chat_router import handle_chat_message
from ...utils.helpers import truncate_text

@with_language_context
async def handle_short_text_intent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理短文本意图选择回调
    
    Callback data format: short_text:note|ai|archive
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析: short_text:action
        action = callback_data.split(':', 1)[1]
        
        # 获取待处理文本
        text = context.user_data.get('pending_short_text')
        if not text:
            await query.edit_message_text("⚠️ 会话已过期，请重新发送文本")
            return
        
        if action == 'note':
            # 保存为笔记
            note_manager = context.bot_data.get('note_manager')
            if note_manager:
                note_id = note_manager.add_note(None, text)
                if note_id:
                    await query.edit_message_text(f"✅ 已保存为笔记 (ID: #{note_id})")
                    logger.info(f"User chose to save as note: {note_id}")
                else:
                    await query.edit_message_text("❌ 笔记保存失败")
            else:
                await query.edit_message_text("❌ 笔记管理器未初始化")
        
        elif action == 'ai':
            # AI互动模式
            ai_summarizer = context.bot_data.get('ai_summarizer')
            if ai_summarizer and ai_summarizer.is_available():
                # 创建AI会话
                from ..core.ai_session import get_session_manager
                from ..ai.chat_router import handle_chat_message
                
                session_manager = get_session_manager()
                user_id = query.from_user.id
                
                # 创建新会话
                session_manager.create_session(user_id)
                
                await query.edit_message_text(
                    "🤖 **AI互动模式已激活**\n\n"
                    "我可以帮你：\n"
                    "• 搜索归档内容\n"
                    "• 回答相关问题\n"
                    "• 分析和总结信息\n\n"
                    "💬 直接发送消息开始对话\n"
                    "📝 发送 \"退出\" 或 \"exit\" 结束会话",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"User activated AI mode with text: {text[:50]}")
                
                # 如果有待处理文本，处理它
                if text:
                    # 获取会话数据
                    session = session_manager.get_session(user_id)
                    
                    # 调用AI处理（使用'auto'让AI自动判断语言）
                    ai_response = await handle_chat_message(text, session, context, 'auto')
                    
                    # 发送AI回复
                    await query.message.reply_text(f"🤖 {ai_response}")
                    
                    # 更新会话
                    session_manager.update_session(user_id, session.get('context', {}))
            else:
                await query.edit_message_text(
                    "❌ AI功能未启用\n\n"
                    "请在配置文件中启用AI功能后重试。"
                )
        
        elif action == 'archive':
            # 归档为内容
            await query.edit_message_text("📦 正在归档...")
            
            try:
                # 使用ContentAnalyzer分析文本
                from ..core.analyzer import ContentAnalyzer
                from telegram import Message
                
                # 创建一个虚拟消息对象用于分析
                # 由于是用户输入的文本，我们直接构建分析结果
                analysis = {
                    'content_type': 'text',
                    'title': text[:50] + ('...' if len(text) > 50 else ''),
                    'content': text,
                    'file_id': None,
                    'file_size': None,
                    'file_name': None,
                    'mime_type': None,
                    'url': None,
                    'hashtags': [],
                    'source': '用户输入',
                    'created_at': None
                }
                
                # 使用archive_content方法归档
                storage_manager = context.bot_data.get('storage_manager')
                if storage_manager:
                    # 由于archive_content需要message对象，我们直接使用db_storage
                    archive_id = storage_manager.db_storage.create_archive(
                        content_type='text',
                        storage_type='database',
                        title=analysis['title'],
                        content=analysis['content'],
                        file_id=None,
                        storage_provider=None,
                        storage_path=None,
                        file_size=None,
                        source=analysis['source'],
                        metadata={},
                        ai_summary=None,
                        ai_key_points=None,
                        ai_category=None
                    )
                    
                    if archive_id:
                        # 添加自动标签
                        tag_manager = context.bot_data.get('tag_manager')
                        if tag_manager:
                            auto_tags = tag_manager.generate_auto_tags('text')
                            if auto_tags:
                                tag_manager.add_tags_to_archive(archive_id, auto_tags, 'auto')
                        
                        # 失效AI缓存
                        storage_manager._invalidate_ai_cache()
                        
                        await query.edit_message_text(
                            f"✅ 已归档 (ID: #{archive_id})\n\n"
                            f"内容：{text[:100] + ('...' if len(text) > 100 else '')}"
                        )
                        logger.info(f"User chose to archive text: {archive_id}")
                    else:
                        await query.edit_message_text("❌ 归档失败")
                else:
                    await query.edit_message_text("❌ 存储管理器未初始化")
                    
            except Exception as e:
                logger.error(f"Error archiving text: {e}", exc_info=True)
                await query.edit_message_text(f"❌ 归档失败: {str(e)}")
        
        # 清除待处理文本
        context.user_data.pop('pending_short_text', None)
        
    except Exception as e:
        logger.error(f"Error handling short text intent callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ 处理失败: {str(e)}")


@with_language_context
async def handle_long_text_intent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理长文本意图选择回调（AI聊天模式中）
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析callback数据: longtxt_note:message_id 或 longtxt_chat:message_id
        parts = callback_data.split(':')
        if len(parts) != 2:
            await query.edit_message_text("❌ Invalid callback data")
            return
        
        action = parts[0]  # longtxt_note 或 longtxt_chat
        message_id = parts[1]
        
        # 从会话获取暂存的文本
        from ..core.ai_session import get_session_manager
        from ..utils.config import get_config
        
        config = get_config()
        ai_config = config.ai
        session_manager = get_session_manager(
            ttl_seconds=ai_config.get('chat_session_ttl_seconds', 600)
        )
        
        user_id = str(query.from_user.id)
        session = session_manager.get_session(user_id)
        
        if not session:
            await query.edit_message_text(lang_ctx.t('ai_chat_session_expired') if hasattr(lang_ctx, 't') else "会话已过期")
            return
        
        pending_texts = session.get('context', {}).get('pending_long_text', {})
        text = pending_texts.get(message_id)
        
        if not text:
            await query.edit_message_text("❌ Text not found or expired")
            return
        
        if action == 'longtxt_note':
            # 用户选择记录为笔记
            storage_manager = context.bot_data.get('storage_manager')
            
            if storage_manager:
                # 归档为笔记
                result = storage_manager.create_archive(
                    content_type='text',
                    title=text[:50] + ('...' if len(text) > 50 else ''),
                    content=text,
                    file_id=None,
                    tags=[],
                    source='telegram',
                    ai_analysis=None
                )
                
                if result:
                    archive_id = result.get('id')
                    
                    if lang_ctx.language == 'en':
                        success_msg = f"✅ Saved as note (ID: #{archive_id})\n\nContent: {truncate_text(text, 100)}"
                    elif lang_ctx.language in ['zh-TW', 'zh-HK', 'zh-MO']:
                        success_msg = f"✅ 已記錄為筆記 (ID: #{archive_id})\n\n內容：{truncate_text(text, 100)}"
                    else:
                        success_msg = f"✅ 已记录为笔记 (ID: #{archive_id})\n\n内容：{truncate_text(text, 100)}"
                    
                    await query.edit_message_text(success_msg)
                    logger.info(f"Long text saved as note: {archive_id}")
                    
                    # 退出AI会话
                    session_manager.clear_session(user_id)
                else:
                    await query.edit_message_text("❌ Failed to save")
            else:
                await query.edit_message_text("❌ Storage manager not initialized")
        
        elif action == 'longtxt_chat':
            # 用户选择继续对话
            try:
                # 删除选择提示
                await query.message.delete()
                
                # 发送AI处理进度
                progress_msg = await query.message.reply_text(f"🤖 {lang_ctx.t('ai_chat_understanding')}")
                
                # 包装进度更新回调
                async def update_ai_progress(stage: str):
                    try:
                        await progress_msg.edit_text(f"🤖 {stage}")
                    except Exception:
                        pass
                
                # 调用AI处理
                from ..ai.chat_router import handle_chat_message
                await update_ai_progress(lang_ctx.t('ai_chat_analyzing'))
                
                ai_response = await handle_chat_message(text, session, context, 'auto', update_ai_progress)
                
                # 编辑消息为最终回复
                await progress_msg.edit_text(f"🤖 {ai_response}")
                
                # 更新会话
                session_manager.update_session(user_id, session.get('context', {}))
                
                logger.info(f"Long text processed as chat message")
                
            except Exception as e:
                logger.error(f"AI chat error for long text: {e}", exc_info=True)
                await query.message.reply_text(lang_ctx.t('ai_chat_error_session_end') if hasattr(lang_ctx, 't') else "AI处理失败，会话已结束")
                session_manager.clear_session(user_id)
        
        # 清除待处理文本
        if message_id in pending_texts:
            del pending_texts[message_id]
            session_manager.update_session(user_id, session.get('context', {}))
        
    except Exception as e:
        logger.error(f"Error handling long text intent callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Processing failed: {str(e)}")
        await query.answer(f"Error: {str(e)}", show_alert=True)
