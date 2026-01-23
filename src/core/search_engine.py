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
        
        # Format each result
        formatted_results = []
        keyboards_per_item = []
        
        for idx, archive in enumerate(search_result.get('results', []), 1):
            archive_id = archive.get('id')
            emoji = get_content_type_emoji(archive.get('content_type', ''))
            title = archive.get('title', 'Untitled')
            title_truncated = truncate_text(title, 50)
            
            # 构建跳转链接（如果有storage_path）
            storage_path = archive.get('storage_path')
            storage_type = archive.get('storage_type')
            if with_links and storage_path and storage_type == 'telegram':
                # 解析 storage_path: 可能是 "message_id" 或 "channel_id:message_id" 或 "channel_id:message_id:file_id"
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    # 格式: channel_id:message_id[:file_id]
                    channel_id = parts[0].replace('-100', '')  # 移除-100前缀
                    message_id = parts[1]
                else:
                    # 格式: message_id（需要从配置获取channel_id）
                    from ..utils.config import get_config
                    config = get_config()
                    channel_id = str(config.telegram_channel_id).replace('-100', '')
                    message_id = storage_path
                
                # Telegram链接格式：https://t.me/c/{channel_id}/{message_id}
                link = f"https://t.me/c/{channel_id}/{message_id}"
                title_truncated = f"<a href='{link}'>{title_truncated}</a>"
            
            # Get tags for this archive
            tags = self.db_storage.get_archive_tags(archive_id)
            tags_str = ' '.join(f"#{tag}" for tag in tags) if tags else ''
            
            archived_at = archive.get('archived_at', '')
            
            # 检查精选和笔记状态
            is_favorite = db_instance.is_favorite(archive_id) if db_instance else False
            has_notes = db_instance.has_notes(archive_id) if db_instance else False
            
            # 构建状态图标（按照要求的顺序）
            fav_icon = "❤️ 已精选" if is_favorite else "🤍 未精选"
            note_icon = "📝 √ 有笔记" if has_notes else "📝 无笔记"
            
            # 格式化结果为一行
            result_text = f"{idx}. {emoji} {title_truncated}"
            if tags_str:
                result_text += f"\n   {tags_str}"
            result_text += f"\n   {fav_icon} | {note_icon} | 📅 {archived_at}"
            
            # 不再添加按钮，返回空的按钮列表
            keyboards_per_item.append([])
            formatted_results.append(result_text)
        
        results_text = '\n---------------------\n'.join(formatted_results)
        
        final_text = self.i18n.t(
            'search_results',
            count=count,
            keyword=search_result.get('query', ''),
            results=results_text
        )
        
        return final_text, keyboards_per_item
