"""
Rate limiter module
Prevents abuse and manages API rate limits
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter
    """
    
    def __init__(self, max_requests: int = 30, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[int, list] = defaultdict(list)
        logger.info(f"RateLimiter initialized: {max_requests} requests per {time_window}s")
    
    def is_allowed(self, user_id: int) -> Tuple[bool, float]:
        """
        Check if request is allowed for user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (allowed, wait_time)
            - allowed: True if request is allowed
            - wait_time: Seconds to wait if not allowed (0 if allowed)
        """
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside time window
        cutoff = now - self.time_window
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff]
        
        # Check if within limit
        if len(user_requests) < self.max_requests:
            user_requests.append(now)
            return True, 0.0
        
        # Calculate wait time
        oldest_request = min(user_requests)
        wait_time = oldest_request + self.time_window - now
        
        logger.warning(f"Rate limit exceeded for user {user_id}, wait {wait_time:.1f}s")
        return False, wait_time
    
    def reset(self, user_id: int):
        """
        Reset rate limit for user
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.requests:
            del self.requests[user_id]
            logger.info(f"Rate limit reset for user {user_id}")
    
    def get_remaining(self, user_id: int) -> int:
        """
        Get remaining requests for user in current window
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of remaining requests
        """
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests
        cutoff = now - self.time_window
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff]
        
        remaining = self.max_requests - len(user_requests)
        return max(0, remaining)


def rate_limit(limiter: RateLimiter):
    """
    Decorator to apply rate limiting to handlers
    
    Args:
        limiter: RateLimiter instance
        
    Returns:
        Decorated function
        
    Example:
        rate_limiter = RateLimiter(max_requests=10, time_window=60)
        
        @rate_limit(rate_limiter)
        async def my_handler(update: Update, context):
            # handler code
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            user_id = update.effective_user.id
            allowed, wait_time = limiter.is_allowed(user_id)
            
            if not allowed:
                # Send rate limit message
                from ..utils.i18n import get_i18n
                i18n = get_i18n()
                await update.effective_message.reply_text(
                    i18n.t('rate_limit_exceeded', wait_time=int(wait_time))
                )
                return
            
            # Execute handler
            return await func(update, context)
        
        return wrapper
    return decorator


# Global rate limiter instance (can be configured in main.py)
_global_limiter = None


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance
    
    Returns:
        RateLimiter instance
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
    return _global_limiter


def set_rate_limiter(limiter: RateLimiter):
    """
    Set global rate limiter instance
    
    Args:
        limiter: RateLimiter instance
    """
    global _global_limiter
    _global_limiter = limiter
