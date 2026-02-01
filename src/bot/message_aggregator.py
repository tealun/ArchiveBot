"""
Message aggregator module
Handles batch message detection and aggregation
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from telegram import Message, Update
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageBatch:
    """Represents a batch of related messages"""
    
    def __init__(self, media_group_id: Optional[str] = None):
        self.messages: List[Message] = []
        self.captions: List[Message] = []  # 附带的文本消息
        self.media_group_id = media_group_id
        self.first_time: Optional[datetime] = None
        self.last_time: Optional[datetime] = None
        
        # 来源信息（从batch中的第一条媒体消息提取）
        self.source_info: Optional[Dict] = None
        self.is_forwarded: bool = False
        
    def add_message(self, message: Message):
        """Add message to batch"""
        if self.first_time is None:
            self.first_time = message.date
        self.last_time = message.date
        
        # 区分媒体消息和纯文本消息
        if self._is_media_message(message):
            self.messages.append(message)
            
            # 从第一条媒体消息提取来源信息
            if self.source_info is None:
                self.source_info = self._extract_source_info(message)
                self.is_forwarded = bool(message.forward_origin)
                if self.source_info:
                    logger.debug(f"Batch source detected: {self.source_info.get('name')} (forwarded={self.is_forwarded})")
                
                # 如果是转发消息，检查是否有等待期的文本消息（用户评论）
                if self.is_forwarded:
                    from .handlers.forward_detector import get_forward_detector
                    detector = get_forward_detector()
                    user_id = str(message.from_user.id)
                    wait_check = detector.check_forwarded_arrived(user_id)
                    if wait_check:
                        # 检测到有等待中的文本消息，这是用户评论
                        user_comment = wait_check.get('user_comment', '')
                        logger.info(f"Detected user comment during forward: '{user_comment[:50]}...'")
                        # 将用户评论添加到caption中
                        # 创建一个虚拟的文本消息对象或直接添加到captions
                        # 这里我们通过在batch中存储user_comment字段
                        if not hasattr(self, 'user_comment'):
                            self.user_comment = user_comment
        elif message.text:
            # 检查是否是标签或笔记
            self.captions.append(message)
    
    @staticmethod
    def _extract_source_info(message: Message) -> Optional[Dict]:
        """从消息中提取来源信息"""
        if not message.forward_origin:
            return None
            
        from telegram import MessageOriginChannel, MessageOriginUser, MessageOriginChat
        
        if isinstance(message.forward_origin, MessageOriginChannel):
            # 来自频道的转发
            return {
                'name': message.forward_origin.chat.title,
                'id': message.forward_origin.chat.id,
                'type': message.forward_origin.chat.type
            }
        elif isinstance(message.forward_origin, MessageOriginChat):
            # 来自群组的转发
            return {
                'name': message.forward_origin.sender_chat.title,
                'id': message.forward_origin.sender_chat.id,
                'type': message.forward_origin.sender_chat.type
            }
        elif isinstance(message.forward_origin, MessageOriginUser):
            # 来自用户的转发
            user = message.forward_origin.sender_user
            return {
                'name': user.username or user.first_name,
                'id': user.id,
                'type': 'private'
            }
        return None
    
    @staticmethod
    def _is_media_message(message: Message) -> bool:
        """判断是否为媒体消息"""
        return any([
            message.photo, message.video, message.document,
            message.audio, message.voice, message.animation,
            message.sticker, message.contact, message.location
        ])
    
    def is_complete(self, window_ms: int = 200) -> bool:
        """判断批次是否完成（超过时间窗口）"""
        if not self.last_time:
            return False
        
        now = datetime.now(tz=self.last_time.tzinfo)
        elapsed = (now - self.last_time).total_seconds() * 1000
        return elapsed > window_ms
    
    def size(self) -> int:
        """批次中的媒体消息数量"""
        return len(self.messages)
    
    def has_captions(self) -> bool:
        """是否有附带的caption"""
        return len(self.captions) > 0
    
    def get_merged_caption(self) -> Optional[str]:
        """
        合并所有caption文本，包括：
        1. 用户发送的文本消息（评论）
        2. 媒体消息自带的caption
        3. 等待期检测到的用户评论（如果有）
        """
        all_texts = []
        
        # 0. 优先添加等待期检测到的用户评论
        if hasattr(self, 'user_comment') and self.user_comment:
            all_texts.append(self.user_comment)
        
        # 1. 用户自己发送的文本消息（评论）
        for msg in self.captions:
            if msg.text:
                all_texts.append(msg.text)
        
        # 2. 媒体消息自带的caption
        for msg in self.messages:
            if msg.caption:
                all_texts.append(msg.caption)
        
        return "\n".join(all_texts) if all_texts else None
    
    def get_user_comments_and_captions(self) -> Tuple[Optional[str], Optional[str]]:
        """
        区分用户评论和原始caption
        
        Returns:
            (user_comments, original_captions)
            - user_comments: 用户自己发送的文本消息（非转发） + 等待期检测到的评论
            - original_captions: 媒体消息自带的caption字段
        """
        user_comments = []
        original_captions = []
        
        # 0. 优先添加等待期检测到的用户评论
        if hasattr(self, 'user_comment') and self.user_comment:
            user_comments.append(self.user_comment)
        
        # 1. 提取用户自己发送的文本消息（评论）
        for msg in self.captions:
            if msg.text and not msg.forward_origin:
                user_comments.append(msg.text)
        
        # 2. 提取媒体消息自带的caption
        for msg in self.messages:
            if msg.caption:
                original_captions.append(msg.caption)
        
        user_comment_str = "\n".join(user_comments) if user_comments else None
        original_caption_str = "\n".join(original_captions) if original_captions else None
        
        return user_comment_str, original_caption_str


class MessageAggregator:
    """
    Message aggregator for batch processing
    聚合批量转发的消息，提升处理效率
    """
    
    def __init__(self, batch_window_ms: int = 200, max_batch_size: int = 100):
        """
        Initialize message aggregator
        
        Args:
            batch_window_ms: Time window for batch detection (milliseconds)
            max_batch_size: Maximum batch size
        """
        self.batch_window_ms = batch_window_ms
        self.max_batch_size = max_batch_size
        
        # 批次缓存
        self._batches: Dict[str, MessageBatch] = {}  # chat_id -> MessageBatch
        self._media_groups: Dict[str, MessageBatch] = {}  # media_group_id -> MessageBatch
        
        # 处理锁（限制数量避免内存泄漏）
        self._locks: Dict[str, asyncio.Lock] = {}
        self._max_locks = 100  # 最多保留100个锁
        
        # 定时器
        self._timers: Dict[str, asyncio.Task] = {}
        
        # 清理计数器（每处理100个批次清理一次）
        self._processed_count = 0
        
        logger.info(f"MessageAggregator initialized: window={batch_window_ms}ms, max_batch={max_batch_size}, max_locks={self._max_locks}")
    
    async def process_message(
        self,
        message: Message,
        handler_callback
    ) -> Optional[List]:
        """
        Process incoming message with batch detection
        
        Args:
            message: Telegram message
            handler_callback: Async callback function for processing
            
        Returns:
            Processing results or None if batched
        """
        chat_id = str(message.chat_id)
        media_group_id = message.media_group_id
        
        # 获取或创建锁（限制数量）
        if chat_id not in self._locks:
            if len(self._locks) >= self._max_locks:
                # 清理最旧的锁（简单策略：清理第一个）
                oldest_key = next(iter(self._locks))
                self._locks.pop(oldest_key, None)
                logger.debug(f"Lock cache full, removed oldest: {oldest_key}")
            self._locks[chat_id] = asyncio.Lock()
        
        async with self._locks[chat_id]:
            # 处理media_group（Telegram原生批量）
            if media_group_id:
                return await self._handle_media_group(message, media_group_id, handler_callback)
            
            # 处理普通消息（可能是批量转发）
            return await self._handle_regular_message(message, chat_id, handler_callback)
    
    async def _handle_media_group(
        self,
        message: Message,
        media_group_id: str,
        handler_callback
    ) -> Optional[List]:
        """Handle media group messages"""
        
        # 获取或创建media_group批次
        if media_group_id not in self._media_groups:
            self._media_groups[media_group_id] = MessageBatch(media_group_id)
            logger.debug(f"Created media_group batch: {media_group_id}")
        
        batch = self._media_groups[media_group_id]
        batch.add_message(message)
        
        # 启动或重置定时器
        await self._schedule_batch_processing(
            media_group_id,
            batch,
            handler_callback,
            is_media_group=True
        )
        
        return None  # 暂不处理，等待批次完成
    
    async def _handle_regular_message(
        self,
        message: Message,
        chat_id: str,
        handler_callback
    ) -> Optional[List]:
        """Handle regular messages (potential batch forwards)"""
        
        # 检查是否有活跃批次
        if chat_id in self._batches:
            batch = self._batches[chat_id]
            
            # 判断是否属于同一批次（时间窗口内）
            if batch.last_time:
                time_diff = (message.date - batch.last_time).total_seconds() * 1000
                
                if time_diff <= self.batch_window_ms and batch.size() < self.max_batch_size:
                    # 加入当前批次
                    batch.add_message(message)
                    logger.debug(f"Added to existing batch: {chat_id}, size={batch.size()}")
                    
                    # 重置定时器
                    await self._schedule_batch_processing(chat_id, batch, handler_callback)
                    return None
        
        # 判断是否是媒体消息（可能开启新批次）
        if MessageBatch._is_media_message(message):
            # 创建新批次
            batch = MessageBatch()
            batch.add_message(message)
            self._batches[chat_id] = batch
            
            logger.debug(f"Started new batch: {chat_id}")
            
            # 启动定时器
            await self._schedule_batch_processing(chat_id, batch, handler_callback)
            return None
        
        # 纯文本消息
        # 检查是否应该作为caption添加到活跃批次
        if chat_id in self._batches and message.text:
            batch = self._batches[chat_id]
            if batch.last_time:
                time_diff = (message.date - batch.last_time).total_seconds() * 1000
                if time_diff <= self.batch_window_ms:
                    # 作为caption加入批次
                    batch.add_message(message)
                    logger.debug(f"Added caption to batch: {chat_id}")
                    
                    # 重置定时器
                    await self._schedule_batch_processing(chat_id, batch, handler_callback)
                    return None
        
        # 单独处理（不属于任何批次）
        logger.debug(f"Processing single message: {chat_id}")
        # 提取单个消息的来源信息
        source_info = MessageBatch._extract_source_info(message)
        is_forwarded = bool(message.forward_origin)
        return await handler_callback([message], None, source_info, is_forwarded)
    
    async def _schedule_batch_processing(
        self,
        batch_id: str,
        batch: MessageBatch,
        handler_callback,
        is_media_group: bool = False
    ):
        """Schedule batch processing after timeout"""
        
        # 取消旧定时器
        if batch_id in self._timers:
            self._timers[batch_id].cancel()
        
        # 创建新定时器
        async def process_after_timeout():
            await asyncio.sleep(self.batch_window_ms / 1000)
            
            # 执行批量处理
            logger.info(f"Processing batch: {batch_id}, size={batch.size()}, captions={len(batch.captions)}, source={batch.source_info.get('name') if batch.source_info else 'direct'}, forwarded={batch.is_forwarded}")
            
            try:
                merged_caption = batch.get_merged_caption()
                # 传递来源信息和转发状态
                await handler_callback(batch.messages, merged_caption, batch.source_info, batch.is_forwarded)
            except Exception as e:
                logger.error(f"Error processing batch {batch_id}: {e}", exc_info=True)
            finally:
                # 清理批次
                if is_media_group:
                    self._media_groups.pop(batch_id, None)
                else:
                    self._batches.pop(batch_id, None)
                self._timers.pop(batch_id, None)
                
                # 定期清理锁（每处理100个批次）
                self._processed_count += 1
                if self._processed_count >= 100:
                    self._cleanup_inactive_locks()
                    self._processed_count = 0
        
        task = asyncio.create_task(process_after_timeout())
        self._timers[batch_id] = task
    
    def _cleanup_inactive_locks(self):
        """清理不活跃的锁（没有对应批次的）"""
        active_ids = set(self._batches.keys()) | set(self._media_groups.keys())
        inactive_locks = [k for k in self._locks.keys() if k not in active_ids]
        
        for lock_id in inactive_locks:
            self._locks.pop(lock_id, None)
        
        if inactive_locks:
            logger.debug(f"Cleaned {len(inactive_locks)} inactive locks, remaining: {len(self._locks)}")
    
    def get_stats(self) -> Dict:
        """Get aggregator statistics"""
        return {
            'active_batches': len(self._batches),
            'active_media_groups': len(self._media_groups),
            'active_timers': len(self._timers),
            'cached_locks': len(self._locks)
        }
