"""
Metadata extraction from HTML
提取网页元数据（Open Graph, Twitter Card, schema.org等）
"""

import logging
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """网页元数据提取器"""
    
    @staticmethod
    def extract(html: str, url: str = None) -> Dict[str, Any]:
        """
        提取网页元数据
        
        Args:
            html: HTML内容
            url: 页面URL
            
        Returns:
            元数据字典
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            metadata = {
                'url': url,
                'title': None,
                'description': None,
                'image': None,
                'site_name': None,
                'author': None,
                'published_time': None,
                'modified_time': None,
                'keywords': [],
                'language': None,
                'type': None,
            }
            
            # Open Graph
            og_data = MetadataExtractor._extract_open_graph(soup)
            metadata.update(og_data)
            
            # Twitter Card
            twitter_data = MetadataExtractor._extract_twitter_card(soup)
            # Twitter Card作为备选，不覆盖已有的OG数据
            for key, value in twitter_data.items():
                if not metadata.get(key):
                    metadata[key] = value
            
            # 基础meta标签
            basic_data = MetadataExtractor._extract_basic_meta(soup)
            for key, value in basic_data.items():
                if not metadata.get(key):
                    metadata[key] = value
            
            # HTML标签
            html_data = MetadataExtractor._extract_html_tags(soup)
            for key, value in html_data.items():
                if not metadata.get(key):
                    metadata[key] = value
            
            # 清理空值
            metadata = {k: v for k, v in metadata.items() if v}
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction error: {e}")
            return {'url': url} if url else {}
    
    @staticmethod
    def _extract_open_graph(soup: BeautifulSoup) -> Dict[str, Any]:
        """提取Open Graph数据"""
        og_data = {}
        
        og_mappings = {
            'og:title': 'title',
            'og:description': 'description',
            'og:image': 'image',
            'og:site_name': 'site_name',
            'og:type': 'type',
            'og:url': 'url',
            'article:author': 'author',
            'article:published_time': 'published_time',
            'article:modified_time': 'modified_time',
        }
        
        for og_property, key in og_mappings.items():
            meta = soup.find('meta', property=og_property)
            if meta and meta.get('content'):
                og_data[key] = meta['content']
        
        return og_data
    
    @staticmethod
    def _extract_twitter_card(soup: BeautifulSoup) -> Dict[str, Any]:
        """提取Twitter Card数据"""
        twitter_data = {}
        
        twitter_mappings = {
            'twitter:title': 'title',
            'twitter:description': 'description',
            'twitter:image': 'image',
            'twitter:site': 'site_name',
            'twitter:creator': 'author',
        }
        
        for twitter_name, key in twitter_mappings.items():
            meta = soup.find('meta', attrs={'name': twitter_name})
            if meta and meta.get('content'):
                twitter_data[key] = meta['content']
        
        return twitter_data
    
    @staticmethod
    def _extract_basic_meta(soup: BeautifulSoup) -> Dict[str, Any]:
        """提取基础meta标签"""
        basic_data = {}
        
        # Description
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta and desc_meta.get('content'):
            basic_data['description'] = desc_meta['content']
        
        # Keywords
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta and keywords_meta.get('content'):
            keywords_str = keywords_meta['content']
            basic_data['keywords'] = [k.strip() for k in keywords_str.split(',') if k.strip()]
        
        # Author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            basic_data['author'] = author_meta['content']
        
        # Language
        lang_meta = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if lang_meta and lang_meta.get('content'):
            basic_data['language'] = lang_meta['content']
        
        return basic_data
    
    @staticmethod
    def _extract_html_tags(soup: BeautifulSoup) -> Dict[str, Any]:
        """从HTML标签提取信息"""
        html_data = {}
        
        # Title从<title>标签
        title_tag = soup.find('title')
        if title_tag:
            html_data['title'] = title_tag.get_text().strip()
        
        # Language从<html lang="">
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            html_data['language'] = html_tag['lang']
        
        return html_data
