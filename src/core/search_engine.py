"""
Search engine module
Provides search functionality for archives
"""

import logging
from typing import List, Dict, Any, Optional

from ..storage.database import DatabaseStorage
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
            
            logger.debug(f"🔍 Search query: '{query}' -> keyword='{keyword}', tags={tag_names}")
            
            # Search with total count
            results, total_count = self.db_storage.search_archives(
                keyword=keyword,
                tag_names=tag_names if tag_names else None,
                limit=limit,
                offset=offset,
                return_total=True
            )
            
            logger.info(f"✅ Search completed: Found {len(results)} results (total: {total_count}) for query '{query}'")
            
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
            logger.error(f"❌ Search error for query '{query}': {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'total_count': 0,
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
    
    def format_results(self, search_result: Dict[str, Any], with_links: bool = True, db_instance=None) -> tuple:
        """
        Format search results for display
        
        Args:
            search_result: Search result dictionary
            with_links: 是否包含跳转链接
            db_instance: Database instance for checking favorite/notes status
            
        Returns:
            Tuple of (formatted_text, inline_keyboards_per_item)
        """
        if not search_result.get('success'):
            error = search_result.get('error', 'Unknown error')
            return self.i18n.t('error_occurred', error=error), []
        
        count = search_result.get('count', 0)
        
        if count == 0:
            return self.i18n.t('search_no_results', keyword=search_result.get('query', '')), []
        
        # 使用MessageBuilder统一格式化
        from ..utils.message_builder import MessageBuilder
        
        archives = search_result.get('results', [])
        
        # 添加tags字段（如果没有）
        for archive in archives:
            if 'tags' not in archive:
                archive['tags'] = self.db_storage.get_archive_tags(archive.get('id'))
        
        results_text = MessageBuilder.format_archive_list(
            archives,
            self.i18n,
            db_instance=db_instance,
            with_links=with_links
        )
        
        final_text = self.i18n.t(
            'search_results',
            count=count,
            keyword=search_result.get('query', ''),
            results=results_text
        )
        
        # 返回空的按钮列表（保持接口兼容）
        keyboards_per_item = [[] for _ in archives]
        
        return final_text, keyboards_per_item
