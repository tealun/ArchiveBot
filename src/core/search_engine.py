"""
Search engine module
Provides search functionality for archives
"""

import logging
from typing import List, Dict, Any, Optional

from ..storage.database import DatabaseStorage
from ..utils.helpers import truncate_text, format_datetime, get_content_type_emoji
from ..utils.i18n import get_i18n

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Search engine for archives
    """
    
    def __init__(self, db_storage: DatabaseStorage):
        """
        Initialize search engine
        
        Args:
            db_storage: DatabaseStorage instance
        """
        self.db_storage = db_storage
        self.i18n = get_i18n()
    
    def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search archives with query
        
        Args:
            query: Search query (keyword or #tag)
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Parse query
            keyword, tag_names = self._parse_query(query)
            
            # Search with total count
            results, total_count = self.db_storage.search_archives(
                keyword=keyword,
                tag_names=tag_names if tag_names else None,
                limit=limit,
                offset=offset,
                return_total=True
            )
            
            return {
                'success': True,
                'query': query,
                'keyword': keyword,
                'tags': tag_names,
                'count': len(results),
                'total_count': total_count,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'results': []
            }
    
    def _parse_query(self, query: str) -> tuple:
        """
        Parse search query into keyword and tags
        
        Args:
            query: Search query
            
        Returns:
            Tuple of (keyword, tag_names)
        """
        if not query:
            return None, []
        
        parts = query.split()
        tags = []
        keywords = []
        
        for part in parts:
            if part.startswith('#'):
                # Remove # prefix
                tag = part[1:]
                if tag:
                    tags.append(tag)
            else:
                keywords.append(part)
        
        keyword = ' '.join(keywords) if keywords else None
        
        return keyword, tags
    
    def format_results(self, search_result: Dict[str, Any], with_links: bool = True) -> tuple:
        """
        Format search results for display
        
        Args:
            search_result: Search result dictionary
            with_links: 是否包含跳转链接
            
        Returns:
            Tuple of (formatted_text, results_with_ai_data)
        """
        if not search_result.get('success'):
            error = search_result.get('error', 'Unknown error')
            return self.i18n.t('error_occurred', error=error), []
        
        count = search_result.get('count', 0)
        
        if count == 0:
            return self.i18n.t('search_no_results', keyword=search_result.get('query', '')), []
        
        # Format each result
        formatted_results = []
        results_with_ai = []
        
        for idx, archive in enumerate(search_result.get('results', []), 1):
            emoji = get_content_type_emoji(archive.get('content_type', ''))
            title = archive.get('title', 'Untitled')
            title_truncated = truncate_text(title, 50)
            
            # 构建跳转链接（如果有storage_path）
            storage_path = archive.get('storage_path')
            if with_links and storage_path:
                # 解析 storage_path: channel_id:message_id:file_id
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    channel_id = parts[0].replace('-100', '')  # 移除-100前缀
                    message_id = parts[1]
                    # Telegram链接格式：https://t.me/c/{channel_id}/{message_id}
                    link = f"https://t.me/c/{channel_id}/{message_id}"
                    title_truncated = f"<a href='{link}'>{title_truncated}</a>"
            
            # Get tags for this archive
            tags = self.db_storage.get_archive_tags(archive.get('id'))
            tags_str = ' '.join(f"#{tag}" for tag in tags) if tags else ''
            
            archived_at = archive.get('archived_at', '')
            
            # 格式化结果
            result_text = f"{idx}. {emoji} {title_truncated}"
            if tags_str:
                result_text += f"\n   {tags_str}"
            result_text += f"\n   📅 {archived_at}"
            
            # 检查是否有AI数据
            has_ai = bool(
                archive.get('ai_summary') or 
                archive.get('ai_key_points') or 
                archive.get('ai_category')
            )
            
            if has_ai:
                results_with_ai.append({
                    'index': idx,
                    'id': archive.get('id'),
                    'title': title,
                    'ai_summary': archive.get('ai_summary'),
                    'ai_key_points': archive.get('ai_key_points'),
                    'ai_category': archive.get('ai_category')
                })
            
            formatted_results.append(result_text)
        
        results_text = '\n\n'.join(formatted_results)
        
        final_text = self.i18n.t(
            'search_results',
            count=count,
            keyword=search_result.get('query', ''),
            results=results_text
        )
        
        return final_text, results_with_ai
