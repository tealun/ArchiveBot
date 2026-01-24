"""
Storage manager module
Manages content storage across different providers
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from ..storage.database import DatabaseStorage
from ..storage.telegram import TelegramStorage
from ..core.tag_manager import TagManager
from ..core.analyzer import ContentAnalyzer
from ..utils.helpers import format_datetime, format_file_size
from ..utils.i18n import get_i18n
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
    
    async def batch_archive_content(self, messages: list, analyses: list, progress_callback=None) -> list:
        """
        批量归档内容（优化：批量存储到Telegram频道）
        
        Args:
            messages: 消息列表
            analyses: 分析结果列表
            progress_callback: 进度回调函数 (current, total, stage)
            
        Returns:
            [(success, message), ...]
        """
        if len(messages) != len(analyses):
            logger.error(f"Messages and analyses count mismatch: {len(messages)} vs {len(analyses)}")
            return [(False, "Internal error") for _ in messages]
        
        results = []
        total = len(messages)
        
        # 收集需要存储到Telegram的文件
        telegram_indices = []
        telegram_metadata_list = []
        
        for i, (message, analysis) in enumerate(zip(messages, analyses)):
            content_type = analysis.get('content_type')
            storage_type = self._determine_storage_type(content_type, analysis.get('file_size'))
            
            if storage_type == STORAGE_TELEGRAM and self.telegram_storage:
                telegram_indices.append(i)
                metadata = {
                    'file_id': analysis.get('file_id'),
                    'content_type': content_type,
                    'caption': analysis.get('title') or analysis.get('content'),
                    'file_size': analysis.get('file_size', 0)
                }
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
                    results.append((False, self.i18n.t('archive_failed', error=analysis.get('error', 'Unknown'))))
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
                    ai_category=analysis.get('ai_category')
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
                
                # Success message (简化版)
                storage_name = self.i18n.t(f'storage_{storage_type}')
                tags_display = self.tag_manager.format_tags_for_display(all_tags)
                
                success_msg = f"✅ {self.i18n.t(f'tag_{content_type}')} | 🏷️ {tags_display}"
                results.append((True, success_msg))
                
                # 更新进度
                if progress_callback and (i + 1) % max(1, total // 20) == 0:
                    await progress_callback(i + 1, total, "存储到频道")
                
            except Exception as e:
                logger.error(f"Error in batch archive item {i}: {e}", exc_info=True)
                results.append((False, str(e)))
        
        logger.info(f"Batch archived {sum(1 for s, _ in results if s)}/{len(results)} items")
        return results
    
    async def archive_content(
        self,
        message: Message,
        analysis: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Archive content based on analysis
        
        Args:
            message: Telegram message object
            analysis: Content analysis result
            
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
            
            # Store file if needed
            storage_path = None
            storage_provider = None
            
            if storage_type == STORAGE_TELEGRAM and self.telegram_storage:
                # Store to Telegram channel
                try:
                    storage_path = await self._store_to_telegram(analysis)
                    if storage_path:
                        storage_provider = 'telegram_channel'
                        logger.info(f"File stored to Telegram: {storage_path}")
                    else:
                        # Fallback to reference only
                        storage_type = STORAGE_REFERENCE
                        logger.warning(f"Failed to store to Telegram, downgraded to reference: {content_type}")
                except Exception as e:
                    logger.error(f"Error storing to Telegram: {e}", exc_info=True)
                    storage_type = STORAGE_REFERENCE
                    logger.warning(f"Exception during Telegram storage, downgraded to reference: {content_type}")
            
            # Create archive entry
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
                ai_category=analysis.get('ai_category')
            )
            
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
            
            # Format success message
            storage_name = self.i18n.t(f'storage_{storage_type}')
            tags_display = self.tag_manager.format_tags_for_display(all_tags)
            source_display = analysis.get('source', '直接发送')
            
            # 构建标题链接（使用HTML格式）
            title = analysis.get('title', '')
            title_link = ''
            if title and storage_path and storage_provider == 'telegram_channel':
                # 获取频道ID
                from ..utils.config import get_config
                config = get_config()
                channel_id = config.telegram_channel_id
                if channel_id:
                    # 解析storage_path: 可能是 "message_id" 或 "channel_id:message_id" 或 "channel_id:message_id:file_id"
                    parts = storage_path.split(':')
                    if len(parts) >= 2:
                        # 格式: channel_id:message_id:file_id
                        channel_id_str = parts[0].replace('-100', '')
                        message_id = parts[1]
                    else:
                        # 格式: message_id（使用配置的channel_id）
                        channel_id_str = str(channel_id).replace('-100', '')
                        message_id = storage_path
                    
                    file_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                    # 使用HTML格式的链接
                    title_link = f"📚 标题: <a href='{file_link}'>{title}</a>\n"
                    logger.debug(f"Generated title link: {file_link} for content_type={content_type}")
            elif title:
                title_link = f"📚 标题: {title}\n"
                logger.debug(f"Generated plain title (no link) for content_type={content_type}, storage_provider={storage_provider}")
            
            # 对于非文本和非链接类型，显示文件大小
            file_size = analysis.get('file_size', 0)
            if content_type not in ['text', 'link'] and file_size > 0:
                success_msg = self.i18n.t(
                    'archive_success_with_size',
                    title_link=title_link,
                    content_type=self.i18n.t(f'tag_{content_type}'),
                    file_size=format_file_size(file_size),
                    tags=tags_display if tags_display else self.i18n.t('tag_text'),
                    storage_type=storage_name,
                    source=source_display,
                    time=format_datetime()
                )
            else:
                success_msg = self.i18n.t(
                    'archive_success',
                    title_link=title_link,
                    content_type=self.i18n.t(f'tag_{content_type}'),
                    tags=tags_display if tags_display else self.i18n.t('tag_text'),
                    storage_type=storage_name,
                    source=source_display,
                    time=format_datetime()
                )
            
            # 注意：此消息需要用 parse_mode='HTML' 发送
            
            # 添加AI分析信息（如果有）
            ai_summary = analysis.get('ai_summary', '')
            ai_key_points = analysis.get('ai_key_points', [])
            ai_category = analysis.get('ai_category', '')
            
            if ai_summary or ai_key_points or ai_category:
                success_msg += "\n\n🤖 AI智能分析："
                
                if ai_category:
                    success_msg += f"\n📁 分类：{ai_category}"
                
                if ai_summary:
                    success_msg += f"\n📝 摘要：{ai_summary}"
                
                if ai_key_points:
                    success_msg += "\n🔑 关键点："
                    for i, point in enumerate(ai_key_points[:3], 1):
                        success_msg += f"\n  {i}. {point}"
            
            logger.info(f"Successfully archived content: archive_id={archive_id}")
            return True, success_msg, archive_id
            
        except Exception as e:
            logger.error(f"Error archiving content: {e}", exc_info=True)
            return False, self.i18n.t('archive_failed', error=str(e)), None
    
    async def _store_to_telegram(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Store file to Telegram channel
        
        Args:
            analysis: Content analysis result
            
        Returns:
            Storage path or None
        """
        if not self.telegram_storage or not self.telegram_storage.is_available():
            logger.warning("Telegram storage not available")
            return None
        
        content_type = analysis.get('content_type')
        file_id = analysis.get('file_id')
        file_size = analysis.get('file_size', 0)
        
        # 检查必需字段
        if not file_id:
            logger.error(f"No file_id in analysis for {content_type}")
            return None
        
        # 构建metadata（统一使用file_id转发，简单可靠）
        metadata = {
            'file_id': file_id,
            'content_type': content_type,
            'caption': analysis.get('title') or analysis.get('content'),
            'file_size': file_size
        }
        
        logger.info(f"Forwarding {content_type} to Telegram channel: file_id={file_id[:20]}..., size={format_file_size(file_size) if file_size else 'unknown'}")
        
        try:
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
        简化的存储策略：
        - 文本/链接 -> database
        - 媒体文件 (<2GB) -> telegram频道 (file_id永久有效)
        - 超大文件 (>2GB) -> reference (仅存储元数据)
        
        Args:
            content_type: Content type
            file_size: File size in bytes
            
        Returns:
            Storage type
        """
        # 文本和链接存数据库
        if content_type in ['text', 'link', 'contact', 'location']:
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
