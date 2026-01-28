"""
Link metadata extractor
链接元数据提取器 - 提取网页标题、描述、图片等信息
"""

import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

try:
    import httpx
    from bs4 import BeautifulSoup
    METADATA_ENABLED = True
except ImportError:
    METADATA_ENABLED = False
    logger.warning("httpx or beautifulsoup4 not installed, link metadata extraction disabled")


class LinkMetadataExtractor:
    """
    提取链接的元数据信息
    """
    
    def __init__(self, timeout: int = 10, user_agent: str = None):
        """
        初始化提取器
        
        Args:
            timeout: 请求超时时间（秒）
            user_agent: 自定义 User-Agent
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    
    async def extract(self, url: str) -> Dict[str, Any]:
        """
        提取链接元数据
        
        Args:
            url: 网页URL
            
        Returns:
            包含元数据的字典
        """
        if not METADATA_ENABLED:
            return self._basic_metadata(url)
        
        try:
            # 异步获取网页内容
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                headers = {'User-Agent': self.user_agent}
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取元数据
                metadata = {
                    'url': str(response.url),  # 可能被重定向
                    'title': self._extract_title(soup),
                    'description': self._extract_description(soup),
                    'image': self._extract_image(soup, url),
                    'site_name': self._extract_site_name(soup),
                    'author': self._extract_author(soup),
                    'published_date': self._extract_date(soup),
                    'keywords': self._extract_keywords(soup),
                    'domain': urlparse(url).netloc,
                    'content_preview': self._extract_content_preview(soup),
                }
                
                logger.info(f"Extracted metadata for: {url}")
                return metadata
                
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error extracting metadata from {url}: {e}")
            return self._basic_metadata(url, error=str(e))
        except Exception as e:
            logger.error(f"Error extracting metadata from {url}: {e}", exc_info=True)
            return self._basic_metadata(url, error=str(e))
    
    def _basic_metadata(self, url: str, error: str = None) -> Dict[str, Any]:
        """
        返回基本元数据（当无法提取时）
        """
        parsed = urlparse(url)
        return {
            'url': url,
            'title': parsed.netloc or url,
            'description': None,
            'image': None,
            'site_name': parsed.netloc,
            'author': None,
            'published_date': None,
            'keywords': [],
            'domain': parsed.netloc,
            'content_preview': None,
            'extraction_error': error
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """提取标题"""
        # 尝试 Open Graph
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # 尝试 Twitter Card
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content'].strip()
        
        # 尝试标准 title 标签
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            return title_tag.string.strip()
        
        # 尝试 h1 标签
        h1 = soup.find('h1')
        if h1 and h1.get_text():
            return h1.get_text().strip()
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """提取描述"""
        # Open Graph
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Twitter Card
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc and twitter_desc.get('content'):
            return twitter_desc['content'].strip()
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        return None
    
    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """提取图片"""
        # Open Graph
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return self._resolve_url(og_image['content'], base_url)
        
        # Twitter Card
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return self._resolve_url(twitter_image['content'], base_url)
        
        # 尝试找第一张大图
        images = soup.find_all('img', src=True)
        for img in images:
            src = img.get('src')
            if src and not src.startswith('data:'):
                return self._resolve_url(src, base_url)
        
        return None
    
    def _extract_site_name(self, soup: BeautifulSoup) -> Optional[str]:
        """提取站点名称"""
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            return og_site['content'].strip()
        
        twitter_site = soup.find('meta', attrs={'name': 'twitter:site'})
        if twitter_site and twitter_site.get('content'):
            return twitter_site['content'].strip()
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """提取作者"""
        # Meta author
        author = soup.find('meta', attrs={'name': 'author'})
        if author and author.get('content'):
            return author['content'].strip()
        
        # Article author
        article_author = soup.find('meta', property='article:author')
        if article_author and article_author.get('content'):
            return article_author['content'].strip()
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """提取发布日期"""
        # Article published time
        published = soup.find('meta', property='article:published_time')
        if published and published.get('content'):
            return published['content'].strip()
        
        # Date meta
        date = soup.find('meta', attrs={'name': 'date'})
        if date and date.get('content'):
            return date['content'].strip()
        
        return None
    
    def _extract_keywords(self, soup: BeautifulSoup) -> list:
        """提取关键词"""
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        if keywords and keywords.get('content'):
            return [k.strip() for k in keywords['content'].split(',')]
        
        return []
    
    def _extract_content_preview(self, soup: BeautifulSoup, max_length: int = 300) -> Optional[str]:
        """提取内容预览"""
        # 尝试找主要内容区域
        main_tags = ['article', 'main', 'div.content', 'div.post-content']
        
        for tag_name in main_tags:
            if '.' in tag_name:
                tag, class_name = tag_name.split('.')
                content = soup.find(tag, class_=class_name)
            else:
                content = soup.find(tag_name)
            
            if content:
                text = content.get_text(separator=' ', strip=True)
                if text:
                    # 清理文本
                    text = re.sub(r'\s+', ' ', text)
                    return text[:max_length] + '...' if len(text) > max_length else text
        
        # 如果找不到，尝试提取所有段落
        paragraphs = soup.find_all('p')
        if paragraphs:
            text = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])
            text = re.sub(r'\s+', ' ', text)
            return text[:max_length] + '...' if len(text) > max_length else text
        
        return None
    
    def _resolve_url(self, url: str, base_url: str) -> str:
        """解析相对URL"""
        from urllib.parse import urljoin
        return urljoin(base_url, url)


# 全局实例
_extractor = None


def get_link_extractor() -> LinkMetadataExtractor:
    """获取全局提取器实例"""
    global _extractor
    if _extractor is None:
        _extractor = LinkMetadataExtractor()
    return _extractor


async def extract_link_metadata(url: str) -> Dict[str, Any]:
    """
    提取链接元数据（便捷函数）
    
    Args:
        url: 网页URL
        
    Returns:
        元数据字典
    """
    extractor = get_link_extractor()
    return await extractor.extract(url)
