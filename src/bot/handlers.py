"""
Message handlers
Handles incoming messages for archiving
"""

import logging
import time
from typing import List, Optional
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..core.analyzer import ContentAnalyzer
from ..core.storage_manager import StorageManager
from ..utils.language_context import get_language_context
from ..utils.helpers import format_file_size, truncate_text
from .message_aggregator import MessageAggregator
from ..core.ai_session import get_session_manager
from ..ai.chat_router import handle_chat_message

logger = logging.getLogger(__name__)

# 全局消息聚合器
_message_aggregator: Optional[MessageAggregator] = None


def _cleanup_user_data(user_data: dict, threshold: int = 15) -> None:
    """
    清理user_data中的临时数据，防止内存泄漏
    
    Args:
        user_data: 用户数据字典
        threshold: 触发清理的键数量阈值
    """
    if len(user_data) <= threshold:
        return
    
    # 定义需要保留的持久化键（只保留语言设置）
    persistent_keys = {'language'}
    
    # 定义临时键（会自动清理）
    temporary_keys = [
        'waiting_note_for_archive', 'note_modify_mode', 'note_id_to_modify',
        'note_append_mode', 'note_id_to_append', 'pending_command',
        'refine_note_context', 'pending_short_text'
    ]
    
    # 清理临时键（跳过持久化键和笔记模式相关键）
    removed_count = 0
    for key in list(user_data.keys()):
        # 保留持久化键
        if key in persistent_keys:
            continue
        # 保留笔记模式活跃时的相关键
        if user_data.get('note_mode') and key in ['note_mode', 'note_messages', 'note_archives', 'note_timeout_job', 'note_start_time']:
            continue
        # 清理临时键
        if key in temporary_keys:
            user_data.pop(key, None)
            removed_count += 1
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} temporary keys from user_data (size: {len(user_data)})")


def get_message_aggregator() -> MessageAggregator:
    """Get or create message aggregator"""
    global _message_aggregator
    if _message_aggregator is None:
        _message_aggregator = MessageAggregator(batch_window_ms=200, max_batch_size=100)
    return _message_aggregator




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
    from ..utils.config import get_config
    
    temp_update = TelegramUpdate(update_id=0, message=message)
    lang_ctx = get_language_context(temp_update, context)
    config = get_config()
    
    try:
        # Analyze content
        if progress_callback:
            await progress_callback(lang_ctx.t('progress_analyzing_content'), 0.1)
        
        analysis = ContentAnalyzer.analyze(message)
    
        # 如果有合并的caption，添加到分析结果
        if merged_caption:
            # 提取hashtags
            from ..utils.helpers import extract_hashtags
            caption_hashtags = extract_hashtags(merged_caption)
            if caption_hashtags:
                existing_hashtags = analysis.get('hashtags', [])
                analysis['hashtags'] = list(set(existing_hashtags + caption_hashtags))
        
            # 添加到content或作为备注
            if analysis.get('content'):
                analysis['content'] = f"{analysis['content']}\n\n📝 {merged_caption}"
            else:
                analysis['content'] = merged_caption
    
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
            
            if should_analyze:
                # 自动生成AI标签
                if config.ai.get('auto_generate_tags', False):
                    if progress_callback:
                        await progress_callback(lang_ctx.t('progress_ai_generating_tags'), 0.45)
                    try:
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
                
                # 自动生成摘要（仅对长文本）
                if config.ai.get('auto_summarize', False):
                    if progress_callback:
                        await progress_callback(lang_ctx.t('progress_ai_analyzing_content'), 0.5)
                    try:
                        content_for_ai = analysis.get('content') or ''
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
                        else:
                            # 截断内容以节省token（最多4000字符，约1000个token）
                            if len(content_for_ai) > 4000:
                                content_for_ai = content_for_ai[:4000] + "...[内容已截断]"
                        
                        if content_for_ai and len(content_for_ai) > 100:  # 降低最小长度要求
                            # 获取用户语言设置
                            user_language = lang_ctx.language
                            
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
                    # 提取转发来源
                    source_prefix = ""
                    if is_forwarded:
                        origin = message.forward_origin
                        if hasattr(origin, 'sender_user') and origin.sender_user:
                            # 从用户转发
                            user = origin.sender_user
                            username = user.username or user.first_name or "用户"
                            source_prefix = f"来自[{username}] "
                        elif hasattr(origin, 'chat') and origin.chat:
                            # 从频道/群组转发
                            chat = origin.chat
                            source_prefix = f"来自[{chat.title}] "
                        elif hasattr(origin, 'sender_user_name'):
                            # 隐藏用户名的转发
                            source_prefix = f"来自[{origin.sender_user_name}] "
                    
                    user_language = lang_ctx.language
                    # 计算标题可用长度（32 - 来源前缀长度）
                    max_title_length = 32 - len(source_prefix)
                    if max_title_length < 10:  # 如果来源太长，限制来源长度
                        source_prefix = source_prefix[:10] + ".. "
                        max_title_length = 32 - len(source_prefix)
                    
                    ai_title = await ai_summarizer.generate_title_from_text(
                        content, 
                        max_length=max_title_length, 
                        language=user_language
                    )
                    if ai_title:
                        analysis['title'] = source_prefix + ai_title
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
        
        # 提取消息来源信息
        source_info = None
        is_direct_send = True  # 默认是直接发送
        
        # 检查是否为转发消息
        if message.forward_origin:
            from telegram import MessageOriginChannel, MessageOriginUser, MessageOriginChat
            
            is_direct_send = False
            if isinstance(message.forward_origin, MessageOriginChannel):
                # 来自频道的转发
                source_info = {
                    'name': message.forward_origin.chat.title,
                    'id': message.forward_origin.chat.id,
                    'type': message.forward_origin.chat.type
                }
                logger.info(f"Message forwarded from channel: {source_info['name']} (ID: {source_info['id']})")
            elif isinstance(message.forward_origin, MessageOriginChat):
                # 来自群组的转发
                source_info = {
                    'name': message.forward_origin.sender_chat.title,
                    'id': message.forward_origin.sender_chat.id,
                    'type': message.forward_origin.sender_chat.type
                }
                logger.info(f"Message forwarded from chat: {source_info['name']} (ID: {source_info['id']})")
            elif isinstance(message.forward_origin, MessageOriginUser):
                # 来自用户的转发
                user = message.forward_origin.sender_user
                source_info = {
                    'name': user.username or user.first_name,
                    'id': user.id,
                    'type': 'private'
                }
                logger.info(f"Message forwarded from user: {source_info['name']} (ID: {source_info['id']})")
        else:
            # 个人直接发送
            logger.info("Message sent directly by user (not forwarded)")
        
        # Archive content (传递来源信息和直发标识)
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
    context: ContextTypes.DEFAULT_TYPE
) -> Optional[int]:
    """
    自动生成关联笔记
    
    根据内容类型和长度判断是否需要生成笔记：
    1. 文本内容 >= 阈值：AI生成简洁笔记
    2. 链接：根据链接信息生成笔记
    3. 文档（有AI分析）：整理完整笔记
    
    Args:
        archive_id: 归档ID
        message: Telegram消息
        analysis: 内容分析结果
        context: Bot context
        
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
        
        # 判断是否需要生成笔记
        
        # 1. 文本内容：判断长度，≥阈值则生成简洁笔记
        if content_type in ['text', 'article']:
            content = analysis.get('content', '')
            if content:
                from ..utils.helpers import should_create_note
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
                # 构建链接信息用于生成笔记
                link_info = f"""链接标题：{analysis.get('title', '未知')}
URL：{analysis.get('url', '')}
"""
                # 如果有提取的元数据，添加描述
                link_metadata = analysis.get('link_metadata', {})
                if link_metadata and link_metadata.get('description'):
                    link_info += f"描述：{link_metadata.get('description')}\n"
                
                # 如果有页面内容，使用页面内容
                page_content = link_metadata.get('content', '')
                if page_content:
                    link_info += f"\n页面内容节选：\n{page_content[:1000]}"
                
                from telegram import Update as TelegramUpdate
                temp_update = TelegramUpdate(update_id=0, message=message)
                lang_ctx = get_language_context(temp_update, context)
                language = lang_ctx.language
                
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
        elif content_type == 'document':
            ai_summary = analysis.get('ai_summary')
            ai_key_points = analysis.get('ai_key_points', [])
            ai_category = analysis.get('ai_category', '')
            
            if ai_summary and ai_summarizer and ai_summarizer.is_available():
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
        
        # 保存笔记
        if note_content:
            note_id = note_manager.add_note(archive_id, note_content)
            if note_id:
                logger.info(f"Auto-generated note {note_id} for archive {archive_id}")
                return note_id
        
        return None
        
    except Exception as e:
        logger.error(f"Error auto-generating note: {e}", exc_info=True)
        return None


async def _process_batch_messages(messages: List[Message], context: ContextTypes.DEFAULT_TYPE, merged_caption: Optional[str] = None, source_info: Optional[Dict] = None, is_forwarded: bool = False, progress_callback=None) -> List[tuple]:
    """
    批量处理消息（优化：共享手动标签 + 独立AI标签）
    
    Args:
        messages: 消息列表
        context: Bot context
        merged_caption: 合并的caption文本（如果有）
        source_info: 来源信息（从batch中提取）
        is_forwarded: 是否为转发消息
        progress_callback: 进度回调函数 (current, total, stage)
        
    Returns:
        [(success, result_msg), ...]
    """
    # 从第一条 message 创建临时 update 对象以获取语言上下文
    from telegram import Update as TelegramUpdate
    temp_update = TelegramUpdate(update_id=0, message=messages[0])
    lang_ctx = get_language_context(temp_update, context)
    results = []
    total = len(messages)
    
    # 阶段1: 分析内容 (0-20%)
    if progress_callback:
        await progress_callback(0, total, lang_ctx.t('batch_progress_analyzing'))
    
    analyses = []
    for i, message in enumerate(messages):
        analysis = ContentAnalyzer.analyze(message)
        analyses.append(analysis)
        if progress_callback and (i + 1) % max(1, total // 10) == 0:
            await progress_callback(i + 1, total, lang_ctx.t('batch_progress_analyzing'))
    
    # 阶段2: 提取共享标签 (20%)
    if progress_callback:
        await progress_callback(total, total, lang_ctx.t('batch_progress_extracting_tags'))
    
    # 提取共享的hashtags（从merged_caption）- 这是用户主动输入的标签
    shared_hashtags = []
    if merged_caption:
        from ..utils.helpers import extract_hashtags
        shared_hashtags = extract_hashtags(merged_caption)
        logger.info(f"Extracted shared hashtags from caption: {shared_hashtags}")
    
    # 阶段3: AI处理 (20-50%) - 批量消息只分析一次合并的caption
    if progress_callback:
        await progress_callback(0, total, lang_ctx.t('batch_progress_ai_generating_tags'))
    
    # 批量AI处理 - 只对合并的caption+用户评论调用一次AI
    shared_ai_result = {'tags': [], 'title': None, 'summary': None}
    ai_summarizer = context.bot_data.get('ai_summarizer')
    if ai_summarizer and ai_summarizer.is_available():
        from ..utils.config import get_config
        config = get_config()
        
        # 只分析一次：使用merged_caption（包含用户评论）
        if config.ai.get('auto_generate_tags', False) and merged_caption:
            try:
                start = time.time()
                max_tags = config.ai.get('max_generated_tags', 8)
                max_tags = max(3, min(max_tags, 5))  # 批量时限制在3-5之间
                
                # 生成标签
                ai_tags = await ai_summarizer.generate_tags(merged_caption, max_tags, language=lang_ctx.language)
                duration = time.time() - start
                provider = getattr(ai_summarizer, '_last_call_info', {}).get('provider', 'single')
                logger.info(f"Batch AI single analysis: provider={provider}, duration={duration:.2f}s, tags={ai_tags}")
                
                if ai_tags:
                    shared_ai_result['tags'] = ai_tags
                
                # 生成标题（限制32字符）
                if config.ai.get('auto_generate_title', False):
                    ai_title = await ai_summarizer.generate_title(merged_caption, language=lang_ctx.language)
                    if ai_title:
                        shared_ai_result['title'] = ai_title[:32]
                        logger.info(f"Batch AI generated title: {shared_ai_result['title']}")
                
                logger.info(f"Batch AI shared analysis completed")
            except Exception as e:
                logger.warning(f"Batch AI analysis failed: {e}")
    
    if progress_callback:
        await progress_callback(total, total, lang_ctx.t('batch_progress_ai_generating_tags'))
    
    # 阶段4: 应用标签和AI结果 (50-60%)
    if progress_callback:
        await progress_callback(0, total, lang_ctx.t('batch_progress_applying_tags'))
    
    # 应用共享的AI分析结果和hashtags到所有分析结果
    for i, analysis in enumerate(analyses):
        # 添加共享的hashtags（用户手动标签）
        if shared_hashtags:
            existing_hashtags = analysis.get('hashtags', [])
            analysis['hashtags'] = list(set(existing_hashtags + shared_hashtags))
        
        # 添加共享的AI标签到所有item
        if shared_ai_result['tags']:
            existing_tags = analysis.get('tags', [])
            analysis['tags'] = list(set(existing_tags + shared_ai_result['tags']))
        
        # 使用共享的AI标题（如果有），否则截取caption前32字符
        if shared_ai_result['title']:
            analysis['title'] = shared_ai_result['title']
        elif merged_caption and not analysis.get('title'):
            # 截取caption前32字符作为标题
            analysis['title'] = merged_caption[:32] + ('...' if len(merged_caption) > 32 else '')
        
        # 第一条消息附加caption到content（作为批注）
        if i == 0 and merged_caption:
            if analysis.get('content'):
                analysis['content'] = f"{analysis['content']}\n\n📝 批注: {merged_caption}"
            else:
                analysis['content'] = f"📝 批注: {merged_caption}"
    
    if progress_callback:
        await progress_callback(total, total, lang_ctx.t('batch_progress_applying_tags'))
    
    logger.info(f"Batch processing: shared hashtags={shared_hashtags}, each item has independent AI tags")
    
    # 阶段5: 批量存储 (60-100%)
    if progress_callback:
        await progress_callback(0, total, lang_ctx.t('batch_progress_storing'))
    
    # 批量存储（优化：使用storage_manager的批量方法）
    storage_manager: StorageManager = context.bot_data.get('storage_manager')
    if not storage_manager:
        return [(False, "Storage manager not initialized") for _ in messages]
    
    # 调用批量归档（带进度回调和来源信息）
    results = await storage_manager.batch_archive_content(
        messages, 
        analyses, 
        source_info=source_info,
        is_batch_forwarded=is_forwarded,
        progress_callback=progress_callback
    )
    
    if progress_callback:
        await progress_callback(total, total, lang_ctx.t('batch_progress_complete'))
    
    return results


async def _batch_callback(messages: List[Message], merged_caption: Optional[str], source_info: Optional[Dict], is_forwarded: bool, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    批次处理回调
    
    Args:
        messages: 消息列表
        merged_caption: 合并的caption
        source_info: 来源信息
        is_forwarded: 是否为转发消息
        update: Telegram update
        context: Bot context
    """
    lang_ctx = get_language_context(update, context)
    
    try:
        if len(messages) == 1:
            # 单条消息处理
            message = messages[0]
            processing_msg = await message.reply_text(lang_ctx.t('archive_processing'))
            
            try:
                # 定义进度更新回调
                async def update_progress(stage: str, progress: float):
                    try:
                        percentage = int(progress * 100)
                        progress_bar = '█' * (percentage // 5) + '░' * (20 - percentage // 5)
                        await processing_msg.edit_text(
                            f"⏳ {stage}\n"
                            f"{lang_ctx.t('archive_progress', percentage=percentage)}\n"
                            f"{progress_bar}"
                        )
                    except Exception as e:
                        logger.debug(f"Progress update failed: {e}")
                
                success, result_msg, archive_id, duplicate_info = await _process_single_message(message, context, merged_caption, update_progress)
                
                # 如果检测到重复文件，构建并发送重复提示消息
                if duplicate_info:
                    # 构建重复文件提示消息（使用HTML格式）
                    dup_msg = f"{lang_ctx.t('archive_duplicate_file')}\n\n"
                    
                    # 构建文件名（如果有频道链接则作为超链接）
                    file_title = duplicate_info.get('title', lang_ctx.t('archive_duplicate_unknown_title'))
                    storage_path = duplicate_info.get('storage_path')
                    storage_type = duplicate_info.get('storage_type')
                    
                    if storage_path and storage_type == 'telegram':
                        from ..utils.config import get_config
                        config = get_config()
                        channel_id = config.telegram_channel_id
                        if channel_id:
                            # 解析 storage_path: 可能是 "message_id" 或 "channel_id:message_id" 或 "channel_id:message_id:file_id"
                            parts = storage_path.split(':')
                            if len(parts) >= 2:
                                # 格式: channel_id:message_id[:file_id]
                                channel_id_str = parts[0].replace('-100', '')
                                message_id = parts[1]
                            else:
                                # 格式: message_id（使用配置的channel_id）
                                channel_id_str = str(channel_id).replace('-100', '')
                                message_id = storage_path
                            
                            file_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                            dup_msg += lang_ctx.t('archive_duplicate_file_name', title=f"<a href='{file_link}'>{file_title}</a>") + "\n"
                        else:
                            dup_msg += lang_ctx.t('archive_duplicate_file_name', title=file_title) + "\n"
                    else:
                        dup_msg += lang_ctx.t('archive_duplicate_file_name', title=file_title) + "\n"
                    
                    dup_msg += lang_ctx.t('archive_duplicate_file_size', size=format_file_size(duplicate_info.get('file_size', 0))) + "\n"
                    dup_msg += lang_ctx.t('archive_duplicate_file_archived_at', time=duplicate_info.get('archived_at', lang_ctx.t('archive_duplicate_unknown_time'))) + "\n"
                    
                    # 获取标签
                    tag_manager = context.bot_data.get('tag_manager')
                    if tag_manager:
                        tags = tag_manager.get_archive_tags(duplicate_info['id'])
                        if tags:
                            tag_str = ' '.join([f"#{tag}" for tag in tags])
                            dup_msg += lang_ctx.t('archive_duplicate_file_tags', tags=tag_str)
                    
                    await processing_msg.edit_text(dup_msg, parse_mode='HTML')
                    return
                
                # 如果归档成功且有archive_id，添加操作按钮（包含精炼笔记）
                if success and archive_id:
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    # 获取数据库检查状态
                    db_storage = context.bot_data.get('db_storage')
                    db = db_storage.db if db_storage else None
                    
                    has_notes = db.has_notes(archive_id) if db else False
                    is_favorite = db.is_favorite(archive_id) if db else False
                    
                    note_icon = "📝✓" if has_notes else "📝"
                    fav_icon = "❤️" if is_favorite else "🤍"
                    
                    keyboard = [[
                        InlineKeyboardButton(note_icon, callback_data=f"note:{archive_id}"),
                        InlineKeyboardButton(fav_icon, callback_data=f"fav:{archive_id}"),
                        InlineKeyboardButton("↗️", callback_data=f"forward:{archive_id}")
                    ]]
                    
                    # 如果有笔记，添加"精炼笔记"按钮
                    if has_notes:
                        keyboard.append([
                            InlineKeyboardButton("✨ 精炼笔记", callback_data=f"refine_note:{archive_id}")
                        ])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await processing_msg.edit_text(result_msg, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    # 使用HTML解析模式（因为result_msg可能包含HTML链接）
                    await processing_msg.edit_text(result_msg, parse_mode='HTML')
                
                if success:
                    logger.info(f"Message archived: type={ContentAnalyzer.analyze(message).get('content_type')}")
            
            finally:
                # 确保进度消息被删除（如果还存在且未被修改为最终消息）
                # 这里只是兜底保护，正常情况下消息已在上面被edit为最终状态
                pass
        else:
            # 批量消息处理
            first_message = messages[0]
            processing_msg = await first_message.reply_text(
                lang_ctx.t('batch_processing_start', total=len(messages))
            )
            
            # 定义进度更新回调
            last_update_time = [0]  # 使用列表存储以便在闭包中修改
            
            async def update_progress(current, total, stage):
                """更新进度消息"""
                nonlocal last_update_time
                current_time = time.time()
                
                # 限制更新频率（每0.5秒最多更新一次）
                if current_time - last_update_time[0] < 0.5 and current < total:
                    return
                
                last_update_time[0] = current_time
                percentage = int((current / total) * 100) if total > 0 else 0
                
                try:
                    await processing_msg.edit_text(
                        f"📦 批量处理中\n"
                        f"阶段: {stage}\n"
                        f"进度: {current}/{total} ({percentage}%)"
                    )
                except Exception as e:
                    logger.debug(f"Progress update failed: {e}")
            
            # 调用批量处理（传递source_info和is_forwarded）
            results = await _process_batch_messages(
                messages, 
                context, 
                merged_caption,
                source_info=source_info,
                is_forwarded=is_forwarded,
                progress_callback=update_progress
            )
            
            # 统计结果
            success_count = sum(1 for success, _ in results if success)
            fail_count = len(results) - success_count
            
            if fail_count > 0:
                summary_msg = lang_ctx.t('batch_processing_complete', success=success_count, fail=fail_count)
            else:
                summary_msg = lang_ctx.t('batch_processing_complete_no_fail', success=success_count)
            
            await processing_msg.edit_text(summary_msg)
            logger.info(f"Batch archived: {success_count}/{len(messages)} messages")
            
    except Exception as e:
        logger.error(f"Error in batch callback: {e}", exc_info=True)


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
        
        # 检查是否是命令
        if message.text and message.text.startswith('/'):
            # 排除/cancel命令（已经在命令处理中）
            if message.text.startswith('/cancel'):
                return
            
            # 其他命令：提示用户选择
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚪 立即退出并保存笔记",
                        callback_data=f"note_exit_save:{message.text}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✍️ 继续记录笔记",
                        callback_data="note_continue"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                f"⚠️ 您正在笔记模式中\n\n"
                f"检测到命令：{message.text}\n\n"
                f"请选择操作：",
                reply_markup=reply_markup
            )
            
            # 暂存命令，等待用户选择后执行
            context.user_data['pending_command'] = message.text
            return
        
        # 重置超时计时器
        if 'note_timeout_job' in context.user_data:
            try:
                context.user_data['note_timeout_job'].schedule_removal()
            except:
                pass
        
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
        
        # 检查消息类型
        if message.text:
            # 文本消息：添加到笔记内容
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
            
            # 内存保护：限制单条消息长度
            MAX_MESSAGE_LENGTH = 4000  # Telegram消息长度限制
            if len(message.text) > MAX_MESSAGE_LENGTH:
                truncated_text = message.text[:MAX_MESSAGE_LENGTH] + "...[已截断]"
                note_messages.append(truncated_text)
            else:
                note_messages.append(message.text)
            
            context.user_data['note_messages'] = note_messages
            
            # 添加"结束记录"按钮
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[
                InlineKeyboardButton("🔚 结束记录并保存", callback_data="note_finish")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if len(message.text) > MAX_MESSAGE_LENGTH:
                await message.reply_text(
                    f"⚠️ 消息过长已截断\n✅ 已记录 ({len(note_messages)} 条)",
                    reply_to_message_id=message.message_id,
                    reply_markup=reply_markup
                )
            else:
                await message.reply_text(
                    f"✅ 已记录 ({len(note_messages)} 条)",
                    reply_to_message_id=message.message_id,
                    reply_markup=reply_markup
                )
            
            logger.debug(f"Note mode: recorded text message ({len(note_messages)} total)")
        
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
                        note_messages.append(f"[媒体] {caption}")
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


def _is_media_message(message: Message) -> bool:
    """判断是否为媒体消息"""
    return any([
        message.photo, message.video, message.document,
        message.audio, message.voice, message.animation,
        message.sticker, message.contact, message.location
    ])


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
        
        # 检查用户是否还在笔记模式
        if not context.user_data or not context.user_data.get('note_mode'):
            return
        
        # 生成并保存笔记
        await _finalize_note_internal(context, chat_id, reason="timeout")
        
        logger.info(f"Note mode timeout for user {job_data.get('user_id')}")
        
    except Exception as e:
        logger.error(f"Error in note timeout callback: {e}", exc_info=True)


async def _finalize_note_internal(context: ContextTypes.DEFAULT_TYPE, chat_id: int, reason: str = "manual") -> None:
    """
    完成笔记记录，生成并保存笔记（内部版本，减少内存占用）
    
    Args:
        context: Bot context
        chat_id: Chat ID
        reason: 退出原因 (manual, timeout, command)
    """
    try:
        messages = context.user_data.get('note_messages', [])
        archives = context.user_data.get('note_archives', [])
        
        if not messages:
            await context.bot.send_message(
                chat_id=chat_id,
                text="📝 笔记模式已退出\n\n⚠️ 未记录到任何消息"
            )
        else:
            # 合并所有文本消息（使用生成器减少内存）
            note_content = '\n\n'.join(messages)
            
            # 生成AI标题（如果AI可用）
            note_title = None
            ai_summarizer = context.bot_data.get('ai_summarizer')
            if ai_summarizer and ai_summarizer.is_available():
                try:
                    # 获取用户语言设置
                    from ..utils.config import get_config
                    config = get_config()
                    user_language = context.user_data.get('language', config.bot.get('language', 'zh-CN'))
                    
                    # 使用AI生成标题（32字以内）
                    note_title = await ai_summarizer.generate_title_from_text(
                        note_content, 
                        max_length=32,
                        language=user_language
                    )
                    logger.info(f"Generated AI title for note: {note_title}")
                except Exception as e:
                    logger.warning(f"Failed to generate AI title: {e}")
            
            # 转发笔记到Telegram频道
            storage_path = None
            telegram_storage = context.bot_data.get('telegram_storage')
            if telegram_storage:
                try:
                    from ..utils.config import get_config
                    config = get_config()
                    
                    # 获取笔记频道ID：NOTE -> TEXT -> default
                    # 优先使用NOTE频道
                    note_channel_key = config.get('storage.telegram.type_mapping.note', 'text')  # 默认映射到text
                    note_channel_id = config.get(f'storage.telegram.channels.{note_channel_key}', 0)
                    
                    # 如果NOTE频道未配置，降级到TEXT频道
                    if not note_channel_id:
                        note_channel_id = config.get('storage.telegram.channels.text', 0)
                    
                    # 如果TEXT频道也未配置，使用默认频道
                    if not note_channel_id:
                        note_channel_id = config.get('storage.telegram.channels.default', 0)
                        if not note_channel_id:
                            # 兼容旧配置
                            note_channel_id = config.get('storage.telegram.channel_id', 0)
                    
                    if note_channel_id:
                        # 准备转发的消息内容
                        forward_content = f"📝 笔记\n"
                        if note_title:
                            forward_content += f"标题：{note_title}\n\n"
                        forward_content += note_content
                        
                        # 限制消息长度（Telegram限制）
                        if len(forward_content) > 4000:
                            forward_content = forward_content[:3997] + "..."
                        
                        # 发送到频道
                        channel_msg = await context.bot.send_message(
                            chat_id=note_channel_id,
                            text=forward_content,
                            parse_mode=None
                        )
                        
                        # 生成频道消息链接
                        channel_username = str(note_channel_id)
                        if channel_username.startswith('-100'):
                            channel_id_numeric = channel_username[4:]
                        else:
                            channel_id_numeric = channel_username.lstrip('-')
                        
                        storage_path = f"https://t.me/c/{channel_id_numeric}/{channel_msg.message_id}"
                        logger.info(f"Note forwarded to channel: {storage_path}")
                    else:
                        logger.warning("No Telegram channel configured for notes")
                        
                except Exception as e:
                    logger.error(f"Failed to forward note to channel: {e}", exc_info=True)
            
            # 保存笔记
            note_manager = context.bot_data.get('note_manager')
            if note_manager:
                # 如果有归档，关联第一个归档
                archive_id = archives[0] if archives else None
                note_id = note_manager.add_note(
                    archive_id, 
                    note_content, 
                    title=note_title,
                    storage_path=storage_path
                )
                
                if note_id:
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
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text='\n'.join(result_parts),
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="❌ 笔记保存失败"
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ 笔记管理器未初始化"
                )
        
        # 立即清除所有笔记模式相关数据，释放内存
        keys_to_remove = ['note_mode', 'note_messages', 'note_archives', 'note_start_time', 'note_timeout_job', 'pending_command']
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
    except Exception as e:
        logger.error(f"Error finalizing note: {e}", exc_info=True)
        # 确保即使出错也清理内存
        for key in ['note_mode', 'note_messages', 'note_archives', 'note_start_time', 'note_timeout_job', 'pending_command']:
            context.user_data.pop(key, None)


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
                                        # 单个资源，直接发送文件
                                        result = await MessageBuilder.send_archive_resource(
                                            context.bot,
                                            message.chat_id,
                                            resources[0]
                                        )
                                        if not result:
                                            await message.reply_text(lang_ctx.t('resource_send_failed') if hasattr(lang_ctx, 't') else "发送资源失败")
                                
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
                                        result = await MessageBuilder.send_archive_resource(
                                            context.bot,
                                            message.chat_id,
                                            resources[0]
                                        )
                                        if not result:
                                            await message.reply_text("发送资源失败")
                                
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
