"""
Batch message processor
"""

import html
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
from .message_processor import _process_single_message, _auto_generate_note

logger = logging.getLogger(__name__)

from ...core.analyzer import ContentAnalyzer
from ...core.storage_manager import StorageManager


def _should_silent_archive(source_info: Optional[Dict], config) -> bool:
    """
    检查是否应该静默归档（不回复消息且删除转发消息）
    
    Args:
        source_info: 来源信息 {'name': str, 'id': int, 'type': str}
        config: 配置对象
        
    Returns:
        bool: True表示应该静默处理
    """
    if not source_info:
        return False
    
    silent_sources = config.get('bot.silent_sources', [])
    if not silent_sources:
        return False
    
    source_id = source_info.get('id')
    source_name = source_info.get('name', '')
    
    for silent_source in silent_sources:
        # 支持ID匹配（整数或字符串形式）
        if isinstance(silent_source, (int, str)):
            try:
                # 尝试转换为整数进行ID匹配
                silent_id = int(str(silent_source).replace('-100', '').replace('-', ''))
                check_id = int(str(source_id).replace('-100', '').replace('-', ''))
                if silent_id == check_id:
                    return True
            except (ValueError, TypeError):
                # 如果不是数字，进行用户名匹配
                silent_username = str(silent_source).strip().lstrip('@')
                source_username = source_name.strip().lstrip('@')
                if silent_username.lower() == source_username.lower():
                    return True
    
    return False



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
    original_captions = []
    source_name = source_info.get('name') if source_info else None
    for i, message in enumerate(messages):
        # 基础分析
        analysis = ContentAnalyzer.analyze(message)
        
        # link类型使用异步分析（Telegram预览提取）
        if analysis.get('content_type') == 'link':
            try:
                logger.debug(f"Link detected in batch message {i}, attempting Telegram preview extraction...")
                analysis = await ContentAnalyzer.analyze_async(message)
            except Exception as e:
                logger.warning(f"Async analyze failed for batch message {i}: {e}")
                # 已经有基础analysis，继续使用
        
        original_caption = analysis.get('content')
        original_captions.append(original_caption)
        
        # 清理转发消息尾部签名（来源名 + URL）
        if is_forwarded:
            cleaned_caption = remove_forward_signature(original_caption, source_name)
            if cleaned_caption != original_caption:
                analysis['content'] = cleaned_caption
                if analysis.get('title') == original_caption:
                    analysis['title'] = cleaned_caption or None
        
        analyses.append(analysis)
        if progress_callback and (i + 1) % max(1, total // 10) == 0:
            await progress_callback(i + 1, total, lang_ctx.t('batch_progress_analyzing'))
    
    # 阶段2: 提取共享标签 (20%)
    if progress_callback:
        await progress_callback(total, total, lang_ctx.t('batch_progress_extracting_tags'))
    
    # 提取共享的hashtags（从merged_caption）- 这是用户主动输入的标签
    cleaned_merged_caption = remove_forward_signature(merged_caption, source_name) if merged_caption else None
    shared_hashtags = []
    if cleaned_merged_caption:
        shared_hashtags = extract_hashtags(cleaned_merged_caption)
        logger.info(f"Extracted shared hashtags from caption: {shared_hashtags}")
    
    # 阶段3: AI处理 (20-50%) - 批量消息只分析一次合并的caption
    if progress_callback:
        await progress_callback(0, total, lang_ctx.t('batch_progress_ai_generating_tags'))
    
    # 批量AI处理 - 只对合并的caption+用户评论调用一次AI
    shared_ai_result = {'tags': [], 'title': None, 'summary': None}
    ai_summarizer = context.bot_data.get('ai_summarizer')
    if ai_summarizer and ai_summarizer.is_available():
        from ...utils.config import get_config
        config = get_config()
        
        # 只分析一次：使用merged_caption（包含用户评论）
        if config.ai.get('auto_generate_tags', False) and cleaned_merged_caption:
            try:
                start = time.time()
                max_tags = config.ai.get('max_generated_tags', 8)
                max_tags = max(3, min(max_tags, 5))  # 批量时限制在3-5之间
                
                # 生成标签
                ai_tags = await ai_summarizer.generate_tags(cleaned_merged_caption, max_tags, language=lang_ctx.language)
                duration = time.time() - start
                provider = getattr(ai_summarizer, '_last_call_info', {}).get('provider', 'single')
                logger.info(f"Batch AI single analysis: provider={provider}, duration={duration:.2f}s, tags={ai_tags}")
                
                if ai_tags:
                    shared_ai_result['tags'] = ai_tags
                
                # 生成标题（限制32字符）
                if config.ai.get('auto_generate_title', False):
                    ai_title = await ai_summarizer.generate_title_from_text(cleaned_merged_caption, max_length=32, language=lang_ctx.language)
                    if ai_title:
                        shared_ai_result['title'] = ai_title
                        logger.info(f"Batch AI generated title: {shared_ai_result['title']}")
                
                # 生成摘要（检查内容长度是否达到阈值）
                min_length = config.ai.get('min_content_length_for_summary', 150)
                if config.ai.get('auto_summarize', False) and len(cleaned_merged_caption) >= min_length:
                    ai_summary_result = await ai_summarizer.summarize_content(cleaned_merged_caption, language=lang_ctx.language)
                    if ai_summary_result and ai_summary_result.get('success'):
                        summary_text = ai_summary_result.get('summary', '')
                        if summary_text:
                            shared_ai_result['summary'] = summary_text
                            logger.info(f"Batch AI generated summary: {len(summary_text)} chars")
                
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
        # 添加来源信息头部到每条消息
        from ...utils.helpers import format_source_header
        source_header = format_source_header(messages[i], source_info)
        
        # 将来源信息添加到content开头
        if analysis.get('content'):
            analysis['content'] = f"{source_header}\n{analysis['content']}"
        else:
            analysis['content'] = source_header
        
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
        elif cleaned_merged_caption and not analysis.get('title'):
            # 截取caption前32字符作为标题
            analysis['title'] = cleaned_merged_caption[:32] + ('...' if len(cleaned_merged_caption) > 32 else '')
        
        # 第一条消息：如果有merged_caption且与原始content不同，添加批注标记
        # 注意：merged_caption通常就是caption本身，只在有用户额外评论时才不同
        if i == 0 and cleaned_merged_caption:
            existing_content = analysis.get('content', '')
            user_comment = extract_user_comment_from_merged(
                cleaned_merged_caption,
                analysis.get('content') or original_captions[i]
            )
            if user_comment:
                if existing_content:
                    analysis['content'] = f"{existing_content}\n📝 批注: {user_comment}"
                else:
                    analysis['content'] = f"📝 批注: {user_comment}"
    
    if progress_callback:
        await progress_callback(total, total, lang_ctx.t('batch_progress_applying_tags'))
    
    logger.info(f"Batch processing: shared hashtags={shared_hashtags}, each item has independent AI tags")
    
    # 阶段5: 批量存储 (60-100%)
    if progress_callback:
        await progress_callback(0, total, lang_ctx.t('batch_progress_storing'))
    
    # 批量存储（优化：使用storage_manager的批量方法）
    storage_manager: StorageManager = context.bot_data.get('storage_manager')
    if not storage_manager:
        return [(False, "Storage manager not initialized", None) for _ in messages]
    
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
    
    # 为每个成功归档的消息生成笔记
    # 提取批量用户评论和原始caption（来自batch aggregator）
    # 注意：这里需要从context.user_data或通过参数传递批次信息
    # 由于批量处理的特性，我们需要在调用这个函数时传递这些信息
    
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
    
    # 检查是否应该静默归档
    from ...utils.config import get_config
    config = get_config()
    should_silent = _should_silent_archive(source_info, config)
    
    try:
        if len(messages) == 1:
            # 单条消息处理
            message = messages[0]
            
            # 静默模式：不发送进度消息
            processing_msg = None if should_silent else await message.reply_text(lang_ctx.t('archive_processing'))
            msg_handled = False  # 跟踪进度消息是否已被处理
            
            try:
                # 定义进度更新回调
                async def update_progress(stage: str, progress: float):
                    if should_silent or not processing_msg:
                        return  # 静默模式不更新进度
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
                
                # 静默模式：处理完成后删除转发消息并返回
                if should_silent:
                    try:
                        await message.delete()
                        logger.info(f"Silent archive: deleted forwarded message from {source_info.get('name')}")
                    except Exception as e:
                        logger.warning(f"Failed to delete forwarded message: {e}")
                    msg_handled = True
                    return
                
                # 如果检测到重复文件，构建并发送重复提示消息
                if duplicate_info and processing_msg:
                    # 构建重复文件提示消息（使用HTML格式）
                    dup_msg = f"{lang_ctx.t('archive_duplicate_file')}\n\n"
                    
                    # 优化标题显示：优先使用title，否则截取content/caption（最多50字符）
                    raw_title = duplicate_info.get('title', '')
                    raw_content = duplicate_info.get('content', '')
                    
                    # 确定显示的标题
                    if raw_title and len(raw_title) <= 50:
                        file_title = raw_title
                    elif raw_title:
                        file_title = raw_title[:50] + '...'
                    elif raw_content:
                        # 没有title，使用content前50字符
                        file_title = raw_content[:50] + ('...' if len(raw_content) > 50 else '')
                    else:
                        file_title = lang_ctx.t('archive_duplicate_unknown_title')
                    
                    storage_path = duplicate_info.get('storage_path')
                    storage_type = duplicate_info.get('storage_type')
                    
                    # 构建带链接的文件名
                    if storage_path and storage_type == 'telegram':
                        from ...utils.config import get_config
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
                            dup_msg += lang_ctx.t('archive_duplicate_file_name', title=f"<a href='{file_link}'>{html.escape(file_title)}</a>") + "\n"
                        else:
                            dup_msg += lang_ctx.t('archive_duplicate_file_name', title=html.escape(file_title)) + "\n"
                    else:
                        dup_msg += lang_ctx.t('archive_duplicate_file_name', title=html.escape(file_title)) + "\n"
                    
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
                    msg_handled = True
                    return
                
                # 如果归档成功且有archive_id，添加操作按钮（包含精炼笔记）
                if success and archive_id and processing_msg:
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
                    msg_handled = True
                elif processing_msg:
                    # 使用HTML解析模式（因为result_msg可能包含HTML链接）
                    await processing_msg.edit_text(result_msg, parse_mode='HTML')
                    msg_handled = True
                
                if success:
                    logger.info(f"Message archived: type={ContentAnalyzer.analyze(message).get('content_type')}")
            
            except Exception as inner_e:
                # 捕获处理流程中的异常
                logger.error(f"Error in single message processing: {inner_e}", exc_info=True)
                
                # 尝试更新进度消息为错误状态
                if processing_msg and not msg_handled:
                    try:
                        await processing_msg.edit_text(
                            f"❌ {lang_ctx.t('archive_failed')}\n\n"
                            f"错误: {str(inner_e)[:100]}"
                        )
                        msg_handled = True
                    except Exception as edit_e:
                        logger.debug(f"Failed to update error message: {edit_e}")
            
            finally:
                # 确保进度消息被清理（兜底保护）
                if processing_msg and not msg_handled:
                    try:
                        await processing_msg.delete()
                        logger.warning("Progress message cleanup: deleted unhandled message")
                    except Exception as cleanup_e:
                        logger.debug(f"Failed to cleanup progress message: {cleanup_e}")
        else:
            # 批量消息处理
            first_message = messages[0]
            
            # 静默模式：不发送进度消息
            processing_msg = None if should_silent else await first_message.reply_text(
                lang_ctx.t('batch_processing_start', total=len(messages))
            )
            msg_handled = False  # 跟踪进度消息是否已被处理
            
            try:
                # 定义进度更新回调
                last_update_time = [0]  # 使用列表存储以便在闭包中修改
                
                async def update_progress(current, total, stage):
                    """更新进度消息"""
                    if should_silent or not processing_msg:
                        return  # 静默模式不更新进度
                        
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
                
                # 为批量归档生成共享的笔记
                # 批量消息应该共享一个笔记，关联到第一个成功的归档
                if results:
                    # 找到第一个成功的归档
                    first_success_archive_id = None
                    for success, msg, archive_id in results:
                        if success and archive_id:
                            first_success_archive_id = archive_id
                            break
                    
                    if first_success_archive_id:
                        # 从batch中提取用户评论和原始caption
                        # 需要区分用户的评论文本和媒体消息自带的caption
                        user_comment = None
                        original_caption = None
                        
                        # 查找用户自己发送的文本消息（非转发，非媒体）
                        for msg in messages:
                            if msg.text and not msg.forward_origin and not any([
                                msg.photo, msg.video, msg.document,
                                msg.audio, msg.voice, msg.animation
                            ]):
                                user_comment = msg.text
                                break
                        
                        # 查找媒体消息自带的caption
                        for msg in messages:
                            if msg.caption:
                                original_caption = msg.caption
                                break
                        
                        # 如果用户评论就是merged_caption且没有其他caption，则只保留用户评论
                        if user_comment == merged_caption and not original_caption:
                            pass  # 保持user_comment，不需要额外处理
                        elif not user_comment and merged_caption:
                            # merged_caption可能是用户评论
                            user_comment = merged_caption
                        
                        # 为第一个归档生成共享笔记（包含AI生成+用户评论+原始caption）
                        await _auto_generate_note(
                            archive_id=first_success_archive_id,
                            message=messages[0],
                            analysis=ContentAnalyzer.analyze(messages[0]),
                            context=context,
                            user_comment=user_comment,
                            original_caption=original_caption,
                            source_info=source_info
                        )
                        logger.info(f"Generated shared note for batch, linked to archive {first_success_archive_id}")
                
                # 静默模式：处理完成后删除所有转发消息并返回
                if should_silent:
                    for msg in messages:
                        try:
                            await msg.delete()
                        except Exception as e:
                            logger.warning(f"Failed to delete forwarded message: {e}")
                    logger.info(f"Silent archive: deleted {len(messages)} forwarded messages from {source_info.get('name')}")
                    msg_handled = True
                    return
                
                # 统计结果
                success_count = sum(1 for success, _, _ in results if success)
                fail_count = len(results) - success_count
                
                # 收集归档ID和详细信息
                archive_ids = [archive_id for success, _, archive_id in results if success and archive_id]
                first_id = min(archive_ids) if archive_ids else 0
                last_id = max(archive_ids) if archive_ids else 0
                
                # 统计内容类型
                type_counts = {}
                for i, (success, _, _) in enumerate(results):
                    if success and i < len(messages):
                        analysis = ContentAnalyzer.analyze(messages[i])
                        content_type = analysis.get('content_type', 'unknown')
                        type_name = lang_ctx.t(f'content_type_{content_type}', default=content_type)
                        type_counts[type_name] = type_counts.get(type_name, 0) + 1
                
                # 格式化内容类型统计
                types_str = '\n'.join([f"  • {t}: {c} 条" for t, c in type_counts.items()])
                
                # 获取标签（从第一个成功的归档）
                tags_str = "无"
                tag_manager = context.bot_data.get('tag_manager')
                if tag_manager and archive_ids:
                    tags = tag_manager.get_archive_tags(archive_ids[0])
                    if tags:
                        # 限制显示前5个标签
                        display_tags = tags[:5]
                        tags_str = ' '.join([f"#{tag}" for tag in display_tags])
                        if len(tags) > 5:
                            tags_str += f" (+{len(tags) - 5})"
                
                # 来源信息
                source_str = ""
                if source_info:
                    source_str = lang_ctx.t('batch_source_from', source=source_info.get('name', '未知'))
                else:
                    source_str = lang_ctx.t('batch_source_direct')
                
                # AI分析结果（从第一个成功的归档获取）
                ai_summary_str = ""
                if archive_ids:
                    db_storage = context.bot_data.get('db_storage')
                    if db_storage:
                        # 直接从数据库查询AI摘要
                        try:
                            result = db_storage.db.execute(
                                "SELECT ai_summary FROM archives WHERE id = ? AND deleted = 0",
                                (archive_ids[0],)
                            ).fetchone()
                            if result and result[0]:
                                summary = result[0]
                                # 限制摘要长度，避免消息过长
                                max_len = 150
                                if len(summary) > max_len:
                                    summary = summary[:max_len] + '...'
                                ai_summary_str = f"\n\n🤖 AI摘要:\n{summary}"
                        except Exception as e:
                            logger.debug(f"Failed to fetch AI summary: {e}")
                
                if fail_count > 0:
                    summary_msg = lang_ctx.t('batch_processing_complete', 
                                            success=success_count, 
                                            fail=fail_count,
                                            first_id=first_id,
                                            last_id=last_id,
                                            types=types_str,
                                            tags=tags_str,
                                            source=source_str) + ai_summary_str
                else:
                    summary_msg = lang_ctx.t('batch_processing_complete_no_fail', 
                                            success=success_count,
                                            first_id=first_id,
                                            last_id=last_id,
                                            types=types_str,
                                            tags=tags_str,
                                            source=source_str) + ai_summary_str
                
                if processing_msg:
                    await processing_msg.edit_text(summary_msg)
                    msg_handled = True
                logger.info(f"Batch archived: {success_count}/{len(messages)} messages")
            
            except Exception as batch_e:
                # 捕获批量处理中的异常
                logger.error(f"Error in batch message processing: {batch_e}", exc_info=True)
                
                # 尝试更新进度消息为错误状态
                if processing_msg and not msg_handled:
                    try:
                        await processing_msg.edit_text(
                            f"❌ 批量处理失败\n\n"
                            f"错误: {str(batch_e)[:100]}"
                        )
                        msg_handled = True
                    except Exception as edit_e:
                        logger.debug(f"Failed to update batch error message: {edit_e}")
            
            finally:
                # 确保进度消息被清理（兜底保护）
                if processing_msg and not msg_handled:
                    try:
                        await processing_msg.delete()
                        logger.warning("Batch progress message cleanup: deleted unhandled message")
                    except Exception as cleanup_e:
                        logger.debug(f"Failed to cleanup batch progress message: {cleanup_e}")
            
    except Exception as e:
        logger.error(f"Error in batch callback: {e}", exc_info=True)
    
    finally:
        # 清理转发检测器的等待状态（兜底保护，防止残留状态影响后续消息）
        try:
            from .forward_detector import get_forward_detector
            detector = get_forward_detector()
            user_id = str(update.effective_user.id) if update.effective_user else None
            if user_id:
                detector.cancel_wait(user_id)
        except Exception as cleanup_e:
            logger.debug(f"Failed to cleanup forward detector state: {cleanup_e}")
