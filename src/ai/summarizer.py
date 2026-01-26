"""
AI Summarizer - Main Class
云端API服务
"""

import logging
import json
from typing import Dict, Any, List, Optional

from .providers import AIProvider, OpenAIProvider, detect_content_language, is_formal_content
from .prompts import PromptManager
from ..core.ai_cache import AICache, content_hash

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
        if not self.is_available():
            return {'success': False, 'error': 'AI不可用'}

        # 尝试从缓存读取（cache key 包含 model 与上下文以避免冲突）
        cached = None
        if self.cache:
            try:
                ctx_ser = json.dumps(context or {}, sort_keys=True, ensure_ascii=False)
                key_src = f"{getattr(self.provider, 'model', '')}|{ctx_ser}|{content}"
                cache_key = content_hash(key_src)
                cached = self.cache.get(cache_key)
                if cached:
                    cached['success'] = True
                    cached['provider'] = 'CACHE'
                    return cached
            except Exception as e:
                logger.debug(f"AI cache lookup error: {e}")

        # 速率检测：如超过限制，优先返回缓存或失败
        if not self._allow_call():
            logger.warning("AI rate limit reached, skipping external summarize call")
            if self.cache and cached:
                cached['success'] = True
                cached['provider'] = 'CACHE'
                return cached
            return {'success': False, 'error': 'AI rate limit exceeded'}

        # 重试逻辑
        last_error = None
        for attempt in range(self.retry_on_failure + 1):
            try:
                if self.log_calls and attempt > 0:
                    logger.info(f"AI summarize retry attempt {attempt}/{self.retry_on_failure}")
                
                start = time.time()
                result = await self.provider.summarize(content, 1000, language=language, context=context)
                duration = time.time() - start
                result['success'] = True
                result['provider'] = 'CLOUD'
                
                # 详细日志
                if self.log_calls:
                    logger.info(f"AI summarize success: duration={duration:.2f}s, content_len={len(content)}, language={language}")
                
                # 记录调用信息
                try:
                    self._last_call_info = {'provider': 'CLOUD', 'duration': duration}
                except Exception:
                    pass

                # 如果summarize没有返回category，单独调用categorize
                default_category = '其他' if language.startswith('zh') else 'Other'
                if not result.get('category') or result.get('category') == default_category:
                    result['category'] = await self.provider.categorize(content, language=language)

                # 写回缓存
                if self.cache:
                    try:
                        ctx_ser = json.dumps(context or {}, sort_keys=True, ensure_ascii=False)
                        key_src = f"{getattr(self.provider, 'model', '')}|{ctx_ser}|{content}"
                        cache_key = content_hash(key_src)
                        self.cache.set(cache_key, result)
                    except Exception as e:
                        logger.debug(f"AI cache write error: {e}")
                
                return result
                
            except Exception as e:
                last_error = e
                if self.log_calls:
                    logger.warning(f"AI summarize attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_on_failure:
                    await asyncio.sleep(1)  # 等待1秒后重试
                continue
        
        # 所有重试失败
        if self.log_calls:
            logger.error(f"AI summarize failed after {self.retry_on_failure + 1} attempts: {last_error}")
        try:
            self._last_call_info = {'provider': 'ERROR', 'duration': 0}
        except Exception:
            pass
        return {'success': False, 'error': str(last_error)}
    
    async def generate_tags(self, content, max_tags=5, language='zh-CN'):
        if not self.is_available(): return []
        
        # 缓存优先
        cached = None
        if self.cache:
            try:
                key_src = f"tags|{getattr(self.provider, 'model', '')}|{max_tags}|{content}"
                cache_key = content_hash(key_src)
                cached = self.cache.get(cache_key)
                if cached:
                    return cached
            except Exception as e:
                logger.debug(f"AI tag cache lookup error: {e}")

        # 速率检测：如超过限制，优先返回缓存或空列表
        if not self._allow_call():
            logger.warning("AI rate limit reached, skipping external generate_tags call")
            if self.cache and cached:
                try:
                    self._last_call_info = {'provider': 'CACHE', 'duration': 0}
                except Exception:
                    pass
                return cached
            try:
                self._last_call_info = {'provider': 'RATE_LIMIT', 'duration': 0}
            except Exception:
                pass
            return []

        # 重试逻辑
        last_error = None
        for attempt in range(self.retry_on_failure + 1):
            try:
                if self.log_calls and attempt > 0:
                    logger.info(f"AI generate_tags retry attempt {attempt}/{self.retry_on_failure}")
                
                start = time.time()
                tags = await self.provider.generate_tags(content, max_tags, language=language)
                duration = time.time() - start
                
                # 详细日志
                if self.log_calls:
                    logger.info(f"AI generate_tags success: duration={duration:.2f}s, tags={tags}, content_len={len(content)}")
                
                try:
                    self._last_call_info = {'provider': 'CLOUD', 'duration': duration}
                except Exception:
                    pass

                # 写回缓存
                if self.cache:
                    try:
                        key_src = f"tags|{getattr(self.provider, 'model', '')}|{max_tags}|{content}"
                        cache_key = content_hash(key_src)
                        self.cache.set(cache_key, tags)
                    except Exception as e:
                        logger.debug(f"AI tag cache write error: {e}")

                return tags
                
            except Exception as e:
                last_error = e
                if self.log_calls:
                    logger.warning(f"AI generate_tags attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_on_failure:
                    await asyncio.sleep(1)  # 等待1秒后重试
                continue
        
        # 所有重试失败
        if self.log_calls:
            logger.error(f"AI generate_tags failed after {self.retry_on_failure + 1} attempts: {last_error}")
        return []
    
    async def batch_generate_tags(self, contents: list, max_tags: int = 5, language: str = 'zh-CN'):
        """
        批量生成标签（并发处理）
        
        Args:
            contents: 内容列表
            max_tags: 每个内容的最大标签数
            language: 输出语言
        
        Returns:
            标签列表的列表
        """
        if not self.is_available():
            return [[] for _ in contents]
        
        start = time.time()
        tasks = [self.generate_tags(content, max_tags, language) for content in contents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        try:
            self._last_call_info = {'provider': 'BATCH', 'duration': time.time() - start}
        except Exception:
            pass
        return results
    
    async def is_ebook(self, file_name: str, language: str = 'zh-CN') -> bool:
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
        """
        批量生成标签
        
        Args:
            contents: 内容列表
            max_tags: 每个内容的最大标签数
            
        Returns:
            标签列表的列表 [[tags1], [tags2], ...]
        """
        if not self.is_available():
            return [[] for _ in contents]
        
        try:
            # 并发调用AI生成标签
            tasks = [self.generate_tags(content, max_tags) for content in contents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果（过滤异常）
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch tag generation failed for item {i}: {result}")
                    final_results.append([])
                else:
                    final_results.append(result)
            
            logger.info(f"Batch generated tags for {len(contents)} items")
            return final_results
            
        except Exception as e:
            logger.error(f"Batch generate tags error: {e}", exc_info=True)
            return [[] for _ in contents]
    
    async def generate_note_from_content(
        self,
        content: str,
        content_type: str,
        max_length: int = 250,
        language: str = 'zh-CN'
    ) -> str:
        """
        根据内容生成笔记
        
        Args:
            content: 原始内容
            content_type: 内容类型 (text/link/document)
            max_length: 笔记最大长度
            language: 语言
            
        Returns:
            生成的笔记内容
        """
        if not self.is_available():
            return ""
        
        try:
            # 判断是否为正式内容
            is_formal = is_formal_content(content[:1000], content_type)
            
            # 构建prompt
            if language.startswith('zh'):
                if is_formal:
                    # 正式风格
                    prompt = f"请为这份{content_type}内容生成简明笔记（不超过{max_length}字）。\n\n"
                    prompt += "要求：\n"
                    prompt += "• 准确提炼核心内容和关键信息\n"
                    prompt += "• 保持专业性和准确性\n"
                    prompt += "• 便于检索和复习\n"
                    prompt += "• 直接输出笔记内容，不要附加其他信息\n\n"
                else:
                    # 轻松风格
                    prompt = f"帮我记一下这个{content_type}的要点（{max_length}字以内就好）。\n\n"
                    prompt += "希望你能：\n"
                    prompt += "• 说清楚核心内容和重要信息\n"
                    prompt += "• 语言自然一些，别太正式\n"
                    prompt += "• 方便以后快速回顾\n"
                    prompt += "• 直接输出笔记，不需要其他说明\n\n"
                prompt += f"内容：\n{content[:3000]}"
            else:
                if is_formal:
                    # Formal style
                    prompt = f"Please generate a concise note (within {max_length} words) for this {content_type} content.\n\n"
                    prompt += "Requirements:\n"
                    prompt += "• Accurately extract core content and key information\n"
                    prompt += "• Maintain professionalism and accuracy\n"
                    prompt += "• Suitable for retrieval and review\n"
                    prompt += "• Output note content directly, no metadata\n\n"
                else:
                    # Casual style
                    prompt = f"Help me jot down the key points of this {content_type} (around {max_length} words).\n\n"
                    prompt += "Please:\n"
                    prompt += "• Explain the core content and important info clearly\n"
                    prompt += "• Keep it natural, not too formal\n"
                    prompt += "• Make it easy to review later\n"
                    prompt += "• Just the note, no extra explanations\n\n"
                prompt += f"Content:\n{content[:3000]}"
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": self.provider.temperature
                }
            )
            note_content = r.json()['choices'][0]['message']['content'].strip()
            
            logger.info(f"Generated note from content: {len(note_content)} chars")
            return note_content
            
        except Exception as e:
            logger.error(f"Generate note from content error: {e}", exc_info=True)
            return ""
    
    async def generate_note_from_ai_analysis(
        self,
        ai_summary: str,
        ai_key_points: List[str],
        ai_category: str,
        title: str,
        language: str = 'zh-CN'
    ) -> str:
        """
        根据AI分析结果整理文档笔记
        
        Args:
            ai_summary: AI摘要
            ai_key_points: AI关键点
            ai_category: AI分类
            title: 文档标题
            language: 语言
            
        Returns:
            整理的完整笔记
        """
        if not self.is_available():
            return ""
        
        try:
            # 判断是否为正式内容（基于分类）
            is_formal = is_formal_content("", "", ai_category)
            
            # 构建prompt
            key_points_text = '\n'.join([f"- {point}" for point in ai_key_points]) if ai_key_points else "无"
            
            if language.startswith('zh'):
                if is_formal:
                    # 正式风格
                    prompt = f"请根据以下AI分析整理一份完整的文档笔记。\n\n"
                    prompt += f"文档：{title}\n"
                    prompt += f"分类：{ai_category}\n\n"
                    prompt += f"摘要：\n{ai_summary}\n\n"
                    prompt += f"关键点：\n{key_points_text}\n\n"
                    prompt += "要求：\n"
                    prompt += "• 准确整合摘要和关键点信息\n"
                    prompt += "• 保持专业性和逻辑性\n"
                    prompt += "• 结构清晰便于理解\n"
                    prompt += "• 直接输出笔记内容\n"
                else:
                    # 轻松风格
                    prompt = f"帮我把这些AI分析的内容整理成一份笔记。\n\n"
                    prompt += f"标题是《{title}》\n"
                    prompt += f"类型是{ai_category}\n\n"
                    prompt += f"AI的总结：\n{ai_summary}\n\n"
                    prompt += f"主要要点：\n{key_points_text}\n\n"
                    prompt += "希望你能：\n"
                    prompt += "• 把摘要和要点融合在一起\n"
                    prompt += "• 组织得清楚易懂\n"
                    prompt += "• 语言自然流畅\n"
                    prompt += "• 直接给我笔记内容就好\n"
            else:
                if is_formal:
                    # Formal style
                    prompt = "Please organize a complete document note based on the following AI analysis.\n\n"
                    prompt += f"Document: {title}\n"
                    prompt += f"Category: {ai_category}\n\n"
                    prompt += f"Summary:\n{ai_summary}\n\n"
                    prompt += f"Key Points:\n{key_points_text}\n\n"
                    prompt += "Requirements:\n"
                    prompt += "• Accurately integrate summary and key points\n"
                    prompt += "• Maintain professionalism and logical flow\n"
                    prompt += "• Clear structure, easy to understand\n"
                    prompt += "• Output note content directly\n"
                else:
                    # Casual style
                    prompt = "Help me organize these AI analysis results into a note.\n\n"
                    prompt += f"Title: {title}\n"
                    prompt += f"Type: {ai_category}\n\n"
                    prompt += f"AI Summary:\n{ai_summary}\n\n"
                    prompt += f"Main Points:\n{key_points_text}\n\n"
                    prompt += "Please:\n"
                    prompt += "• Combine the summary and points naturally\n"
                    prompt += "• Keep it clear and easy to understand\n"
                    prompt += "• Use natural, flowing language\n"
                    prompt += "• Just give me the note content\n"
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": self.provider.temperature
                }
            )
            note_content = r.json()['choices'][0]['message']['content'].strip()
            
            logger.info(f"Generated note from AI analysis: {len(note_content)} chars")
            return note_content
            
        except Exception as e:
            logger.error(f"Generate note from AI analysis error: {e}", exc_info=True)
            return ""
    
    async def generate_title_from_text(self, content: str, max_length: int = 32, language: str = 'zh-CN') -> str:
        """
        从文本内容生成标题
        
        Args:
            content: 文本内容
            max_length: 标题最大长度(字符数)
            language: 语言代码
            
        Returns:
            生成的标题
        """
        if not content or not content.strip():
            return "无标题"
        
        try:
            # 检测语言和判断内容类型
            detected_lang = detect_content_language(content)
            is_formal = is_formal_content(content[:1000])
            
            if language.startswith('zh') or detected_lang == 'zh':
                if is_formal:
                    prompt = f"请为这段文本拟一个标题（{max_length}字以内）。\n\n"
                    prompt += "要求：\n"
                    prompt += "• 准确概括核心内容\n"
                    prompt += "• 简洁规范\n"
                    prompt += "• 不加引号\n"
                    prompt += "• 直接输出标题\n\n"
                else:
                    prompt = f"帮我给这段内容想个标题（{max_length}字以内）。\n\n"
                    prompt += "希望：\n"
                    prompt += "• 能说清楚主要内容\n"
                    prompt += "• 简单明了\n"
                    prompt += "• 不要加引号\n"
                    prompt += "• 直接给我标题就好\n\n"
                prompt += f"内容：\n{content[:1000]}"
            else:
                if is_formal:
                    prompt = f"Please create a title for this text (within {max_length} characters).\n\n"
                    prompt += "Requirements:\n"
                    prompt += "• Accurately summarize core content\n"
                    prompt += "• Concise and formal\n"
                    prompt += "• No quotation marks\n"
                    prompt += "• Output title directly\n\n"
                else:
                    prompt = f"Help me come up with a title for this content (around {max_length} characters).\n\n"
                    prompt += "Please:\n"
                    prompt += "• Capture the main content\n"
                    prompt += "• Keep it simple and clear\n"
                    prompt += "• No quotes\n"
                    prompt += "• Just give me the title\n\n"
                prompt += f"Content:\n{content[:1000]}"
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": self.provider.temperature
                }
            )
            title = r.json()['choices'][0]['message']['content'].strip()
            
            # 移除可能的引号
            title = title.strip('"\'""''')
            
            # 确保标题不超过最大长度
            if len(title) > max_length:
                title = title[:max_length-3] + "..."
            
            logger.info(f"Generated title from text: {title}")
            return title
            
        except Exception as e:
            logger.error(f"Generate title from text error: {e}", exc_info=True)
            # 降级：返回截断的文本
            fallback = content[:max_length].strip()
            if len(content) > max_length:
                fallback = fallback[:max_length-3] + "..."
            return fallback

_summarizer = None


def get_ai_summarizer(config=None):
    global _summarizer
    if not _summarizer and config: _summarizer = AISummarizer(config)
    return _summarizer

async def summarize_link(url, content, config):
    summarizer = get_ai_summarizer(config)
    return await summarizer.summarize_content(content, url)
