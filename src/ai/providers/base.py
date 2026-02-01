"""
AI Provider base class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class AIProvider(ABC):
    @abstractmethod
    async def summarize(self, content: str, max_tokens: int = 500, language: str = 'zh-CN', 
                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: pass
    @abstractmethod
    async def generate_tags(self, content: str, max_tags: int = 5, language: str = 'zh-CN') -> List[str]: pass
    @abstractmethod
    async def categorize(self, content: str, language: str = 'zh-CN') -> str: pass
