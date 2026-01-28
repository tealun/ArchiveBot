"""
Content summarization operations
"""
import logging
import time
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def summarize_operation(
    provider,
    content: str,
    url: Optional[str] = None,
    language: str = 'zh-CN',
    context: Optional[Dict[str, Any]] = None,
    cache=None,
    retry_on_failure: int = 1,
    log_calls: bool = False
) -> Dict[str, Any]:
    """
    总结内容
    
    Args:
        provider: AI provider实例
        content: 内容
        url: URL (可选)
        language: 语言
        context: 上下文信息
        cache: 缓存实例
        retry_on_failure: 重试次数
        log_calls: 是否记录日志
        
    Returns:
        总结结果字典
    """
    if not provider or not hasattr(provider, 'summarize'):
        return {'success': False, 'error': 'AI不可用'}
    
    # 尝试从缓存读取
    cached = None
    if cache:
        try:
            import json
            from ..providers.utils import content_hash
            ctx_ser = json.dumps(context or {}, sort_keys=True, ensure_ascii=False)
            key_src = f"{getattr(provider, 'model', '')}|{ctx_ser}|{content}"
            cache_key = content_hash(key_src)
            cached = cache.get(cache_key)
            if cached:
                cached['success'] = True
                cached['provider'] = 'CACHE'
                return cached
        except Exception as e:
            logger.debug(f"AI cache lookup error: {e}")
    
    # 重试逻辑
    last_error = None
    for attempt in range(retry_on_failure + 1):
        try:
            if log_calls and attempt > 0:
                logger.info(f"AI summarize retry attempt {attempt}/{retry_on_failure}")
            
            start = time.time()
            result = await provider.summarize(content, 1000, language=language, context=context)
            duration = time.time() - start
            result['success'] = True
            result['provider'] = 'CLOUD'
            
            if log_calls:
                logger.info(f"AI summarize success: duration={duration:.2f}s, content_len={len(content)}, language={language}")
            
            # 如果没有category，单独调用categorize
            default_category = '其他' if language.startswith('zh') else 'Other'
            if not result.get('category') or result.get('category') == default_category:
                result['category'] = await provider.categorize(content, language=language)
            
            # 写回缓存
            if cache:
                try:
                    import json
                    from ..providers.utils import content_hash
                    ctx_ser = json.dumps(context or {}, sort_keys=True, ensure_ascii=False)
                    key_src = f"{getattr(provider, 'model', '')}|{ctx_ser}|{content}"
                    cache_key = content_hash(key_src)
                    cache.set(cache_key, result)
                except Exception as e:
                    logger.debug(f"AI cache write error: {e}")
            
            return result
            
        except Exception as e:
            last_error = e
            if log_calls:
                logger.warning(f"AI summarize attempt {attempt + 1} failed: {e}")
            if attempt < retry_on_failure:
                await asyncio.sleep(1)
            continue
    
    # 所有重试失败 - 始终记录最终失败（不管log_calls设置）
    logger.error(f"AI summarize failed after {retry_on_failure + 1} attempts: {last_error}")
    return {'success': False, 'error': str(last_error)}
