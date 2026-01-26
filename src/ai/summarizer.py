"""
AI Summarizer - Main Class
云端API服务
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional

from .providers import AIProvider, OpenAIProvider, detect_content_language, is_formal_content
from .prompts import PromptManager
from ..core.ai_cache import AICache, content_hash
from .operations import (
    summarize_operation,
    generate_tags_operation,
    batch_generate_tags_operation,
    generate_note_from_content_operation,
    generate_note_from_ai_analysis_operation,
    generate_title_from_text_operation,
    is_ebook_operation,
)

logger = logging.getLogger(__name__)

class AISummarizer:
    def __init__(self, config):
        self.config, self.provider = config, None
        self.cache = None
        self._last_call_info = {}
        if not config.get('enabled'):
            return

        # 只使用云端API
        api = config.get('api', {})
        
        # 从全局 Config 获取配置（支持环境变量优先）
        from ..utils.config import get_config
        global_config = get_config()
        
        # 优先从环境变量读取（通过 global_config.get），然后从传入的 config 读取
        api_key = global_config.get('ai.api.api_key') or api.get('api_key')
        if not api_key:
            logger.warning("AI enabled but no API key provided in config.api")
            # 继续允许 provider 初始化失败后的 graceful behavior
        
        provider_type = (global_config.get('ai.api.provider') or api.get('provider', 'openai')).lower()
        
        if provider_type in ['openai', 'grok']:
            try:
                model = global_config.get('ai.api.model') or api.get('model', 'gpt-3.5-turbo')
                api_url = global_config.get('ai.api.api_url') or api.get('api_url')
                temperature = api.get('temperature', 0.7)
                
                self.provider = OpenAIProvider(
                    api_key,
                    model,
                    api_url,
                    temperature
                )
                logger.info(f"Using {provider_type.upper()} API: {model}")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_type} provider: {e}")

        # 初始化缓存（如果启用）
        try:
            cache_enabled = bool(config.get('cache_enabled', False))
            cache_path = config.get('cache_path') or api.get('cache_path') or 'data/ai_cache.db'
            cache_ttl = int(config.get('cache_ttl_seconds', 604800))
            if cache_enabled:
                try:
                    self.cache = AICache(db_path=cache_path, ttl=cache_ttl)
                    logger.info(f"AI cache enabled at {cache_path}, ttl={cache_ttl}s")
                except Exception as e:
                    logger.warning(f"Failed to initialize AI cache: {e}")
        except Exception:
            pass
        # 速率限制配置（calls per minute）
        try:
            self.rate_limit = int(config.get('rate_limit_per_minute', 0) or 0)
        except Exception:
            self.rate_limit = 0
        self._rate_count = 0
        self._rate_window_start = int(time.time())
        
        # 日志和重试配置
        try:
            self.log_calls = bool(config.get('log_calls', False))
            self.retry_on_failure = int(config.get('retry_on_failure', 1))
            self.retry_on_failure = max(0, min(3, self.retry_on_failure))  # 限制在0-3次
            if self.log_calls:
                logger.info(f"AI call logging enabled, retry_on_failure={self.retry_on_failure}")
        except Exception:
            self.log_calls = False
            self.retry_on_failure = 1

    def _allow_call(self) -> bool:
        """简单的每分钟速率限制（非分布式）"""
        if not self.rate_limit or self.rate_limit <= 0:
            return True
        now = int(time.time())
        # window start per minute
        if now - self._rate_window_start >= 60:
            self._rate_window_start = now
            self._rate_count = 0
        if self._rate_count < self.rate_limit:
            self._rate_count += 1
            return True
        return False
    
    def is_available(self):
        """Check if AI provider is available"""
        return self.provider is not None and hasattr(self.provider, 'available') and self.provider.available
    
    async def summarize_content(self, content, url=None, language='zh-CN', context: Optional[Dict[str, Any]] = None):
        """总结内容（使用operations模块）"""
        if not self.is_available():
            return {'success': False, 'error': 'AI不可用'}
        
        # 速率检测
        if not self._allow_call():
            logger.warning("AI rate limit reached")
            return {'success': False, 'error': 'AI rate limit exceeded'}
        
        # 调用operations模块
        result = await summarize_operation(
            self.provider,
            content,
            url=url,
            language=language,
            context=context,
            cache=self.cache,
            retry_on_failure=self.retry_on_failure,
            log_calls=self.log_calls
        )
        
        # 记录调用信息
        if result.get('success'):
            self._last_call_info = {'provider': result.get('provider', 'UNKNOWN'), 'duration': 0}
        else:
            self._last_call_info = {'provider': 'ERROR', 'duration': 0}
        
        return result
    
    async def generate_tags(self, content, max_tags=5, language='zh-CN'):
        """生成标签（使用operations模块）"""
        if not self.is_available():
            return []
        
        # 速率检测
        if not self._allow_call():
            logger.warning("AI rate limit reached")
            self._last_call_info = {'provider': 'RATE_LIMIT', 'duration': 0}
            return []
        
        # 调用operations模块
        tags = await generate_tags_operation(
            self.provider,
            content,
            max_tags=max_tags,
            language=language,
            cache=self.cache,
            retry_on_failure=self.retry_on_failure,
            log_calls=self.log_calls
        )
        
        # 记录调用信息
        self._last_call_info = {'provider': 'CLOUD' if tags else 'ERROR', 'duration': 0}
        return tags
    
    async def batch_generate_tags(self, contents: list, max_tags: int = 5, language: str = 'zh-CN'):
        """批量生成标签（使用operations模块）"""
        if not self.is_available():
            return [[] for _ in contents]
        
        start = time.time()
        results = await batch_generate_tags_operation(
            self.provider,
            contents,
            max_tags=max_tags,
            language=language,
            cache=self.cache,
            retry_on_failure=self.retry_on_failure,
            log_calls=self.log_calls
        )
        self._last_call_info = {'provider': 'BATCH', 'duration': time.time() - start}
        return results
    
    async def is_ebook(self, file_name: str, language: str = 'zh-CN') -> bool:
        """判断是否为电子书（使用operations模块）"""
        """
        判断文件是否为电子书（书籍、杂志、报刊、画报等）
        
        Args:
            file_name: 文件名
            language: 用户界面语言
            
        Returns:
            True表示是电子书，False表示不是
        """
        if not self.is_available():
            return False
        
        try:
            # 根据语言构建prompt
            if language.startswith('zh'):
                if language in ['zh-TW', 'zh-HK', 'zh-MO']:
                    prompt = "請判斷以下檔案名稱是否為電子書\n"
                    prompt += "包括書籍雜誌期刊畫報漫畫等\n"
                    prompt += "只需回答是或否\n\n"
                    prompt += f"檔案名稱{file_name}\n\n這是電子書嗎"
                else:
                    prompt = "请判断以下文件名是否为电子书\n"
                    prompt += "包括书籍杂志期刊画报漫画等\n"
                    prompt += "只需回答是或否\n\n"
                    prompt += f"文件名{file_name}\n\n这是电子书吗"
            else:
                prompt = "Please determine if the following file name is an eBook\n"
                prompt += "including books magazines journals pictorials comics etc\n"
                prompt += "Just answer Yes or No\n\n"
                prompt += f"File name {file_name}\n\nIs this an eBook"
            
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10,
                    "temperature": self.provider.temperature
                }
            )
            
            response = r.json()['choices'][0]['message']['content'].strip().lower()
            
            # 判断回答
            positive_answers = ['yes', '是', 'true', 'y']
            return any(ans in response for ans in positive_answers)
            
        except Exception as e:
            logger.error(f"AI判断电子书失败: {e}")
            return False
    
    async def generate_tags_batch(self, contents: list, max_tags: int = 5) -> list:
        """批量生成标签（兼容方法，调用batch_generate_tags）"""
        return await self.batch_generate_tags(contents, max_tags)
    
    async def generate_note_from_content(
        self,
        content: str,
        content_type: str,
        max_length: int = 250,
        language: str = 'zh-CN'
    ) -> str:
        """生成笔记（使用operations模块）"""
        if not self.is_available():
            return ""
        
        return await generate_note_from_content_operation(
            self.provider,
            content,
            content_type,
            max_length,
            language
        )
    
    async def generate_note_from_ai_analysis(
        self,
        ai_summary: str,
        ai_key_points: List[str],
        ai_category: str,
        title: str,
        language: str = 'zh-CN'
    ) -> str:
        """生成AI分析笔记（使用operations模块）"""
        if not self.is_available():
            return ""
        
        return await generate_note_from_ai_analysis_operation(
            self.provider,
            ai_summary,
            ai_key_points,
            ai_category,
            title,
            language
        )
    
    async def generate_title_from_text(self, content: str, max_length: int = 32, language: str = 'zh-CN') -> str:
        """生成标题（使用operations模块）"""
        if not content or not content.strip():
            return "无标题"
        
        if not self.is_available():
            # 降级处理
            fallback = content[:max_length].strip()
            if len(content) > max_length:
                fallback = fallback[:max_length-3] + "..."
            return fallback
        
        return await generate_title_from_text_operation(
            self.provider,
            content,
            max_length,
            language
        )

_summarizer = None


def get_ai_summarizer(config=None):
    global _summarizer
    if not _summarizer and config: _summarizer = AISummarizer(config)
    return _summarizer

async def summarize_link(url, content, config):
    summarizer = get_ai_summarizer(config)
    return await summarizer.summarize_content(content, url)
