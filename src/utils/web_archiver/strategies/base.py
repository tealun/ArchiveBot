"""
Base strategy interface for web fetching
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """网页抓取结果"""
    success: bool
    html: Optional[str] = None
    text: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    strategy_used: Optional[str] = None
    quality_score: float = 0.0  # 0-1评分，用于判断是否需要fallback
    error: Optional[str] = None
    
    @classmethod
    def empty(cls, url: str = None, error: str = "No content fetched") -> 'FetchResult':
        """创建空结果（抓取失败）"""
        return cls(
            success=False,
            url=url,
            quality_score=0.0,
            error=error
        )
    
    @classmethod
    def from_telegram_preview(cls, url: str, preview_data: Dict[str, Any]) -> 'FetchResult':
        """从Telegram预览创建结果"""
        return cls(
            success=True,
            url=url,
            title=preview_data.get('title'),
            text=preview_data.get('description'),
            metadata=preview_data,
            strategy_used='telegram_preview',
            quality_score=0.3  # 预览信息质量较低
        )


class FetchStrategy(ABC):
    """抓取策略基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
    
    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """
        抓取网页
        
        Args:
            url: 目标URL
            **kwargs: 额外参数
            
        Returns:
            FetchResult对象
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass
    
    def _calculate_quality_score(self, html: str, text: str) -> float:
        """
        计算内容质量评分
        
        Args:
            html: HTML内容
            text: 文本内容
            
        Returns:
            0-1之间的质量分数
        """
        if not html and not text:
            return 0.0
        
        score = 0.0
        
        # HTML长度评分（0-0.3）
        if html:
            html_len = len(html)
            if html_len > 10000:
                score += 0.3
            elif html_len > 5000:
                score += 0.2
            elif html_len > 1000:
                score += 0.1
        
        # 文本长度评分（0-0.4）
        if text:
            text_len = len(text)
            if text_len > 2000:
                score += 0.4
            elif text_len > 1000:
                score += 0.3
            elif text_len > 500:
                score += 0.2
            elif text_len > 200:
                score += 0.1
        
        # HTML结构评分（0-0.3）
        if html:
            structure_score = 0
            if '<article' in html or '<main' in html:
                structure_score += 0.15
            if '<p>' in html:
                structure_score += 0.1
            if 'og:' in html or 'twitter:' in html:
                structure_score += 0.05
            score += structure_score
        
        return min(score, 1.0)
