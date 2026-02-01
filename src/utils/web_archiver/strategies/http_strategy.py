"""
HTTP-based fetching strategy using httpx
轻量级HTTP抓取，适用于静态网页
"""

import httpx
import logging
from typing import Dict, Any
from .base import FetchStrategy, FetchResult

logger = logging.getLogger(__name__)


class HttpStrategy(FetchStrategy):
    """基于httpx的HTTP抓取策略"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.user_agent = self.config.get(
            'user_agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.follow_redirects = self.config.get('follow_redirects', True)
        self.max_redirects = self.config.get('max_redirects', 5)
    
    @property
    def name(self) -> str:
        return 'http'
    
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """
        使用httpx抓取网页
        
        Args:
            url: 目标URL
            **kwargs: 额外参数（如headers）
            
        Returns:
            FetchResult对象
        """
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,zh-CN,zh;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # 合并自定义headers
            custom_headers = kwargs.get('headers', {})
            headers.update(custom_headers)
            
            logger.info(f"HTTP fetching: {url}")
            
            async with httpx.AsyncClient(
                follow_redirects=self.follow_redirects,
                timeout=self.timeout
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                html = response.text
                final_url = str(response.url)
                
                # 提取基础metadata
                metadata = {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('content-type', ''),
                    'content_length': len(html),
                    'final_url': final_url,
                    'encoding': response.encoding
                }
                
                # 简单提取title（正文提取由extractor负责）
                title = self._extract_title(html)
                
                # 计算质量分数
                quality_score = self._calculate_quality_score(html, html)
                
                logger.info(f"HTTP fetch success: {len(html)} bytes, quality={quality_score:.2f}")
                
                return FetchResult(
                    success=True,
                    html=html,
                    title=title,
                    url=final_url,
                    metadata=metadata,
                    strategy_used=self.name,
                    quality_score=quality_score
                )
                
        except httpx.TimeoutException as e:
            logger.warning(f"HTTP fetch timeout: {url} - {e}")
            return FetchResult.empty(url, f"Timeout: {e}")
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP status error: {url} - {e.response.status_code}")
            return FetchResult.empty(url, f"HTTP {e.response.status_code}")
            
        except Exception as e:
            logger.error(f"HTTP fetch error: {url} - {e}", exc_info=True)
            return FetchResult.empty(url, str(e))
    
    def _extract_title(self, html: str) -> str:
        """简单提取HTML标题"""
        import re
        
        # 尝试提取<title>标签
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            # 清理HTML实体
            title = re.sub(r'&[a-z]+;', ' ', title)
            return title[:200]
        
        # 尝试提取og:title
        og_title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_title_match:
            return og_title_match.group(1)[:200]
        
        return "Untitled"
