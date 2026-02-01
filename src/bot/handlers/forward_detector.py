"""
Forward Message Detector
用于检测文本消息后是否有转发消息跟随，避免AI误判
"""

import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ForwardDetector:
    """
    检测文本消息后的转发消息（两阶段检测）
    
    阶段1（1000ms预等待）：快速过滤转发场景
    阶段2（5000ms深度等待）：AI/笔记处理中检测慢速转发
    """
    
    def __init__(self, stage1_wait_ms: int = 1000, stage2_wait_ms: int = 5000):
        """
        Args:
            stage1_wait_ms: 第一阶段等待期（毫秒），默认1000ms
            stage2_wait_ms: 第二阶段等待期（毫秒），默认5000ms
        """
        self.stage1_wait_ms = stage1_wait_ms
        self.stage2_wait_ms = stage2_wait_ms
        # 存储正在等待的用户消息: {user_id: {'text': str, 'timestamp': datetime, ...}}
        self._pending_texts: Dict[str, Dict] = {}
        logger.info(f"ForwardDetector initialized: stage1={stage1_wait_ms}ms, stage2={stage2_wait_ms}ms")
    
    async def register_text_message(self, user_id: str, text: str) -> Dict:
        """
        注册一个文本消息，进入第一阶段等待期
        
        Args:
            user_id: 用户ID
            text: 文本内容
            
        Returns:
            等待标记字典 {'waiting': True, 'text': str, 'timestamp': datetime, 'stage': 1}
        """
        # 如果已有等待中的消息，直接覆盖（用户可能快速发送多条消息）
        if user_id in self._pending_texts:
            logger.debug(f"Overwriting existing wait data for user {user_id}")
        
        # 注册新的等待消息
        wait_data = {
            'text': text,
            'timestamp': datetime.now(),
            'waiting': True,
            'forwarded_detected': False,
            'stage': 1  # 第一阶段
        }
        
        self._pending_texts[user_id] = wait_data
        logger.info(f"Registered text message for user {user_id}, entering stage 1 ({self.stage1_wait_ms}ms)")
        
        return wait_data
    
    def enter_stage2(self, user_id: str) -> None:
        """
        进入第二阶段等待期（AI/笔记处理开始）
        
        Args:
            user_id: 用户ID
        """
        wait_data = self._pending_texts.get(user_id)
        if wait_data:
            wait_data['stage'] = 2
            wait_data['stage2_start'] = datetime.now()
            logger.info(f"User {user_id} entered stage 2 ({self.stage2_wait_ms}ms deep wait)")
    
    def check_forwarded_arrived(self, user_id: str) -> Optional[Dict]:
        """
        检查用户是否有等待中的文本消息（用于转发消息到达时查询）
        
        Args:
            user_id: 用户ID
            
        Returns:
            如果有等待中的文本，返回 {'user_comment': str, 'timestamp': datetime}
            如果没有，返回 None
        """
        wait_data = self._pending_texts.get(user_id)
        if wait_data and wait_data.get('waiting'):
            logger.info(f"Forward message detected for user {user_id} during wait period, user comment: '{wait_data['text'][:50]}...'")
            # 标记为已检测到转发
            wait_data['forwarded_detected'] = True
            wait_data['waiting'] = False
            
            # 返回用户评论文本，但不立即清除（AI处理完成后会检查）
            return {
                'user_comment': wait_data['text'],
                'timestamp': wait_data['timestamp']
            }
        
        return None
    
    def is_in_wait_period(self, user_id: str) -> bool:
        """
        检查用户是否在等待期内（包括已检测到转发但AI未处理完的状态）
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否在等待期或已检测到转发
        """
        wait_data = self._pending_texts.get(user_id)
        # 如果存在wait_data（无论waiting状态），都认为需要检查
        return wait_data is not None
    
    def get_forward_status(self, user_id: str) -> Optional[Dict]:
        """
        获取转发检测状态（用于AI处理完成后检查）
        
        Args:
            user_id: 用户ID
            
        Returns:
            如果检测到转发，返回 {'forwarded_detected': True, 'user_comment': str}
            如果没有检测到，返回 None
        """
        wait_data = self._pending_texts.get(user_id)
        if wait_data and wait_data.get('forwarded_detected'):
            return {
                'forwarded_detected': True,
                'user_comment': wait_data.get('text', '')
            }
        return None
    
    def cancel_wait(self, user_id: str) -> None:
        """
        取消用户的等待期（用于AI处理完成后清理）
        
        Args:
            user_id: 用户ID
        """
        wait_data = self._pending_texts.pop(user_id, None)
        if wait_data:
            logger.debug(f"Cancelled wait period for user {user_id}")
    
    def is_within_stage2_window(self, user_id: str) -> bool:
        """
        检查是否在第二阶段时间窗口内
        
        Args:stage1_wait_ms': self.stage1_wait_ms,
            'stage2_wait_ms': self.stage2_wait
            user_id: 用户ID
            
        Returns:
            bool: 是否在第二阶段时间窗口内
        """
        wait_data = self._pending_texts.get(user_id)
        if not wait_data or wait_data.get('stage') != 2:
            return False
        
        stage2_start = wait_data.get('stage2_start')
        if not stage2_start:
            return False
        
        elapsed = (datetime.now() - stage2_start).total_seconds() * 1000
        return elapsed <= self.stage2_wait_ms
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'pending_count': len(self._pending_texts),
            'wait_period_ms': self.wait_period_ms
        }


# 全局单例
_forward_detector: Optional[ForwardDetector] = None


def get_forward_detector() -> ForwardDetector:
    """获取全局转发检测器"""
    global _forward_detector
    if _forward_detector is None:
        _forward_detector = ForwardDetector(stage1_wait_ms=1000, stage2_wait_ms=5000)
    return _forward_detector
