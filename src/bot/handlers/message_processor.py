"""
Single message processor
"""

import logging
import time
from typing import List, Optional, Dict
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import get_language_context
from ...utils.helpers import (
    format_file_size,
    truncate_text,
    extract_hashtags,
    remove_forward_signature,
    extract_user_comment_from_merged
)

logger = logging.getLogger(__name__)

from ...core.analyzer import ContentAnalyzer
from ...core.storage_manager import StorageManager


async def _process_single_message(message: Message, context: ContextTypes.DEFAULT_TYPE, merged_caption: Optional[str] = None, progress_callback=None) -> tuple:
    """
    处理单条消息（内部方法）
    
    Args:
        message: Telegram message
        context: Bot context
        merged_caption: 合并的caption文本（如果有）
        progress_callback: 进度回调函数 async def callback(stage: str, progress: float)
        
    Returns:
        (success, result_msg, archive_id, duplicate_info)
        - success: 是否成功
        - result_msg: 结果消息
        - archive_id: 归档ID（成功时）
        - duplicate_info: 重复文件信息（检测到重复时）
    """
    # 从 message 创建临时 update 对象以获取语言上下文
    from telegram import Update as TelegramUpdate
    from ...utils.config import get_config
    
    temp_update = TelegramUpdate(update_id=0, message=message)
    lang_ctx = get_language_context(temp_update, context)
    config = get_config()
    
    try:
        # Analyze content
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_analyzing_content'), 0.1)
        
        # 先做基础分析
        analysis = ContentAnalyzer.analyze(message)
        
        # 如果是link类型，尝试异步提取 Telegram 预览
        if analysis.get('content_type') == 'link':
            try:
                logger.info("Link detected, attempting Telegram preview extraction...")
                analysis = await ContentAnalyzer.analyze_async(message)
                has_preview = analysis.get('telegram_preview') is not None
                logger.info(f"Async analyze completed: has_telegram_preview={has_preview}")
            except Exception as e:
                logger.error(f"Async analyze failed: {e}", exc_info=True)
    
        # 提取消息来源信息（提前获取用于清理caption）
        source_info = None
        is_direct_send = True  # 默认是直接发送
        
        if message.forward_origin:
            from telegram import MessageOriginChannel, MessageOriginUser, MessageOriginChat, MessageOriginHiddenUser
            
            is_direct_send = False
            if isinstance(message.forward_origin, MessageOriginChannel):
                source_info = {
                    'name': message.forward_origin.chat.title,
                    'id': message.forward_origin.chat.id,
                    'type': message.forward_origin.chat.type
                }
                logger.info(f"Message forwarded from channel: {source_info['name']} (ID: {source_info['id']})")
            elif isinstance(message.forward_origin, MessageOriginChat):
                source_info = {
                    'name': message.forward_origin.sender_chat.title,
                    'id': message.forward_origin.sender_chat.id,
                    'type': message.forward_origin.sender_chat.type
                }
                logger.info(f"Message forwarded from chat: {source_info['name']} (ID: {source_info['id']})")
            elif isinstance(message.forward_origin, MessageOriginUser):
                user = message.forward_origin.sender_user
                source_info = {
                    'name': user.username or user.first_name,
                    'id': user.id,
                    'type': 'bot' if user.is_bot else 'user'
                }
                logger.info(f"Message forwarded from {'bot' if user.is_bot else 'user'}: {source_info['name']} (ID: {source_info['id']})")
            elif isinstance(message.forward_origin, MessageOriginHiddenUser):
                source_info = {
                    'name': message.forward_origin.sender_user_name,
                    'id': None,
                    'type': 'hidden_user'
                }
                logger.info(f"Message forwarded from hidden user: {source_info['name']}")
        else:
            logger.info("Message sent directly by user (not forwarded)")
        
        # 清理转发消息尾部签名（来源名 + URL）
        source_name = source_info.get('name') if source_info else None
        original_caption = analysis.get('content') or message.caption
        cleaned_caption = remove_forward_signature(original_caption, source_name)
        if cleaned_caption != original_caption:
            analysis['content'] = cleaned_caption
            if analysis.get('title') == original_caption:
                analysis['title'] = cleaned_caption or None
        
        # 如果有合并的caption，添加到分析结果
        if merged_caption:
            cleaned_merged_caption = remove_forward_signature(merged_caption, source_name)
            # 提取hashtags
            caption_hashtags = extract_hashtags(cleaned_merged_caption or '')
            if caption_hashtags:
                existing_hashtags = analysis.get('hashtags', [])
                analysis['hashtags'] = list(set(existing_hashtags + caption_hashtags))
        
            # 仅添加用户评论，避免与原caption重复
            user_comment = extract_user_comment_from_merged(
                cleaned_merged_caption,
                analysis.get('content') or original_caption
            )
            if user_comment:
                if analysis.get('content'):
                    analysis['content'] = f"{analysis['content']}\n\n📝 {user_comment}"
                else:
                    analysis['content'] = user_comment
        
        # 文件去重检测（仅对有文件的内容）
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_checking_duplicates'), 0.2)
        
        if analysis.get('file_id'):
            db_storage = context.bot_data.get('db_storage')
            if db_storage:
                duplicate = db_storage.find_duplicate_file(
                    file_id=analysis.get('file_id'),
                    file_name=analysis.get('file_name'),
                    file_size=analysis.get('file_size')
                )
                
                if duplicate:
                    # 检测到重复文件，返回duplicate信息由外层统一处理
                    logger.info(f"Duplicate file detected: {analysis.get('file_name')}, existing ID: {duplicate['id']}")
                    return False, "文件重复", None, duplicate
        
        # AI智能处理（如果启用）
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_ai_analysis'), 0.4)
        
        ai_summarizer = context.bot_data.get('ai_summarizer')
        ai_available = ai_summarizer and ai_summarizer.is_available()
        
        if ai_available:
            # 1. 优先处理电子书判断（如果需要）
            if analysis.get('_needs_ai_ebook_check'):
                if progress_callback:
                    await progress_callback(lang_ctx.t('progress_ai_document_type'), 0.35)
                try:
                    file_name = analysis.get('file_name', '')
                    user_language = lang_ctx.language
                    is_ebook = await ai_summarizer.is_ebook(file_name, language=user_language)
                    
                    if is_ebook:
                        analysis['content_type'] = 'ebook'
                        logger.info(f"AI判定为电子书: {file_name}")
                    else:
                        logger.info(f"AI判定为普通文档: {file_name}")
                        
                except Exception as e:
                    logger.warning(f"AI电子书判断失败: {e}")
                
                # 移除标记
                analysis.pop('_needs_ai_ebook_check', None)
            
            # 2. 判断是否应该进行AI分析
            content_type = analysis.get('content_type', '')
            file_size = analysis.get('file_size', 0)
            
            # 可分析的内容类型：文本、链接、文档、电子书
            analyzable_types = ['text', 'link', 'article', 'document', 'ebook']
            # 媒体类型（图片、视频等）如果有caption或merged_caption也可分析
            media_types = ['photo', 'image', 'video', 'audio', 'voice', 'animation']
            # 文档文件扩展名
            analyzable_extensions = ['.txt', '.md', '.doc', '.docx', '.pdf', '.epub', '.rtf']
            
            should_analyze = False
            
            # 判断是否应该分析
            if content_type in analyzable_types:
                should_analyze = True
            elif content_type == 'document':
                # 所有支持格式的文档都可以分析，但大文件使用元数据方式
                file_name = analysis.get('file_name', '').lower()
                if any(file_name.endswith(ext) for ext in analyzable_extensions):
                    should_analyze = True
            elif content_type in media_types:
                # 媒体类型：如果有caption或merged_caption则可分析
                has_caption = bool(message.caption or merged_caption)
                if has_caption:
                    should_analyze = True
                    logger.info(f"Media {content_type} has caption/comment, will perform AI analysis")
            
            if should_analyze:
                # 自动生成AI标签
                if config.ai.get('auto_generate_tags', False):
                    if progress_callback:
                        await progress_callback(lang_ctx.t('progress_ai_generating_tags'), 0.45)
                    try:
                        # 确定用于AI分析的文本内容
                        # 优先级：merged_caption（含用户评论） > caption > content
                        content_for_ai = ''
                        if content_type in media_types:
                            # 媒体类型：优先使用merged_caption，其次message.caption
                            content_for_ai = merged_caption or message.caption or ''
                        else:
                            # 其他类型：使用content或title
                            content_for_ai = analysis.get('content') or analysis.get('title', '')
                        
                        if content_for_ai:
                            start = time.time()
                            user_language = lang_ctx.language
                            # 获取配置的最大标签数量
                            max_tags = config.ai.get('max_generated_tags', 8)
                            max_tags = max(5, min(10, int(max_tags)))  # 限制在5-10之间
                            
                            ai_tags = await ai_summarizer.generate_tags(content_for_ai, max_tags, language=user_language)
                            duration = time.time() - start
                            provider = getattr(ai_summarizer, '_last_call_info', {}).get('provider', 'unknown')
                            logger.info(f"AI generate_tags provider={provider}, duration={duration:.2f}s, max_tags={max_tags}")
                            
                            if ai_tags:
                                existing_tags = analysis.get('tags', [])
                                
                                # 智能甄别caption标签
                                extract_from_caption = config.get('features.extract_tags_from_caption', False)
                                if not extract_from_caption and message.caption:
                                    # 从caption中提取潜在标签进行甄别
                                    caption_tags = extract_hashtags(message.caption)
                                    if caption_tags:
                                        # AI甄别：只保留与AI生成标签语义相关的caption标签
                                        filtered_caption_tags = []
                                        for ctag in caption_tags:
                                            if any(ai_tag.lower() in ctag.lower() or ctag.lower() in ai_tag.lower() for ai_tag in ai_tags):
                                                filtered_caption_tags.append(ctag)
                                        
                                        analysis['tags'] = list(set(existing_tags + ai_tags + filtered_caption_tags))
                                        if filtered_caption_tags:
                                            logger.info(f"Filtered caption tags: {filtered_caption_tags} (from {caption_tags})")
                                    else:
                                        analysis['tags'] = list(set(existing_tags + ai_tags))
                                else:
                                    analysis['tags'] = list(set(existing_tags + ai_tags))
                                
                                logger.info(f"AI generated tags: {ai_tags}")
                    except Exception as e:
                        logger.warning(f"AI tag generation failed: {e}")
                
                # 自动生成摘要
                if config.ai.get('auto_summarize', False):
                    if progress_callback:
                        await progress_callback(lang_ctx.t('progress_ai_analyzing_content'), 0.5)
                    try:
                        # 确定用于AI分析的文本内容
                        content_for_ai = ''
                        file_name = (analysis.get('file_name') or '').lower()
                        
                        # 对于电子书或大文件，使用元数据而非内容
                        if file_name.endswith('.epub') or (content_type == 'document' and file_size and file_size > 1 * 1024 * 1024):
                            # 提取书名、文件名等元数据作为分析依据
                            title = analysis.get('title', '') or file_name
                            content_for_ai = f"""请基于以下文件信息进行分析：
文件名：{title}
文件大小：{file_size / 1024 / 1024:.2f}MB

重要提示：
1. 如果你熟悉这个文件/书籍，请提供准确的介绍和分类
2. 如果不确定或不了解，请在摘要中明确说明"无法确定具体内容"，不要编造信息
3. 基于文件名、文件扩展名、获得的信息等提供可能的分类和标签
4. 标签应包含文件属性（如：电子书、小说、技术文档、教程、电影、照片、证件照等）"""
                            logger.info(f"Using metadata for large file analysis: {title} ({file_size / 1024 / 1024:.2f}MB)")
                        elif content_type in media_types:
                            # 媒体类型：使用merged_caption或caption
                            content_for_ai = merged_caption or message.caption or ''
                        else:
                            # 其他类型：使用content
                            content_for_ai = analysis.get('content') or ''
                            # 截断内容以节省token（最多4000字符，约1000个token）
                            if len(content_for_ai) > 4000:
                                content_for_ai = content_for_ai[:4000] + "...[内容已截断]"
                        
                        # 检查内容长度是否达到摘要阈值
                        min_length = config.ai.get('min_content_length_for_summary', 150)
                        if content_for_ai and len(content_for_ai) >= min_length:
                            # 构建上下文信息
                            context_info = {
                                'content_type': content_type,
                                'file_size': file_size or 0,
                                'existing_tags': analysis.get('tags', []),
                                'title': analysis.get('title', ''),
                                'file_extension': analysis.get('file_name', '').split('.')[-1] if analysis.get('file_name') else ''
                            }
                            
                            summary_result = None
                            start = time.time()
                            summary_result = await ai_summarizer.summarize_content(
                                    content_for_ai, 
                                    language=user_language,
                                    context=context_info
                                )
                            duration = time.time() - start
                            provider = getattr(ai_summarizer, '_last_call_info', {}).get('provider', 'unknown')
                            logger.info(f"AI summarize_content provider={provider}, duration={duration:.2f}s")
                            
                            # 记录失败详情
                            if summary_result and not summary_result.get('success'):
                                error_msg = summary_result.get('error', 'Unknown error')
                                logger.error(f"AI summarize failed: {error_msg}")
                            
                            if summary_result and summary_result.get('success'):
                                # 将AI分析结果添加到analysis
                                analysis['ai_summary'] = summary_result.get('summary', '')
                                analysis['ai_key_points'] = summary_result.get('key_points', [])
                                analysis['ai_category'] = summary_result.get('category', '')
                                
                                # 将AI建议的标签添加到标签列表
                                suggested_tags = summary_result.get('suggested_tags', [])
                                if suggested_tags:
                                    existing_tags = analysis.get('tags', [])
                                    analysis['tags'] = list(set(existing_tags + suggested_tags))
                                
                                logger.info(f"AI analysis complete: summary={analysis['ai_summary'][:50]}..., category={analysis['ai_category']}")
                                if progress_callback:
                                    await progress_callback(lang_ctx.t('progress_ai_analysis_complete'), 0.6)
                    except Exception as e:
                        logger.warning(f"AI summary generation failed: {e}")
        
        # ========== AI 降级策略：AI 不可用时使用基础分析 ==========
        elif not ai_available and config.ai.get('auto_summarize', False):
            # AI 未配置或不可用，使用降级分析
            try:
                from ..ai.fallback import AIFallbackAnalyzer
                
                user_language = lang_ctx.language
                fallback_result = None
                
                # 根据内容类型选择降级策略
                if analysis.get('file_name'):
                    # 文件分析
                    fallback_result = AIFallbackAnalyzer.analyze_file(
                        file_name=analysis.get('file_name', ''),
                        file_ext=analysis.get('file_name', '').split('.')[-1] if '.' in analysis.get('file_name', '') else '',
                        file_size=analysis.get('file_size', 0),
                        language=user_language
                    )
                elif analysis.get('urls'):
                    # URL 分析
                    url = analysis['urls'][0]
                    fallback_result = AIFallbackAnalyzer.analyze_url(url, language=user_language)
                elif analysis.get('content'):
                    # 文本分析
                    fallback_result = AIFallbackAnalyzer.analyze_text(
                        content=analysis['content'],
                        content_type=content_type,
                        language=user_language
                    )
                
                if fallback_result and fallback_result.get('success'):
                    # 使用降级分析结果
                    if fallback_result.get('category'):
                        analysis['ai_category'] = fallback_result['category']
                    if fallback_result.get('title') and not analysis.get('title'):
                        analysis['title'] = fallback_result['title']
                    if fallback_result.get('summary'):
                        analysis['ai_summary'] = fallback_result['summary']
                    if fallback_result.get('tags'):
                        existing_tags = analysis.get('tags', [])
                        analysis['tags'] = list(set(existing_tags + fallback_result['tags']))
                    
                    logger.info(f"Fallback analysis applied: category={analysis.get('ai_category')}")
                    
            except Exception as e:
                logger.warning(f"Fallback analysis failed: {e}")
        
        # 如果是文本内容且需要AI标题，生成标题
        if analysis.get('_needs_ai_title') and ai_available:
            if progress_callback:
                await progress_callback(lang_ctx.t('progress_ai_generating_title'), 0.62)
            try:
                content = analysis.get('content', '')
                is_forwarded = bool(message.forward_origin)
                
                # 转发消息无需长度判断，直接发送的消息需要>=250字符
                should_generate_title = is_forwarded or (content and len(content) >= 250)
                
                if should_generate_title and content:
                    # 生成标题（来源信息已在content开头显示，不需要在标题中重复）
                    user_language = lang_ctx.language
                    # 标题长度限制为32字符
                    max_title_length = 32
                    
                    ai_title = await ai_summarizer.generate_title_from_text(
                        content, 
                        max_length=max_title_length, 
                        language=user_language
                    )
                    if ai_title:
                        analysis['title'] = ai_title
                        analysis['ai_title'] = ai_title
                        logger.info(f"AI generated title: {analysis['title']}")
                        if progress_callback:
                            await progress_callback(lang_ctx.t('progress_title_complete'), 0.65)
            except Exception as e:
                logger.warning(f"AI title generation failed: {e}")
        

        # Get storage manager
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_saving_archive'), 0.7)
        
        storage_manager: StorageManager = context.bot_data.get('storage_manager')
        
        if not storage_manager:
            return False, "Storage manager not initialized"
        
        # 添加来源信息头部到content
        from ...utils.helpers import format_source_header, escape_html
        source_header = format_source_header(message, source_info)
        
        # 将来源信息添加到content开头（转义用户原始文本）
        if analysis.get('content'):
            # source_header已包含HTML标签，仅转义用户content
            user_content = escape_html(analysis['content'])
            analysis['content'] = f"{source_header}\n{user_content}"
        else:
            analysis['content'] = source_header
        
        # Archive content
        success, result_msg, archive_id = await storage_manager.archive_content(
            message, 
            analysis,
            source_info=source_info,
            is_direct_send=is_direct_send
        )
        
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_complete'), 1.0)
        
        # 自动生成关联笔记（如果归档成功）
        if success and archive_id:
            await _auto_generate_note(
                archive_id=archive_id,
                message=message,
                analysis=analysis,
                context=context
            )
        
        return success, result_msg, archive_id, None
        
    except Exception as e:
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_failed'), 1.0)
        raise


async def _auto_generate_note(
    archive_id: int,
    message: Message,
    analysis: Dict,
    context: ContextTypes.DEFAULT_TYPE,
    user_comment: Optional[str] = None,
    original_caption: Optional[str] = None,
    source_info: Optional[Dict] = None
) -> Optional[int]:
    """
    自动生成关联笔记
    
    根据内容类型和长度判断是否需要生成笔记：
    1. 文本内容 >= 阈值：AI生成简洁笔记
    2. 链接：根据链接信息生成笔记
    3. 文档（有AI分析）：整理完整笔记
    4. 其他媒体类型：整合AI生成 + 用户评论 + 原始caption
    
    Args:
        archive_id: 归档ID
        message: Telegram消息
        analysis: 内容分析结果
        context: Bot context
        user_comment: 用户附带的评论（可选）
        original_caption: 转发消息原始的caption（可选）
        source_info: 来源信息，包含来源名称（可选）
        
    Returns:
        note_id or None
    """
    try:
        note_manager = context.bot_data.get('note_manager')
        ai_summarizer = context.bot_data.get('ai_summarizer')
        
        if not note_manager:
            return None
        
        content_type = analysis.get('content_type', '')
        note_content = None
        
        # 获取AI分析结果
        ai_summary = analysis.get('ai_summary')
        ai_category = analysis.get('ai_category')
        ai_key_points = analysis.get('ai_key_points', [])
        
        # 检查是否有任何可用内容（AI、用户评论、caption）
        has_ai_content = bool(ai_summary or ai_category or ai_key_points)
        has_user_comment = bool(user_comment)
        has_caption = bool(original_caption)
        
        # 只有在完全没有内容时才不生成笔记
        if not (has_ai_content or has_user_comment or has_caption):
            logger.debug(f"No content available for note generation, skipping archive {archive_id}")
            return None
        
        # ========== 生成AI笔记部分 ==========
        
        # 1. 文本内容：判断长度，≥阈值则生成简洁笔记
        if content_type in ['text', 'article']:
            content = analysis.get('content', '')
            if content:
                from ...utils.helpers import should_create_note
                is_short, note_type = should_create_note(content)
                
                if not is_short and ai_summarizer and ai_summarizer.is_available():
                    # 长文本，AI生成简洁笔记
                    from telegram import Update as TelegramUpdate
                    temp_update = TelegramUpdate(update_id=0, message=message)
                    lang_ctx = get_language_context(temp_update, context)
                    language = lang_ctx.language
                    
                    note_content = await ai_summarizer.generate_note_from_content(
                        content=content,
                        content_type='text',
                        max_length=250,
                        language=language
                    )
                    
                    if note_content:
                        note_content = f"[自动] {note_content}"
                        logger.info(f"Auto-generated note for long text archive {archive_id}")
        
        # 2. 链接：根据链接元数据生成笔记
        elif content_type == 'link':
            if ai_summarizer and ai_summarizer.is_available():
                from telegram import Update as TelegramUpdate
                temp_update = TelegramUpdate(update_id=0, message=message)
                lang_ctx = get_language_context(temp_update, context)
                language = lang_ctx.language
                
                # 构建链接信息用于生成笔记
                link_info = f"""链接标题：{analysis.get('title', '未知')}
URL：{analysis.get('url', '')}
"""
                # 如果有 Telegram 预览数据
                telegram_preview = analysis.get('telegram_preview', {})
                if telegram_preview and telegram_preview.get('description'):
                    link_info += f"描述：{telegram_preview.get('description')}\n"
                
                # 使用内容
                if analysis.get('content'):
                    link_info += f"\n内容：\n{analysis.get('content')[:1000]}"
                
                note_content = await ai_summarizer.generate_note_from_content(
                    content=link_info,
                    content_type='link',
                    max_length=250,
                    language=language
                )
                
                if note_content:
                    note_content = f"[自动] {note_content}"
                    logger.info(f"Auto-generated note for link archive {archive_id}")

        
        # 3. 文档：如果有AI分析结果，整理完整笔记
        elif content_type in ['document', 'ebook']:
            if has_ai_content and ai_summarizer and ai_summarizer.is_available():
                from telegram import Update as TelegramUpdate
                temp_update = TelegramUpdate(update_id=0, message=message)
                lang_ctx = get_language_context(temp_update, context)
                language = lang_ctx.language
                
                title = analysis.get('title') or analysis.get('file_name', '未知文档')
                
                note_content = await ai_summarizer.generate_note_from_ai_analysis(
                    ai_summary=ai_summary,
                    ai_key_points=ai_key_points,
                    ai_category=ai_category,
                    title=title,
                    language=language
                )
                
                if note_content:
                    note_content = f"[自动] {note_content}"
                    logger.info(f"Auto-generated note for document archive {archive_id}")
        
        # 4. 其他类型（图片、视频、音频等）：如果有AI分析，生成笔记
        else:
            if has_ai_content and ai_summarizer and ai_summarizer.is_available():
                from telegram import Update as TelegramUpdate
                temp_update = TelegramUpdate(update_id=0, message=message)
                lang_ctx = get_language_context(temp_update, context)
                language = lang_ctx.language
                
                # 使用AI摘要生成笔记
                note_content = await ai_summarizer.generate_note_from_content(
                    content=ai_summary or ai_category or '',
                    content_type=content_type,
                    max_length=250,
                    language=language
                )
                
                if note_content:
                    note_content = f"[自动] {note_content}"
                    logger.info(f"Auto-generated note for {content_type} archive {archive_id}")
        
        # 构建完整的笔记内容：AI生成 + 用户评论 + 原始caption
        if note_content or user_comment or original_caption:
            final_note_parts = []
            
            # 第一部分：AI生成的笔记
            if note_content:
                final_note_parts.append(note_content)
            
            # 第二部分：用户评论
            if user_comment:
                # 只有前面有内容时才添加分隔线
                if final_note_parts:
                    final_note_parts.append("----------------------------------")
                final_note_parts.append(f"[用户]: {user_comment}")
            
            # 第三部分：原始caption（转发消息的原文）
            if original_caption:
                # 只有前面有内容时才添加分隔线
                if final_note_parts:
                    final_note_parts.append("----------------------------------")
                final_note_parts.append(f"[原文]: {original_caption}")
            
            # 合并所有部分
            final_note_content = "\n".join(final_note_parts)
            
            # 提取笔记标题：优先使用AI分析的标题或文件名
            note_title = None
            
            # 统一的标题提取逻辑：优先使用 analysis.title，其次 file_name，最后原始caption
            if analysis.get('title'):
                note_title = analysis.get('title')
            elif analysis.get('file_name'):
                note_title = analysis.get('file_name')
            elif original_caption:
                # 文本类型或其他没有标题的内容，尝试从caption获取
                note_title = original_caption[:50]
            
            # 保存笔记
            note_id = note_manager.add_note(archive_id, final_note_content)
            if note_id:
                logger.info(f"Auto-generated note {note_id} for archive {archive_id} (with_user_comment={bool(user_comment)}, with_caption={bool(original_caption)})")
                
                # 转发笔记到Telegram频道（与手动笔记模式保持一致）
                from ...utils.note_storage_helper import forward_note_to_channel, update_archive_message_buttons
                storage_path = await forward_note_to_channel(
                    context=context,
                    note_id=note_id,
                    note_content=final_note_content,
                    note_title=note_title,
                    note_manager=note_manager
                )
                
                if storage_path:
                    logger.info(f"Auto-generated note {note_id} forwarded to channel: {storage_path}")
                
                # 更新原始存档消息的按钮（将"添加笔记"改为"查看笔记"）
                await update_archive_message_buttons(context, archive_id)
                
                return note_id
        
        return None
        
    except Exception as e:
        logger.error(f"Error auto-generating note: {e}", exc_info=True)
        return None
