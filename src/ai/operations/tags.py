"""
Tag generation operations
"""
import logging
import time
import asyncio
from typing import List

logger = logging.getLogger(__name__)


async def generate_tags_operation(
    provider,
    content: str,
    max_tags: int = 5,
    language: str = 'zh-CN',
    cache=None,
    retry_on_failure: int = 1,
    log_calls: bool = False
) -> List[str]:
    """生成标签"""
    if not provider or not hasattr(provider, 'generate_tags'):
        return []
    
    # 缓存优先
    cached = None
    if cache:
        try:
            from ..providers.utils import content_hash
            key_src = f"tags|{getattr(provider, 'model', '')}|{max_tags}|{content}"
            cache_key = content_hash(key_src)
            cached = cache.get(cache_key)
            if cached:
                return cached
        except Exception as e:
            logger.debug(f"AI tag cache lookup error: {e}")
    
    # 重试逻辑
    last_error = None
    for attempt in range(retry_on_failure + 1):
        try:
            if log_calls and attempt > 0:
                logger.info(f"AI generate_tags retry attempt {attempt}/{retry_on_failure}")
            
            start = time.time()
            tags = await provider.generate_tags(content, max_tags, language=language)
            duration = time.time() - start
            
            if log_calls:
                logger.info(f"AI generate_tags success: duration={duration:.2f}s, tags={tags}, content_len={len(content)}")
            
            # 写回缓存
            if cache:
                try:
                    from ..providers.utils import content_hash
                    key_src = f"tags|{getattr(provider, 'model', '')}|{max_tags}|{content}"
                    cache_key = content_hash(key_src)
                    cache.set(cache_key, tags)
                except Exception as e:
                    logger.debug(f"AI tag cache write error: {e}")
            
            return tags
            
        except Exception as e:
            last_error = e
            if log_calls:
                logger.warning(f"AI generate_tags attempt {attempt + 1} failed: {e}")
            if attempt < retry_on_failure:
                await asyncio.sleep(1)
            continue
    
    # 所有重试失败
    if log_calls:
        logger.error(f"AI generate_tags failed after {retry_on_failure + 1} attempts: {last_error}")
    return []


async def batch_generate_tags_operation(
    provider,
    contents: list,
    max_tags: int = 5,
    language: str = 'zh-CN',
    cache=None,
    retry_on_failure: int = 1,
    log_calls: bool = False
) -> list:
    """批量生成标签（并发处理）"""
    if not provider:
        return [[] for _ in contents]
    
    start = time.time()
    tasks = [
        generate_tags_operation(provider, content, max_tags, language, cache, retry_on_failure, log_calls)
        for content in contents
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start
    
    if log_calls:
        logger.info(f"Batch tags generated: duration={duration:.2f}s, count={len(contents)}")
    
    return results
