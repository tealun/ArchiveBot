"""
AI Summarizer - 云端API服务
"""
import logging, json
from typing import Dict, Any, List
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)

class AIProvider(ABC):
    @abstractmethod
    async def summarize(self, content: str, max_tokens: int = 500) -> Dict[str, Any]: pass
    @abstractmethod
    async def generate_tags(self, content: str, max_tags: int = 5) -> List[str]: pass
    @abstractmethod
    async def categorize(self, content: str) -> str: pass

class OpenAIProvider(AIProvider):
    def __init__(self, api_key, model="gpt-3.5-turbo", api_url=None):
        self.api_key, self.model = api_key, model
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        try:
            import httpx
            self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
            self.available = True
        except: self.available = False
    
    async def summarize(self, content, max_tokens=500):
        r = await self.client.post(self.api_url,
            json={"model": self.model, "messages": [{"role": "user", "content": f"总结：{content[:4000]}"}], "max_tokens": max_tokens})
        text = r.json()['choices'][0]['message']['content']
        return {'summary': text, 'key_points': [], 'tags': []}
    
    async def generate_tags(self, content, max_tags=5):
        r = await self.client.post(self.api_url,
            json={"model": self.model, "messages": [{"role": "user", "content": f"为以下内容生成{max_tags}个中文标签（逗号分隔）：\n{content[:1000]}"}], "max_tokens": 50})
        tags_str = r.json()['choices'][0]['message']['content']
        return [t.strip().replace('#', '') for t in tags_str.split(',') if t.strip()][:max_tags]
    
    async def categorize(self, content): return "技术"

class AISummarizer:
    def __init__(self, config):
        self.config, self.provider = config, None
        if not config.get('enabled'): return
        
        # 只使用云端API
        api = config.get('api', {})
        if not api.get('api_key'): 
            logger.warning("AI enabled but no API key provided")
            return
        
        provider_type = api.get('provider', 'openai')
        if provider_type in ['openai', 'grok']:
            try:
                self.provider = OpenAIProvider(
                    api['api_key'], 
                    api.get('model', 'gpt-3.5-turbo'),
                    api.get('api_url')  # 支持自定义API URL
                )
                logger.info(f"Using {provider_type.upper()} API: {api.get('model', 'gpt-3.5-turbo')}")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_type} provider: {e}")
    
    def is_available(self):
        """Check if AI provider is available"""
        return self.provider is not None and hasattr(self.provider, 'available') and self.provider.available
    
    async def summarize_content(self, content, url=None):
        if not self.is_available(): return {'success': False, 'error': 'AI不可用'}
        try:
            result = await self.provider.summarize(content, 1000)
            result['success'], result['category'] = True, '技术'
            result['provider'] = 'CLOUD'
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def generate_tags(self, content, max_tags=5):
        if not self.is_available(): return []
        try:
            return await self.provider.generate_tags(content, max_tags)
        except Exception as e:
            logger.error(f"Generate tags error: {e}")
            return []

_summarizer = None
def get_ai_summarizer(config=None):
    global _summarizer
    if not _summarizer and config: _summarizer = AISummarizer(config)
    return _summarizer

async def summarize_link(url, content, config):
    summarizer = get_ai_summarizer(config)
    return await summarizer.summarize_content(content, url)
