"""
Message handlers
Handles incoming messages for archiving
"""

import logging
from typing import List, Optional
from telegram import Update, Message
from telegram.ext import ContextTypes

from ..core.analyzer import ContentAnalyzer
from ..core.storage_manager import StorageManager
from ..utils.i18n import get_i18n
from ..utils.helpers import format_file_size
from .message_aggregator import MessageAggregator

logger = logging.getLogger(__name__)

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
        (success, result_msg)
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
                    # 构建重复文件提示消息
                    dup_msg = f"⚠️ 文件已存在\n\n"
                    
                    # 构建文件名（如果有频道链接则作为超链接）
                    file_title = duplicate.get('title', '未知')
                    storage_path = duplicate.get('storage_path')
                    
                    if storage_path:
                        from ..utils.config import get_config
                        config = get_config()
                        channel_id = config.telegram_channel_id
                        if channel_id:
                            # 去掉-100前缀并构建链接
                            channel_id_str = str(channel_id).replace('-100', '')
                            message_id = storage_path
                            file_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                            dup_msg += f"📝 文件名：[{file_title}]({file_link})\n"
                        else:
                            dup_msg += f"📝 文件名：{file_title}\n"
                    else:
                        dup_msg += f"📝 文件名：{file_title}\n"
                    
                    dup_msg += f"📦 大小：{format_file_size(duplicate.get('file_size', 0))}\n"
                    dup_msg += f"📅 归档时间：{duplicate.get('archived_at', '未知')}\n"
                    
                    # 获取标签
                    tag_manager = context.bot_data.get('tag_manager')
                    if tag_manager:
                        tags = tag_manager.get_archive_tags(duplicate['id'])
                        if tags:
                            tag_str = ' '.join([f"#{tag}" for tag in tags])
                            dup_msg += f"🏷️ 标签：{tag_str}"
                    
                    await message.reply_text(dup_msg, parse_mode='Markdown')
                    logger.info(f"Duplicate file detected: {analysis.get('file_name')}, existing ID: {duplicate['id']}")
                    return False, "文件重复"
        
        # AI智能处理（如果启用）
        if progress_callback:
            await progress_callback("🤖 AI智能分析", 0.4)
        
        ai_summarizer = context.bot_data.get('ai_summarizer')
        if ai_summarizer and ai_summarizer.is_available():
            from ..utils.config import get_config
            config = get_config()
            
            # 判断是否应该进行AI分析
            content_type = analysis.get('content_type', '')
            file_size = analysis.get('file_size', 0)
            
            # 可分析的内容类型：文本、链接、文档
            analyzable_types = ['text', 'link', 'article', 'document']
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
                    try:
                        content_for_ai = analysis.get('content') or analysis.get('title', '')
                        if content_for_ai:
                            ai_tags = await ai_summarizer.generate_tags(content_for_ai, 5)
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
                        file_name = analysis.get('file_name', '').lower()
                        
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
                            from ..utils.i18n import get_i18n
                            i18n = get_i18n()
                            user_language = i18n.current_language
                            
                            # 构建上下文信息
                            context_info = {
                                'content_type': content_type,
                                'file_size': file_size or 0,
                                'existing_tags': analysis.get('tags', []),
                                'title': analysis.get('title', ''),
                                'file_extension': analysis.get('file_name', '').split('.')[-1] if analysis.get('file_name') else ''
                            }
                            
                            summary_result = await ai_summarizer.summarize_content(
                                content_for_ai, 
                                language=user_language,
                                context=context_info
                            )
                            if summary_result.get('success'):
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
                    except Exception as e:
                        logger.warning(f"AI summary generation failed: {e}")
        
        # Get storage manager
        if progress_callback:
            await progress_callback("💾 保存归档", 0.7)
        
        storage_manager: StorageManager = context.bot_data.get('storage_manager')
        
        if not storage_manager:
            return False, "Storage manager not initialized"
        
        # Archive content
        success, result_msg = await storage_manager.archive_content(message, analysis)
        
        if progress_callback:
            await progress_callback("✅ 完成", 1.0)
        
        return success, result_msg
        
    except Exception as e:
        if progress_callback:
            await progress_callback("❌ 处理失败", 1.0)
        raise


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
                batch_ai_tags = await ai_summarizer.batch_generate_tags(contents_for_ai, 3)
                
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
            
            success, result_msg = await _process_single_message(message, context, merged_caption, update_progress)
            await processing_msg.edit_text(result_msg)
            
            if success:
                logger.info(f"Message archived: type={ContentAnalyzer.analyze(message).get('content_type')}")
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
