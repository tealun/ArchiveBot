"""
Message handlers
Handles incoming messages for archiving
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..core.analyzer import ContentAnalyzer
from ..core.storage_manager import StorageManager
from ..utils.i18n import get_i18n

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming message for archiving
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        message = update.message
        i18n = get_i18n()
        
        # Send processing message
        processing_msg = await message.reply_text(i18n.t('processing'))
        
        # Analyze content
        analysis = ContentAnalyzer.analyze(message)
        
        # 如果是链接，尝试提取元数据
        if analysis.get('_needs_metadata_extraction'):
            try:
                from ..utils.link_extractor import extract_link_metadata
                url = analysis.get('url')
                metadata = await extract_link_metadata(url)
                
                # 更新分析结果
                analysis['title'] = metadata.get('title') or url
                analysis['link_metadata'] = metadata
                
                # 如果有描述，添加到内容中
                if metadata.get('description'):
                    analysis['content'] = f"{analysis.get('content', '')}\n\n📄 {metadata['description']}"
                
                logger.info(f"Extracted link metadata: {metadata.get('title')}")
            except Exception as e:
                logger.warning(f"Failed to extract link metadata: {e}")
        
        # AI智能处理（如果启用）
        ai_summarizer = context.bot_data.get('ai_summarizer')
        if ai_summarizer and ai_summarizer.is_available():
            from ..utils.config import get_config
            config = get_config()
            
            # 自动生成AI标签
            if config.ai.get('auto_generate_tags', False):
                try:
                    content_for_ai = analysis.get('content') or analysis.get('title', '')
                    if content_for_ai:
                        ai_tags = await ai_summarizer.generate_tags(content_for_ai, 3)
                        if ai_tags:
                            existing_tags = analysis.get('tags', [])
                            analysis['tags'] = list(set(existing_tags + ai_tags))
                            logger.info(f"AI generated tags: {ai_tags}")
                except Exception as e:
                    logger.warning(f"AI tag generation failed: {e}")
            
            # 自动生成摘要（仅对长文本）
            if config.ai.get('auto_summarize', False):
                try:
                    content_for_ai = analysis.get('content') or ''
                    if content_for_ai and len(content_for_ai) > 500:  # 只对长文本总结
                        summary_result = await ai_summarizer.summarize_content(content_for_ai)
                        if summary_result.get('success'):
                            # 将摘要添加到内容开头
                            summary = summary_result.get('summary', '')
                            if summary:
                                analysis['ai_summary'] = summary
                                logger.info(f"AI summary generated: {summary[:100]}...")
                except Exception as e:
                    logger.warning(f"AI summary generation failed: {e}")
        
        # Get storage manager
        storage_manager: StorageManager = context.bot_data.get('storage_manager')
        
        if not storage_manager:
            await processing_msg.edit_text("Storage manager not initialized")
            return
        
        # Archive content
        success, result_msg = await storage_manager.archive_content(message, analysis)
        
        # Send result
        await processing_msg.edit_text(result_msg)
        
        if success:
            logger.info(
                f"Message archived: user={update.effective_user.id}, "
                f"type={analysis.get('content_type')}"
            )
        else:
            logger.warning(
                f"Failed to archive message: user={update.effective_user.id}, "
                f"type={analysis.get('content_type')}"
            )
        
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        i18n = get_i18n()
        try:
            await update.message.reply_text(i18n.t('error_occurred', error=str(e)))
        except:
            pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo message"""
    await handle_message(update, context)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video message"""
    await handle_message(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document message"""
    await handle_message(update, context)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio message"""
    await handle_message(update, context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice message"""
    await handle_message(update, context)


async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle animation (GIF) message"""
    await handle_message(update, context)


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker message"""
    await handle_message(update, context)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle contact message"""
    await handle_message(update, context)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle location message"""
    await handle_message(update, context)
