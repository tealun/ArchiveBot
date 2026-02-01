"""
Storage manager module
Manages content storage across different providers
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from telegram import Message

from ..storage.database import DatabaseStorage
from ..storage.telegram import TelegramStorage
from ..core.tag_manager import TagManager
from ..core.analyzer import ContentAnalyzer
from ..utils.helpers import format_datetime, format_file_size
from ..utils.i18n import get_i18n
from ..utils.config import get_config
from ..utils.constants import (
    TELEGRAM_MAX_SIZE,
    STORAGE_DATABASE,
    STORAGE_TELEGRAM,
    STORAGE_REFERENCE
)

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages content storage strategy and execution
    """
    
    def __init__(
        self, 
        db_storage: DatabaseStorage, 
        tag_manager: TagManager,
        telegram_storage: Optional[TelegramStorage] = None
    ):
        """
        Initialize storage manager
        
        Args:
            db_storage: DatabaseStorage instance
            tag_manager: TagManager instance
            telegram_storage: TelegramStorage instance (optional)
        """
        self.db_storage = db_storage
        self.tag_manager = tag_manager
        self.telegram_storage = telegram_storage
        self.ai_cache = None  # Will be set by main.py
        self.i18n = get_i18n()
    
    def set_ai_cache(self, ai_cache):
        """Set AI data cache instance (called after initialization)"""
        self.ai_cache = ai_cache
    
    def _invalidate_ai_cache(self):
        """失效AI数据缓存"""
        if self.ai_cache:
            self.ai_cache.invalidate('statistics', 'recent_samples', 'tag_analysis')
            logger.debug("AI cache invalidated")
    
    async def batch_archive_content(self, messages: list, analyses: list, source_info: Optional[Dict[str, Any]] = None, is_batch_forwarded: bool = False, progress_callback=None) -> list:
        """
        批量归档内容（优化：批量存储到Telegram频道）
        
        Args:
            messages: 消息列表
            analyses: 分析结果列表
            source_info: 批次来源信息（从batch中提取）
            is_batch_forwarded: 批次是否为转发消息
            progress_callback: 进度回调函数 (current, total, stage)
            
        Returns:
            [(success, message, archive_id), ...]
        """
        if len(messages) != len(analyses):
            logger.error(f"Messages and analyses count mismatch: {len(messages)} vs {len(analyses)}")
            return [(False, "Internal error", None) for _ in messages]
        
        results = []
        total = len(messages)
        
        # 收集需要存储到Telegram的文件
        telegram_indices = []
        telegram_metadata_list = []
        
        # 对于批次消息，确定是否为直发（批次中无转发信息则认为是直发）
        is_direct_send = not is_batch_forwarded
        
        for i, (message, analysis) in enumerate(zip(messages, analyses)):
            content_type = analysis.get('content_type')
            storage_type = self._determine_storage_type(content_type, analysis.get('file_size'))
            
            if storage_type == STORAGE_TELEGRAM and self.telegram_storage:
                telegram_indices.append(i)
                
                # 收集标签用于频道选择
                collected_tags = []
                collected_tags.extend(analysis.get('hashtags', []))
                collected_tags.extend(analysis.get('tags', []))
                
                # 根据规则确定频道
                target_channel_id = self._determine_channel_id(
                    content_type=content_type,
                    tags=collected_tags,
                    source_info=source_info,
                    is_direct_send=is_direct_send
                )
                
                metadata = {
                    'file_id': analysis.get('file_id'),
                    'content_type': content_type,
                    'caption': analysis.get('content') or analysis.get('title'),  # 使用content（含批注），回退到title
                    'file_size': analysis.get('file_size', 0)
                }
                
                # 如果确定了特定频道，添加override
                if target_channel_id:
                    metadata['override_channel_id'] = target_channel_id
                
                telegram_metadata_list.append(metadata)
        
        # 批量存储到Telegram（如果有）
        telegram_storage_paths = []
        if telegram_indices:
            logger.info(f"Batch storing {len(telegram_indices)} files to Telegram channel")
            telegram_storage_paths = await self.telegram_storage.batch_store(telegram_metadata_list)
        
        # 逐个创建数据库记录（带进度更新）
        for i, (message, analysis) in enumerate(zip(messages, analyses)):
            try:
                content_type = analysis.get('content_type')
                
                if content_type == 'error':
                    results.append((False, self.i18n.t('archive_failed', error=analysis.get('error', 'Unknown')), None))
                    continue
                
                # Determine storage
                storage_type = self._determine_storage_type(content_type, analysis.get('file_size'))
                storage_path = None
                storage_provider = None
                
                # 检查是否是批量存储的
                if i in telegram_indices:
                    idx_in_batch = telegram_indices.index(i)
                    storage_path = telegram_storage_paths[idx_in_batch]
                    if storage_path:
                        storage_provider = 'telegram_channel'
                    else:
                        storage_type = STORAGE_REFERENCE
                        logger.warning(f"Batch store failed for item {i}, downgraded to reference")
                
                # Create archive entry
                message = messages[i] if i < len(messages) else None
                media_group_id = message.media_group_id if message and hasattr(message, 'media_group_id') else None
                
                archive_id = self.db_storage.create_archive(
                    content_type=content_type,
                    storage_type=storage_type,
                    title=analysis.get('title'),
                    content=analysis.get('content'),
                    file_id=analysis.get('file_id'),
                    storage_provider=storage_provider,
                    storage_path=storage_path,
                    file_size=analysis.get('file_size'),
                    source=analysis.get('source'),
                    metadata={
                        'file_name': analysis.get('file_name'),
                        'mime_type': analysis.get('mime_type'),
                        'url': analysis.get('url'),
                    },
                    ai_summary=analysis.get('ai_summary'),
                    ai_key_points=analysis.get('ai_key_points'),
                    ai_category=analysis.get('ai_category'),
                    media_group_id=media_group_id
                )
                
                # Generate and add tags
                all_tags = []
                
                # Auto tags
                auto_tags = self.tag_manager.generate_auto_tags(content_type)
                if auto_tags:
                    self.tag_manager.add_tags_to_archive(archive_id, auto_tags, 'auto')
                    all_tags.extend(auto_tags)
                
                # Manual tags from hashtags
                manual_tags = analysis.get('hashtags', [])
                if manual_tags:
                    self.tag_manager.add_tags_to_archive(archive_id, manual_tags, 'manual')
                    all_tags.extend(manual_tags)
                
                # AI tags
                ai_tags = analysis.get('tags', [])
                if ai_tags:
                    unique_ai_tags = [tag for tag in ai_tags if tag not in all_tags]
                    if unique_ai_tags:
                        self.tag_manager.add_tags_to_archive(archive_id, unique_ai_tags, 'ai')
                        all_tags.extend(unique_ai_tags)
                
                # Success message (使用MessageBuilder统一构建)
                from ..utils.message_builder import MessageBuilder
                
                # 获取bot实例（从 telegram_storage 中获取）
                bot = self.telegram_storage.bot if self.telegram_storage else None
                
                success_msg = await MessageBuilder.build_archive_success_message(
                    archive_data={
                        'title': analysis.get('title'),
                        'content': analysis.get('content'),
                        'caption': analysis.get('caption'),  # 添加caption
                        'content_type': content_type,
                        'file_size': analysis.get('file_size', 0),
                        'tags': all_tags,
                        'storage_type': storage_type,
                        'storage_provider': storage_provider,
                        'storage_path': storage_path,
                        'source': analysis.get('source', '直接发送'),
                        'ai_title': analysis.get('ai_title'),  # 添加AI标题
                        'ai_summary': analysis.get('ai_summary'),
                        'ai_category': analysis.get('ai_category'),
                        'ai_key_points': analysis.get('ai_key_points', [])
                    },
                    i18n=self.i18n,
                    include_ai_info=True,
                    bot=bot
                )
                
                results.append((True, success_msg, archive_id))
                
                # 更新进度
                if progress_callback and (i + 1) % max(1, total // 20) == 0:
                    await progress_callback(i + 1, total, "存储到频道")
                
            except Exception as e:
                logger.error(f"Error in batch archive item {i}: {e}", exc_info=True)
                results.append((False, str(e), None))
        
        logger.info(f"Batch archived {sum(1 for s, _, _ in results if s)}/{len(results)} items")
        return results
    
    async def archive_content(
        self,
        message: Message,
        analysis: Dict[str, Any],
        source_info: Dict[str, Any] = None,
        is_direct_send: bool = False
    ) -> Tuple[bool, str]:
        """
        Archive content based on analysis
        
        Args:
            message: Telegram message object
            analysis: Content analysis result
            source_info: 消息来源信息 {'name': str, 'id': int, 'type': str}
            is_direct_send: 是否为个人直接发送（非转发）
            
        Returns:
            Tuple of (success, message)
        """
        try:
            content_type = analysis.get('content_type')
            
            if content_type == 'error':
                return False, self.i18n.t('archive_failed', error=analysis.get('error', 'Unknown'))
            
            # Determine storage type
            storage_type = self._determine_storage_type(content_type, analysis.get('file_size'))
            logger.info(f"Determined storage type: {storage_type} for {content_type} (size: {analysis.get('file_size')})")
            
            # 收集标签（用于频道选择）
            collected_tags = []
            collected_tags.extend(analysis.get('hashtags', []))
            collected_tags.extend(analysis.get('tags', []))
            
            # Store file if needed
            storage_path = None
            storage_provider = None
            
            # 先创建archive记录（获取archive_id用于生成按钮）
            archive_id = self.db_storage.create_archive(
                content_type=content_type,
                storage_type=storage_type,
                title=analysis.get('title'),
                content=analysis.get('content'),
                file_id=analysis.get('file_id'),
                storage_provider=storage_provider,
                storage_path=storage_path or '',  # 临时为空，后面会更新
                file_size=analysis.get('file_size'),
                source=analysis.get('source'),
                metadata={
                    'file_name': analysis.get('file_name'),
                    'mime_type': analysis.get('mime_type'),
                    'url': analysis.get('url'),
                },
                ai_summary=analysis.get('ai_summary'),
                ai_key_points=analysis.get('ai_key_points'),
                ai_category=analysis.get('ai_category'),
                media_group_id=message.media_group_id if hasattr(message, 'media_group_id') else None
            )
            
            # 常规存储逻辑（传递archive_id用于生成按钮）
            if storage_type == STORAGE_TELEGRAM and self.telegram_storage and not storage_path:
                # Store to Telegram channel
                try:
                    storage_path = await self._store_to_telegram(
                        analysis,
                        tags=collected_tags,
                        source_info=source_info,
                        is_direct_send=is_direct_send,
                        archive_id=archive_id  # 传递archive_id用于生成按钮
                    )
                    if storage_path:
                        storage_provider = 'telegram_channel'
                        logger.info(f"File stored to Telegram: {storage_path}")
                        # 更新storage_path
                        self.db_storage.db.execute(
                            "UPDATE archives SET storage_path = ?, storage_provider = ? WHERE id = ?",
                            (storage_path, storage_provider, archive_id)
                        )
                        self.db_storage.db.commit()
                    else:
                        # Fallback to reference only
                        storage_type = STORAGE_REFERENCE
                        logger.warning(f"Failed to store to Telegram, downgraded to reference: {content_type}")
                        self.db_storage.db.execute(
                            "UPDATE archives SET storage_type = ? WHERE id = ?",
                            (storage_type, archive_id)
                        )
                        self.db_storage.db.commit()
                except Exception as e:
                    logger.error(f"Error storing to Telegram: {e}", exc_info=True)
                    storage_type = STORAGE_REFERENCE
                    logger.warning(f"Exception during Telegram storage, downgraded to reference: {content_type}")
                    self.db_storage.db.execute(
                        "UPDATE archives SET storage_type = ? WHERE id = ?",
                        (storage_type, archive_id)
                    )
                    self.db_storage.db.commit()
            
            # 特殊处理：link类型如果有PDF，存储PDF到document频道
            if content_type == 'link' and analysis.get('web_archive_pdf') and not storage_path:
                try:
                    pdf_path = await self._store_link_pdf(
                        analysis=analysis,
                        tags=collected_tags,
                        source_info=source_info,
                        is_direct_send=is_direct_send,
                        archive_id=archive_id
                    )
                    
                    if pdf_path:
                        storage_path = pdf_path
                        storage_provider = 'telegram_channel_pdf'
                        storage_type = STORAGE_TELEGRAM
                        logger.info(f"Link PDF stored to document channel: {pdf_path}")
                        # 更新storage_path
                        self.db_storage.db.execute(
                            "UPDATE archives SET storage_path = ?, storage_provider = ?, storage_type = ? WHERE id = ?",
                            (storage_path, storage_provider, storage_type, archive_id)
                        )
                        self.db_storage.db.commit()
                    else:
                        logger.warning("Failed to store link PDF, will use text storage")
                        
                except Exception as e:
                    logger.error(f"Error storing link PDF: {e}", exc_info=True)
            
            # 触发AI数据缓存失效（新归档添加）
            self._invalidate_ai_cache()
            
            # Generate and add tags
            all_tags = []
            
            # Auto tags based on content type
            auto_tags = self.tag_manager.generate_auto_tags(content_type)
            if auto_tags:
                self.tag_manager.add_tags_to_archive(archive_id, auto_tags, 'auto')
                all_tags.extend(auto_tags)
            
            # Manual tags from hashtags
            manual_tags = analysis.get('hashtags', [])
            if manual_tags:
                self.tag_manager.add_tags_to_archive(archive_id, manual_tags, 'manual')
                all_tags.extend(manual_tags)
            
            # AI tags from analysis (修复：从'tags'字段获取AI生成的标签)
            ai_tags = analysis.get('tags', [])
            if ai_tags:
                # 过滤掉已经添加的auto和manual标签
                unique_ai_tags = [tag for tag in ai_tags if tag not in all_tags]
                if unique_ai_tags:
                    self.tag_manager.add_tags_to_archive(archive_id, unique_ai_tags, 'ai')
                    all_tags.extend(unique_ai_tags)
                    logger.info(f"Added AI tags: {unique_ai_tags}")
            
            # Format success message (使用MessageBuilder统一构建)
            from ..utils.message_builder import MessageBuilder
            
            # 获取bot实例（从 telegram_storage 中获取）
            bot = self.telegram_storage.bot if self.telegram_storage else None
            
            success_msg = await MessageBuilder.build_archive_success_message(
                archive_data={
                    'title': analysis.get('title'),
                    'content': analysis.get('content'),
                    'caption': analysis.get('caption'),  # 添加caption
                    'content_type': content_type,
                    'file_size': analysis.get('file_size', 0),
                    'tags': all_tags,
                    'storage_type': storage_type,
                    'storage_provider': storage_provider,
                    'storage_path': storage_path,
                    'source': analysis.get('source', '直接发送'),
                    'ai_title': analysis.get('ai_title'),  # 添加AI标题
                    'ai_summary': analysis.get('ai_summary'),
                    'ai_category': analysis.get('ai_category'),
                    'ai_key_points': analysis.get('ai_key_points', [])
                },
                i18n=self.i18n,
                include_ai_info=True,
                bot=bot
            )
            
            logger.info(f"Successfully archived content: archive_id={archive_id}")
            return True, success_msg, archive_id
            
        except Exception as e:
            logger.error(f"Error archiving content: {e}", exc_info=True)
            return False, self.i18n.t('archive_failed', error=str(e)), None
    
    def _determine_channel_id(
        self, 
        content_type: str, 
        tags: List[str] = None,
        source_info: Dict[str, Any] = None,
        is_direct_send: bool = False
    ) -> Optional[int]:
        """
        根据多种规则确定存储频道ID（优先级从高到低）
        
        优先级:
        1. 标签匹配 (tag_mapping)
        2. 来源匹配 (source_mapping)
        3. 个人直发配置 (direct_send)
        4. 内容类型映射 (type_mapping)
        5. 默认频道 (default)
        
        Args:
            content_type: 内容类型
            tags: 标签列表
            source_info: 来源信息 {'name': str, 'id': int, 'type': str}
            is_direct_send: 是否为个人直接发送
            
        Returns:
            频道ID或None
        """
        config = get_config()
        
        # 优先级1: 标签匹配
        if tags:
            tag_mapping = config.get('storage.telegram.tag_mapping', [])
            if tag_mapping:
                for mapping in tag_mapping:
                    mapping_tags = mapping.get('tags', [])
                    channel_id = mapping.get('channel_id')
                    if channel_id and any(tag in mapping_tags for tag in tags):
                        logger.info(f"Channel determined by tag mapping: {channel_id} (matched tags: {[t for t in tags if t in mapping_tags]})")
                        return channel_id
        
        # 优先级2: 来源匹配
        if source_info:
            source_mapping = config.get('storage.telegram.source_mapping', [])
            if source_mapping:
                source_name = source_info.get('name', '')
                source_id = source_info.get('id')
                
                logger.debug(f"Checking source mapping: source_name='{source_name}', source_id={source_id}, source_type={source_info.get('type')}")
                
                for mapping in source_mapping:
                    sources = mapping.get('sources', [])
                    channel_id = mapping.get('channel_id')
                    if channel_id and sources:
                        # 检查名称匹配
                        if source_name in sources:
                            logger.info(f"Channel determined by source mapping (name): {channel_id} (source: {source_name})")
                            return channel_id
                        
                        # 检查ID匹配（支持多种格式）
                        if source_id:
                            for src in sources:
                                if isinstance(src, int):
                                    # 直接匹配
                                    if source_id == src:
                                        logger.info(f"Channel determined by source mapping (id): {channel_id} (source_id: {source_id})")
                                        return channel_id
                                    
                                    # 尝试-100格式转换匹配
                                    # 配置: -1003024714275, API返回可能是: -1003024714275 或 3024714275 或 -3024714275
                                    src_str = str(src)
                                    source_id_str = str(source_id)
                                    
                                    # 去掉-100前缀比较
                                    src_without_100 = src_str.replace('-100', '') if src_str.startswith('-100') else src_str
                                    source_without_100 = source_id_str.replace('-100', '') if source_id_str.startswith('-100') else source_id_str
                                    
                                    if src_without_100.lstrip('-') == source_without_100.lstrip('-'):
                                        logger.info(f"Channel determined by source mapping (id normalized): {channel_id} (config: {src}, actual: {source_id})")
                                        return channel_id
                
                logger.debug(f"No source mapping matched for source: {source_name or source_id}")
        
        # 优先级3: 个人直发配置
        if is_direct_send:
            # 重要：不要用config.get获取整个节点（会绕过环境变量覆盖）
            # 而是用具体路径逐个获取值，这样才能触发环境变量优先机制
            
            # 检查是否启用了直发配置
            direct_enabled = config.get('storage.telegram.direct_send.channels.default') is not None
            
            if direct_enabled:
                # 1. 优先尝试type_mapping映射（从环境变量无法配置dict，所以只能从yaml读取）
                direct_type_mapping = config._config.get('storage', {}).get('telegram', {}).get('direct_send', {}).get('type_mapping')
                if direct_type_mapping and isinstance(direct_type_mapping, dict):
                    channel_key = direct_type_mapping.get(content_type)
                    if channel_key:
                        # 通过具体路径获取频道ID（触发环境变量覆盖）
                        channel_id = config.get(f'storage.telegram.direct_send.channels.{channel_key}')
                        if channel_id:
                            logger.info(f"Channel determined by direct_send config: {channel_id} (type: {content_type} -> {channel_key})")
                            return channel_id
                
                # 2. 使用default频道（通过具体路径获取，触发环境变量覆盖）
                default_channel = config.get('storage.telegram.direct_send.channels.default')
                if default_channel:
                    logger.info(f"Channel determined by direct_send default: {default_channel}")
                    return default_channel
        
        # 优先级4和5: 使用TelegramStorage的默认逻辑（类型映射+默认频道）
        # 返回None让TelegramStorage自己处理
        logger.debug(f"No specific channel rule matched, using TelegramStorage default logic")
        return None
    
    async def _store_link_pdf(
        self,
        analysis: Dict[str, Any],
        tags: List[str] = None,
        source_info: Dict[str, Any] = None,
        is_direct_send: bool = False,
        archive_id: Optional[int] = None
    ) -> Optional[str]:
        """
        存储link类型的PDF到document频道
        
        Args:
            analysis: Content analysis result (must contain web_archive_pdf)
            tags: 标签列表
            source_info: 来源信息
            is_direct_send: 是否为个人直接发送
            
        Returns:
            Storage path or None
        """
        if not self.telegram_storage or not self.telegram_storage.is_available():
            logger.warning("Telegram storage not available for PDF")
            return None
        
        pdf_bytes = analysis.get('web_archive_pdf')
        if not pdf_bytes:
            logger.warning("No PDF bytes in analysis")
            return None
        
        try:
            import io
            from datetime import datetime
            import html
            
            # 准备PDF文件
            pdf_file = io.BytesIO(pdf_bytes)
            
            title = analysis.get('title', 'webpage')
            url = analysis.get('url', '')
            
            # 解码HTML实体后再生成文件名
            title_decoded = html.unescape(title)
            
            # 生成文件名（只保留安全字符）
            safe_title = "".join(c for c in title_decoded[:50] if c.isalnum() or c in (' ', '-', '_', '–', '—')).strip()
            if not safe_title:
                safe_title = "webpage"
            
            file_name = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_file.name = file_name
            
            # 确定目标频道（document类型）
            # link的PDF应该存到document频道，不是text频道
            target_channel_id = self._determine_channel_id(
                content_type='document',  # 使用document类型映射
                tags=tags,
                source_info=source_info,
                is_direct_send=is_direct_send
            )
            
            if not target_channel_id:
                # Fallback到默认document频道
                config = get_config()
                target_channel_id = config.get('storage.telegram.channels.document')
            
            if not target_channel_id:
                logger.error("No document channel configured for PDF storage")
                return None
            
            # 构建caption
            web_summary = analysis.get('web_archive_summary', '')
            # web_archive_summary 可能是字符串或字典
            if isinstance(web_summary, dict):
                summary = web_summary.get('text', '') or web_summary.get('summary', '')
            else:
                summary = str(web_summary) if web_summary else ''
            
            # 解码HTML实体（如 &#8211; → –）
            import html
            title_decoded = html.unescape(title)
            url_decoded = html.unescape(url)
            summary_decoded = html.unescape(summary) if summary else ''
            
            caption_parts = [
                f"🔗 网页存档 - {title_decoded}",
                f"\n📄 来源: {url_decoded}",
            ]
            
            if summary_decoded:
                # 截断长摘要
                summary_text = summary_decoded[:300] + "..." if len(summary_decoded) > 300 else summary_decoded
                caption_parts.append(f"\n\n📝 摘要:\n{summary_text}")
            
            caption = "".join(caption_parts)
            
            # 发送PDF
            logger.info(f"Sending PDF to document channel {target_channel_id}: {file_name} ({len(pdf_bytes)} bytes)")
            
            # 生成按钮（如果有archive_id）
            reply_markup = None
            if archive_id:
                # 查询是否有笔记（用于按钮状态）
                result = self.db_storage.db.execute(
                    "SELECT COUNT(*) as count FROM notes WHERE archive_id = ?",
                    (archive_id,)
                ).fetchone()
                has_notes = result['count'] > 0 if result else False
                
                # 查询精选状态
                fav_result = self.db_storage.db.execute(
                    "SELECT favorite FROM archives WHERE id = ?",
                    (archive_id,)
                ).fetchone()
                is_favorite = fav_result['favorite'] == 1 if fav_result else False
                
                # 生成按钮（复用telegram.py的逻辑）
                reply_markup = self.telegram_storage._create_archive_buttons(archive_id, has_notes, is_favorite)
            
            message = await self.telegram_storage.bot.send_document(
                chat_id=target_channel_id,
                document=pdf_file,
                caption=caption[:1024],  # Telegram caption限制
                filename=file_name,
                reply_markup=reply_markup
            )
            
            if message and message.document:
                storage_path = f"{target_channel_id}:{message.message_id}:{message.document.file_id}"
                logger.info(f"Link PDF stored successfully: {storage_path}")
                return storage_path
            else:
                logger.error("Failed to send PDF: no message returned")
                return None
                
        except Exception as e:
            logger.error(f"Error storing link PDF: {e}", exc_info=True)
            return None
    
    async def _store_to_telegram(
        self, 
        analysis: Dict[str, Any],
        tags: List[str] = None,
        source_info: Dict[str, Any] = None,
        is_direct_send: bool = False,
        archive_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Store file to Telegram channel
        
        Args:
            analysis: Content analysis result
            tags: 标签列表（用于频道选择）
            source_info: 来源信息（用于频道选择）
            is_direct_send: 是否为个人直接发送
            
        Returns:
            Storage path or None
        """
        if not self.telegram_storage or not self.telegram_storage.is_available():
            logger.warning("Telegram storage not available")
            return None
        
        content_type = analysis.get('content_type')
        file_id = analysis.get('file_id')
        file_size = analysis.get('file_size', 0)
        
        # 文本和链接类型不需要file_id
        if content_type not in ['text', 'link']:
            # 检查必需字段
            if not file_id:
                logger.error(f"No file_id in analysis for {content_type}")
                return None
        
        # 确定存储频道（根据多种规则）
        target_channel_id = self._determine_channel_id(
            content_type=content_type,
            tags=tags,
            source_info=source_info,
            is_direct_send=is_direct_send
        )
        
        # 构建metadata
        # 对于媒体类型（非text/link），如果content包含来源信息，使用它作为caption
        # text/link类型，content包含完整的来源信息和正文，会被telegram.py特殊处理
        # 媒体类型，content可能包含 "来源信息\n用户caption"，适合作为caption显示
        caption = None
        if content_type in ['text', 'link']:
            # text/link类型不需要caption，使用content字段
            caption = None
        else:
            # 媒体类型：优先使用content（已包含来源信息），fallback到title
            if analysis.get('content'):
                caption = analysis.get('content')
            elif analysis.get('title'):
                caption = analysis.get('title')
        
        metadata = {
            'file_id': file_id,
            'content_type': content_type,
            'title': analysis.get('title'),
            'content': analysis.get('content'),  # 文本和链接需要content字段
            'caption': caption,
            'file_size': file_size
        }
        
        # 如果确定了特定频道，添加override_channel_id参数
        if target_channel_id:
            metadata['override_channel_id'] = target_channel_id
            logger.info(f"Using specific channel {target_channel_id} for this storage")
        
        logger.info(f"Forwarding {content_type} to Telegram channel: file_id={file_id[:20] if file_id else 'text/link'}..., size={format_file_size(file_size) if file_size else 'N/A'}")
        
        try:
            # 查询笔记和精选状态（用于按钮）
            has_notes = False
            is_favorite = False
            if archive_id:
                # 查询笔记数量
                result = self.db_storage.db.execute(
                    "SELECT COUNT(*) as count FROM notes WHERE archive_id = ?",
                    (archive_id,)
                ).fetchone()
                has_notes = result['count'] > 0 if result else False
                
                # 查询精选状态
                fav_result = self.db_storage.db.execute(
                    "SELECT favorite FROM archives WHERE id = ?",
                    (archive_id,)
                ).fetchone()
                is_favorite = fav_result['favorite'] == 1 if fav_result else False
            
            # 将archive_id、has_notes和is_favorite添加到metadata
            if archive_id:
                metadata['archive_id'] = archive_id
                metadata['has_notes'] = has_notes
                metadata['is_favorite'] = is_favorite
            
            storage_path = await self.telegram_storage.store(None, metadata)
            if storage_path:
                logger.info(f"Successfully stored to Telegram: {storage_path}")
            else:
                logger.error(f"Telegram storage returned None for {content_type}")
            return storage_path
        except Exception as e:
            logger.error(f"Exception during Telegram storage: {e}", exc_info=True)
            return None
    
    def _determine_storage_type(self, content_type: str, file_size: Optional[int]) -> str:
        """
        双存储策略优化：
        - 文本/链接 -> database + telegram频道（双存储，数据库为主，频道为辅助浏览）
        - 媒体文件 (<2GB) -> telegram频道 (file_id永久有效)
        - 超大文件 (>2GB) -> reference (仅存储元数据)
        
        Args:
            content_type: Content type
            file_size: File size in bytes
            
        Returns:
            Storage type (返回STORAGE_TELEGRAM表示需要存储到频道)
        """
        # 文本和链接：同时存数据库+频道（但标记为STORAGE_TELEGRAM让其发送到频道）
        # 数据库存储在archive_content中会自动进行
        if content_type in ['text', 'link']:
            if self.telegram_storage and self.telegram_storage.is_available():
                logger.debug(f"{content_type} -> database + telegram (dual storage)")
                return STORAGE_TELEGRAM  # 返回TELEGRAM表示需要发送到频道
            else:
                logger.debug(f"{content_type} -> database only (telegram unavailable)")
                return STORAGE_DATABASE
        
        # contact和location仍然只存数据库
        if content_type in ['contact', 'location']:
            return STORAGE_DATABASE
        
        # 无文件大小信息，存为引用
        if file_size is None:
            logger.warning(f"{content_type} -> reference (no file size)")
            return STORAGE_REFERENCE
        
        # Telegram频道支持2GB内的所有文件
        if file_size < TELEGRAM_MAX_SIZE:
            if self.telegram_storage and self.telegram_storage.is_available():
                logger.debug(f"{content_type} ({format_file_size(file_size)}) -> telegram")
                return STORAGE_TELEGRAM
            else:
                logger.warning(f"Telegram不可用，降级为引用")
                return STORAGE_REFERENCE
        
        # 超过2GB，只能存引用
        logger.warning(f"{content_type} ({format_file_size(file_size)}) 超过2GB -> reference")
        return STORAGE_REFERENCE
    
    def search_archives(
        self,
        keyword: Optional[str] = None,
        content_type: Optional[str] = None,
        tag_names: Optional[list] = None,
        limit: int = 10
    ) -> list:
        """
        Search archives
        
        Args:
            keyword: Search keyword
            content_type: Filter by content type
            tag_names: Filter by tag names
            limit: Maximum results
            
        Returns:
            List of archive dictionaries
        """
        return self.db_storage.search_archives(
            keyword=keyword,
            content_type=content_type,
            tag_names=tag_names,
            limit=limit
        )
    
    def get_archive(self, archive_id: int) -> Optional[Dict[str, Any]]:
        """
        Get archive by ID
        
        Args:
            archive_id: Archive ID
            
        Returns:
            Archive dictionary or None
        """
        return self.db_storage.get_archive(archive_id)
    
    def delete_archive(self, archive_id: int) -> bool:
        """
        Delete archive
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if deleted, False otherwise
        """
        return self.db_storage.delete_archive(archive_id)
