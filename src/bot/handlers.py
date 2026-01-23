"""
Message handlers
Handles incoming messages for archiving
"""

import logging
from typing import List, Optional
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..core.analyzer import ContentAnalyzer
from ..core.storage_manager import StorageManager
from ..utils.i18n import get_i18n
from ..utils.helpers import format_file_size, truncate_text
from .message_aggregator import MessageAggregator
from ..core.ai_session import get_session_manager
from .ai_chat_router import handle_chat_message

logger = logging.getLogger(__name__)
import time

# 全局消息聚合器
_message_aggregator: Optional[MessageAggregator] = None


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
    i18n = get_i18n()
    
    try:
        # Analyze content
        if progress_callback:
            await progress_callback("📋 分析内容", 0.1)
        
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
            await progress_callback("🔍 检查重复文件", 0.2)
        
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
            await progress_callback("🤖 AI智能分析", 0.4)
        
        ai_summarizer = context.bot_data.get('ai_summarizer')
        ai_available = ai_summarizer and ai_summarizer.is_available()
        
        if ai_available:
            from ..utils.config import get_config
            config = get_config()
            
            # 1. 优先处理电子书判断（如果需要）
            if analysis.get('_needs_ai_ebook_check'):
                if progress_callback:
                    await progress_callback("📚 AI判断文档类型中...", 0.35)
                try:
                    file_name = analysis.get('file_name', '')
                    user_language = i18n.current_language
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
                        await progress_callback("🏷️ AI生成标签中...", 0.45)
                    try:
                        content_for_ai = analysis.get('content') or analysis.get('title', '')
                        if content_for_ai:
                            start = time.time()
                            ai_tags = await ai_summarizer.generate_tags(content_for_ai, 5)
                            duration = time.time() - start
                            provider = getattr(ai_summarizer, '_last_call_info', {}).get('provider', 'unknown')
                            logger.info(f"AI generate_tags provider={provider}, duration={duration:.2f}s")
                            if ai_tags:
                                existing_tags = analysis.get('tags', [])
                                analysis['tags'] = list(set(existing_tags + ai_tags))
                                logger.info(f"AI generated tags: {ai_tags}")
                    except Exception as e:
                        logger.warning(f"AI tag generation failed: {e}")
                
                # 自动生成摘要（仅对长文本）
                if config.ai.get('auto_summarize', False):
                    if progress_callback:
                        await progress_callback("📝 AI分析内容中...", 0.5)
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
                            user_language = i18n.current_language
                            
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
                                    await progress_callback("✅ AI分析完成", 0.6)
                    except Exception as e:
                        logger.warning(f"AI summary generation failed: {e}")
        
        # ========== AI 降级策略：AI 不可用时使用基础分析 ==========
        elif not ai_available and config.ai.get('auto_summarize', False):
            # AI 未配置或不可用，使用降级分析
            try:
                from ..ai.fallback import AIFallbackAnalyzer
                
                user_language = i18n.current_language
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
                await progress_callback("📝 AI生成标题中...", 0.62)
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
                    
                    user_language = i18n.current_language
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
                            await progress_callback("✅ 标题生成完成", 0.65)
            except Exception as e:
                logger.warning(f"AI title generation failed: {e}")
        
        # Get storage manager
        if progress_callback:
            await progress_callback("💾 保存归档", 0.7)
        
        storage_manager: StorageManager = context.bot_data.get('storage_manager')
        
        if not storage_manager:
            return False, "Storage manager not initialized"
        
        # Archive content
        success, result_msg, archive_id = await storage_manager.archive_content(message, analysis)
        
        if progress_callback:
            await progress_callback("✅ 完成", 1.0)
        
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
            await progress_callback("❌ 处理失败", 1.0)
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
                    from ..utils.i18n import get_i18n
                    i18n = get_i18n()
                    language = i18n.current_language
                    
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
                
                from ..utils.i18n import get_i18n
                i18n = get_i18n()
                language = i18n.current_language
                
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
                from ..utils.i18n import get_i18n
                i18n = get_i18n()
                language = i18n.current_language
                
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


async def _process_batch_messages(messages: List[Message], context: ContextTypes.DEFAULT_TYPE, merged_caption: Optional[str] = None, progress_callback=None) -> List[tuple]:
    """
    批量处理消息（优化：共享手动标签 + 独立AI标签）
    
    Args:
        messages: 消息列表
        context: Bot context
        merged_caption: 合并的caption文本（如果有）
        progress_callback: 进度回调函数 (current, total, stage)
        
    Returns:
        [(success, result_msg), ...]
    """
    i18n = get_i18n()
    results = []
    total = len(messages)
    
    # 阶段1: 分析内容 (0-20%)
    if progress_callback:
        await progress_callback(0, total, "分析内容")
    
    analyses = []
    for i, message in enumerate(messages):
        analysis = ContentAnalyzer.analyze(message)
        analyses.append(analysis)
        if progress_callback and (i + 1) % max(1, total // 10) == 0:
            await progress_callback(i + 1, total, "分析内容")
    
    # 阶段2: 提取共享标签 (20%)
    if progress_callback:
        await progress_callback(total, total, "提取标签")
    
    # 提取共享的hashtags（从merged_caption）- 这是用户主动输入的标签
    shared_hashtags = []
    if merged_caption:
        from ..utils.helpers import extract_hashtags
        shared_hashtags = extract_hashtags(merged_caption)
        logger.info(f"Extracted shared hashtags from caption: {shared_hashtags}")
    
    # 阶段3: AI处理 (20-50%)
    if progress_callback:
        await progress_callback(0, total, "AI生成标签")
    
    # 批量AI处理 - 为每个内容独立生成AI标签（并发执行，但不共享）
    ai_summarizer = context.bot_data.get('ai_summarizer')
    if ai_summarizer and ai_summarizer.is_available():
        from ..utils.config import get_config
        config = get_config()
        
        # 批量生成AI标签（每个内容独立）
        if config.ai.get('auto_generate_tags', False):
            try:
                # 准备每个内容的文本
                contents_for_ai = [
                    analysis.get('content') or analysis.get('title', '')
                    for analysis in analyses
                ]
                
                # 批量并发调用AI（但每个内容获得独立标签）
                start = time.time()
                batch_ai_tags = await ai_summarizer.batch_generate_tags(contents_for_ai, 3)
                duration = time.time() - start
                provider = getattr(ai_summarizer, '_last_call_info', {}).get('provider', 'batch')
                logger.info(f"AI batch_generate_tags provider={provider}, duration={duration:.2f}s")
                
                # 为每个分析结果添加其独立的AI标签
                for i, ai_tags in enumerate(batch_ai_tags):
                    if ai_tags:
                        existing_tags = analyses[i].get('tags', [])
                        analyses[i]['tags'] = list(set(existing_tags + ai_tags))
                        logger.debug(f"Item {i}: AI tags = {ai_tags}")
                
                logger.info(f"Batch AI generated independent tags for {len(messages)} messages")
            except Exception as e:
                logger.warning(f"Batch AI tag generation failed: {e}")
    
    if progress_callback:
        await progress_callback(total, total, "AI生成标签")
    
    # 阶段4: 应用标签 (50-60%)
    if progress_callback:
        await progress_callback(0, total, "应用标签")
    
    # 应用共享的hashtags到所有分析结果
    for i, analysis in enumerate(analyses):
        # 添加共享的hashtags（用户手动标签）
        if shared_hashtags:
            existing_hashtags = analysis.get('hashtags', [])
            analysis['hashtags'] = list(set(existing_hashtags + shared_hashtags))
        
        # 第一条消息附加caption到content（作为批注）
        if i == 0 and merged_caption:
            if analysis.get('content'):
                analysis['content'] = f"{analysis['content']}\n\n📝 批注: {merged_caption}"
            else:
                analysis['content'] = f"📝 批注: {merged_caption}"
    
    if progress_callback:
        await progress_callback(total, total, "应用标签")
    
    logger.info(f"Batch processing: shared hashtags={shared_hashtags}, each item has independent AI tags")
    
    # 阶段5: 批量存储 (60-100%)
    if progress_callback:
        await progress_callback(0, total, "存储到频道")
    
    # 批量存储（优化：使用storage_manager的批量方法）
    storage_manager: StorageManager = context.bot_data.get('storage_manager')
    if not storage_manager:
        return [(False, "Storage manager not initialized") for _ in messages]
    
    # 调用批量归档（带进度回调）
    results = await storage_manager.batch_archive_content(messages, analyses, progress_callback)
    
    if progress_callback:
        await progress_callback(total, total, "完成")
    
    return results


async def _batch_callback(messages: List[Message], merged_caption: Optional[str], update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    批次处理回调
    
    Args:
        messages: 消息列表
        merged_caption: 合并的caption
        update: Telegram update
        context: Bot context
    """
    i18n = get_i18n()
    
    try:
        if len(messages) == 1:
            # 单条消息处理
            message = messages[0]
            processing_msg = await message.reply_text("⏳ 正在处理...")
            
            try:
                # 定义进度更新回调
                async def update_progress(stage: str, progress: float):
                    try:
                        percentage = int(progress * 100)
                        progress_bar = '█' * (percentage // 5) + '░' * (20 - percentage // 5)
                        await processing_msg.edit_text(
                            f"⏳ {stage}\n"
                            f"进度: {percentage}%\n"
                            f"{progress_bar}"
                        )
                    except Exception as e:
                        logger.debug(f"Progress update failed: {e}")
                
                success, result_msg, archive_id, duplicate_info = await _process_single_message(message, context, merged_caption, update_progress)
                
                # 如果检测到重复文件，构建并发送重复提示消息
                if duplicate_info:
                    # 构建重复文件提示消息（使用HTML格式）
                    dup_msg = f"⚠️ 文件已存在\n\n"
                    
                    # 构建文件名（如果有频道链接则作为超链接）
                    file_title = duplicate_info.get('title', '未知')
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
                            dup_msg += f"📝 文件名：<a href='{file_link}'>{file_title}</a>\n"
                        else:
                            dup_msg += f"📝 文件名：{file_title}\n"
                    else:
                        dup_msg += f"📝 文件名：{file_title}\n"
                    
                    dup_msg += f"📦 大小：{format_file_size(duplicate_info.get('file_size', 0))}\n"
                    dup_msg += f"📅 归档时间：{duplicate_info.get('archived_at', '未知')}\n"
                    
                    # 获取标签
                    tag_manager = context.bot_data.get('tag_manager')
                    if tag_manager:
                        tags = tag_manager.get_archive_tags(duplicate_info['id'])
                        if tags:
                            tag_str = ' '.join([f"#{tag}" for tag in tags])
                            dup_msg += f"🏷️ 标签：{tag_str}"
                    
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
                f"📦 批量处理开始\n总数: {len(messages)} 条\n进度: 0% (0/{len(messages)})"
            )
            
            # 定义进度更新回调
            last_update_time = [0]  # 使用列表存储以便在闭包中修改
            import time
            
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
                        f"进度: {percentage}% ({current}/{total})\n"
                        f"{'█' * (percentage // 5)}{'░' * (20 - percentage // 5)}"
                    )
                except Exception as e:
                    # 忽略消息编辑过于频繁的错误
                    logger.debug(f"Progress update skipped: {e}")
            
            results = await _process_batch_messages(messages, context, merged_caption, update_progress)
            
            # 统计结果
            success_count = sum(1 for success, _ in results if success)
            fail_count = len(results) - success_count
            
            summary_msg = f"✅ 批量归档完成\n\n"
            summary_msg += f"成功: {success_count} 条\n"
            if fail_count > 0:
                summary_msg += f"失败: {fail_count} 条\n"
            summary_msg += f"\n💡 提示: 使用 /search 搜索已归档内容"
            
            await processing_msg.edit_text(summary_msg)
            logger.info(f"Batch archived: {success_count}/{len(messages)} messages")
            
    except Exception as e:
        logger.error(f"Error in batch callback: {e}", exc_info=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming message for archiving (with batch detection)
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        message = update.message
        i18n = get_i18n()
        
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
                                await message.reply_text(f"✅ 笔记已修改\n\n📝 归档 #{archive_id}")
                                logger.info(f"Modified note {note_id_to_modify} -> {new_note_id} for archive {archive_id}")
                            else:
                                await message.reply_text(i18n.t('note_add_failed'))
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
                                    await message.reply_text(f"✅ 笔记已追加\n\n📝 归档 #{archive_id}")
                                    logger.info(f"Appended to note {note_id_to_append} -> {new_note_id} for archive {archive_id}")
                                else:
                                    await message.reply_text(i18n.t('note_add_failed'))
                        # 清除追加模式标记
                        context.user_data.pop('note_append_mode', None)
                        context.user_data.pop('note_id_to_append', None)
                    else:
                        # 普通添加模式
                        note_id = note_manager.add_note(archive_id, message.text)
                        if note_id:
                            await message.reply_text(f"✅ 笔记已添加到归档 #{archive_id}\n\n📝 笔记ID: #{note_id}")
                            logger.info(f"Added note {note_id} to archive {archive_id}")
                        else:
                            await message.reply_text("❌ 笔记添加失败")
                else:
                    await message.reply_text("❌ 笔记管理器未初始化")
                
                # 清除等待状态
                context.user_data['waiting_note_for_archive'] = None
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
                        await message.reply_text("🤖 正在处理...")
                        
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
                            max_tokens=500
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
                                        f"✅ **笔记已精炼**\n\n"
                                        f"📝 归档 #{archive_id}\n\n"
                                        f"精炼后内容：\n{truncate_text(refined_content, 300)}",
                                        parse_mode=ParseMode.MARKDOWN
                                    )
                                    logger.info(f"Refined notes for archive {archive_id}")
                                else:
                                    await message.reply_text("❌ 保存精炼后的笔记失败")
                            else:
                                await message.reply_text("❌ 笔记管理器未初始化")
                        else:
                            await message.reply_text("❌ AI处理失败")
                            
                    except Exception as e:
                        logger.error(f"Error refining note: {e}", exc_info=True)
                        await message.reply_text(f"❌ 精炼失败: {str(e)}")
                else:
                    await message.reply_text("❌ AI功能未启用")
                
                # 清除等待状态
                context.user_data.pop('refine_note_context', None)
                return

        
        # AI Chat Mode - 如果用户已在AI会话中，优先处理
        if message.text and not message.forward_origin:
            text = message.text.strip()
            
            from ..utils.config import get_config
            config = get_config()
            ai_config = config.ai
            chat_enabled = ai_config.get('chat_enabled', False)
            
            if chat_enabled:
                # 检查是否已有活跃会话
                session_manager = get_session_manager(
                    ttl_seconds=ai_config.get('chat_session_ttl_seconds', 600)
                )
                user_id = str(message.from_user.id)
                session = session_manager.get_session(user_id)
                
                if session:
                    # 用户已在AI会话中，处理消息
                    try:
                        ai_response = await handle_chat_message(text, session, context)
                        
                        # 带🤖标识回复
                        await message.reply_text(f"🤖 {ai_response}")
                        
                        # 更新会话（保存上下文）
                        session_manager.update_session(user_id, session.get('context', {}))
                        
                        logger.info(f"AI chat response sent to user {user_id}")
                        return
                        
                    except Exception as e:
                        logger.error(f"AI chat error: {e}", exc_info=True)
                        await message.reply_text("❌ AI处理出错，已退出会话")
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
                    # 如果非常短（<50字符），询问用户意图
                    if len(text) < 50:
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
                            "💬 请问您需要做什么呢？",
                            reply_markup=reply_markup
                        )
                        logger.info(f"Asking user intent for short text: {text[:30]}")
                        return
                    
                    # 50-150字符（中文）或50-250字符（英文）的短文本，直接保存为笔记
                    note_manager = context.bot_data.get('note_manager')
                    if note_manager:
                        note_id = note_manager.add_note(None, text)
                        if note_id:
                            await message.reply_text(f"📝 笔记已保存 (ID: #{note_id})")
                            logger.info(f"Short text saved as standalone note: {note_id}")
                        else:
                            await message.reply_text(i18n.t('note_add_failed'))
                    return
        
        # 正常归档流程
        aggregator = get_message_aggregator()
        
        # 使用聚合器处理（自动检测批量）
        async def callback(messages: List[Message], merged_caption: Optional[str]):
            await _batch_callback(messages, merged_caption, update, context)
        
        await aggregator.process_message(message, callback)
        
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
