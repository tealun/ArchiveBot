"""
AI API Request Queue - 管理并发请求，防止速率限制

特点:
1. FIFO 队列 - 按顺序处理请求
2. 自适应延迟 - 根据 rate_limit 自动计算最小延迟
3. 指数退避 - 触发速率限制时自动退避
4. 请求优先级 - 标签生成 > 标题生成 > 摘要生成
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """请求优先级"""
    TAGS = 1      # 标签生成 - 最快，应该优先
    TITLE = 2     # 标题生成 - 中等
    SUMMARY = 3   # 摘要生成 - 最慢，可以延后


@dataclass
class QueuedRequest:
    """队列中的请求"""
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: RequestPriority = RequestPriority.SUMMARY
    created_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 2
    result_future: asyncio.Future = field(default=None)  # 存储结果的 Future


class AIRequestQueue:
    """AI 请求队列管理器"""
    
    def __init__(self, rate_limit_per_minute: int = 5, max_queue_size: int = 50):
        """
        初始化队列
        
        Args:
            rate_limit_per_minute: 每分钟最大请求数
            max_queue_size: 最大队列长度（防止内存溢出）
        """
        self.rate_limit = max(1, rate_limit_per_minute)  # 最低1个/分钟
        self.min_interval = 60.0 / self.rate_limit  # 请求间隔（秒）
        self.max_queue_size = max_queue_size
        
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.last_request_time = time.time() - self.min_interval  # 允许第一个请求立即执行
        self.is_running = False
        self.worker_task = None
        
        # 统计信息
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_retries = 0
        
        # 动态退避
        self.backoff_multiplier = 1.0  # 当前延迟倍数
        self.max_backoff_multiplier = 5.0
        self.backoff_reset_time = time.time()
        
    def start(self):
        """启动队列处理"""
        if not self.is_running:
            self.is_running = True
            self.worker_task = asyncio.create_task(self._process_queue())
            logger.info(f"AI Request Queue started: {self.rate_limit} requests/min, "
                       f"interval={self.min_interval:.2f}s")
    
    async def stop(self):
        """停止队列处理"""
        self.is_running = False
        if self.worker_task:
            await self.worker_task
        logger.info(f"AI Request Queue stopped. Stats: "
                   f"total={self.total_requests}, "
                   f"success={self.successful_requests}, "
                   f"failed={self.failed_requests}, "
                   f"rate_limited_retries={self.rate_limited_retries}")
    
    async def submit(self, 
                     func: Callable,
                     *args,
                     priority: RequestPriority = RequestPriority.SUMMARY,
                     max_retries: int = 2,
                     **kwargs) -> Optional[Any]:
        """
        提交请求到队列
        
        Args:
            func: 异步函数
            args: 位置参数
            priority: 请求优先级
            max_retries: 最大重试次数
            kwargs: 关键字参数
            
        Returns:
            等待执行结果的 Future，可以直接 await
        """
        if self.queue.qsize() >= self.max_queue_size:
            logger.warning(f"AI Request Queue full ({self.max_queue_size}), dropping request")
            return None
        
        # 创建 Future 来存储结果
        result_future = asyncio.Future()
        
        request = QueuedRequest(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            result_future=result_future
        )
        
        # 使用优先级和创建时间作为排序键
        # 优先级数字越小越优先（TAGS=1 > TITLE=2 > SUMMARY=3）
        sort_key = (priority.value, request.created_at.timestamp())
        await self.queue.put((sort_key, request))
        
        self.total_requests += 1
        
        # 返回 Future，调用者可以直接 await 这个 Future
        return await result_future
    
    async def _process_queue(self):
        """处理队列中的请求"""
        while self.is_running:
            try:
                # 计算需要等待的时间
                now = time.time()
                time_since_last = now - self.last_request_time
                wait_time = max(0, self.min_interval * self.backoff_multiplier - time_since_last)
                
                try:
                    # 带超时的队列获取
                    _, request = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # 队列空，定期检查并逐步降低退避倍数
                    if time.time() - self.backoff_reset_time > 60:  # 每分钟检查一次
                        old_multiplier = self.backoff_multiplier
                        self.backoff_multiplier = max(1.0, self.backoff_multiplier * 0.8)
                        if old_multiplier != self.backoff_multiplier:
                            logger.debug(f"Reduced backoff multiplier: {old_multiplier:.2f} -> {self.backoff_multiplier:.2f}")
                        self.backoff_reset_time = time.time()
                    continue
                
                # 等待直到可以发送请求
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                # 执行请求
                result = await self._execute_request(request)
                self.last_request_time = time.time()
                
                # 设置 Future 的结果
                if not request.result_future.done():
                    request.result_future.set_result(result)
                
                # 成功 - 降低退避倍数
                if result is not None:
                    self.successful_requests += 1
                    if self.backoff_multiplier > 1.0:
                        self.backoff_multiplier = max(1.0, self.backoff_multiplier * 0.95)
                else:
                    self.failed_requests += 1
                    
            except Exception as e:
                logger.error(f"Error in AI request queue: {e}", exc_info=True)
                # 确保 Future 被设置（即使出错）
                try:
                    if 'request' in locals() and hasattr(request, 'result_future') and not request.result_future.done():
                        request.result_future.set_result(None)
                except:
                    pass
                await asyncio.sleep(1)
    
    async def _execute_request(self, request: QueuedRequest) -> Optional[Any]:
        """执行单个请求（带重试逻辑）"""
        while request.retry_count <= request.max_retries:
            try:
                result = await request.func(*request.args, **request.kwargs)
                
                # 检查是否是速率限制错误
                if isinstance(result, dict) and not result.get('success'):
                    error = result.get('error', '')
                    if 'rate limit' in error.lower():
                        request.retry_count += 1
                        self.rate_limited_retries += 1
                        
                        # 增加退避倍数
                        old_multiplier = self.backoff_multiplier
                        self.backoff_multiplier = min(
                            self.max_backoff_multiplier,
                            self.backoff_multiplier * 1.5
                        )
                        logger.warning(
                            f"Rate limited (retry {request.retry_count}/{request.max_retries}), "
                            f"backoff: {old_multiplier:.2f} -> {self.backoff_multiplier:.2f}"
                        )
                        
                        # 指数退避等待
                        wait_time = (2 ** request.retry_count) * self.min_interval
                        await asyncio.sleep(wait_time)
                        continue
                
                return result
                
            except Exception as e:
                request.retry_count += 1
                logger.error(f"Request execution error (retry {request.retry_count}): {e}")
                
                if request.retry_count <= request.max_retries:
                    wait_time = (2 ** request.retry_count) * self.min_interval
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return None
        
        return None
    
    def get_stats(self) -> dict:
        """获取队列统计信息"""
        return {
            'queue_size': self.queue.qsize(),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'rate_limited_retries': self.rate_limited_retries,
            'current_backoff_multiplier': self.backoff_multiplier,
            'min_interval': self.min_interval,
            'is_running': self.is_running,
        }
