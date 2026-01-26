"""
Batch message processor
"""

import logging
from typing import List, Optional, Dict
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import get_language_context
from ...utils.helpers import format_file_size, truncate_text

logger = logging.getLogger(__name__)

from ...core.analyzer import ContentAnalyzer
from ...core.storage_manager import StorageManager


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
            
            # 统计结果
            success_count = sum(1 for success, _, _ in results if success)
            fail_count = len(results) - success_count
            
            if fail_count > 0:
                summary_msg = lang_ctx.t('batch_processing_complete', success=success_count, fail=fail_count)
            else:
                summary_msg = lang_ctx.t('batch_processing_complete_no_fail', success=success_count)
            
            await processing_msg.edit_text(summary_msg)
            logger.info(f"Batch archived: {success_count}/{len(messages)} messages")
            
    except Exception as e:
        logger.error(f"Error in batch callback: {e}", exc_info=True)
