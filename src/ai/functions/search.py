"""
Search Functions
Provides archive search capabilities
"""
import logging
from typing import Dict, Any, List
from .filter_utils import should_apply_exclusion, get_exclusion_filters

logger = logging.getLogger(__name__)


def search_archives(
    context,
    keyword: str,
    limit: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    全文搜索归档内容
    
    Args:
        context: Bot context
        keyword: 搜索关键词（必填）
        limit: 返回结果数量 (1-50)
        
    Returns:
        {
            "keyword": str,         # 搜索关键词
            "total_count": int,     # 匹配总数
            "results": [
                {
                    "id": int,
                    "title": str,
                    "content_type": str,
                    "content_preview": str,
                    "created_at": str
                }
            ]
        }
    """
    try:
        search_engine = context.bot_data.get('search_engine')
        if not search_engine:
            return {
                'keyword': keyword,
                'total_count': 0,
                'results': [],
                'error': 'Search engine not available'
            }
        
        # 验证limit
        if limit < 1:
            limit = 10
        if limit > 50:
            limit = 50
        
        # 执行搜索
        search_result = search_engine.search(keyword, limit=limit)
        
        if not search_result.get('success'):
            return {
                'keyword': keyword,
                'total_count': 0,
                'results': [],
                'error': search_result.get('error', 'Search failed')
            }
        
        # 应用排除过滤（如果启用）
        results = search_result.get('results', [])
        if should_apply_exclusion(context):
            excluded_channels, excluded_tags = get_exclusion_filters(context)
            
            if excluded_channels or excluded_tags:
                filtered_results = []
                for archive in results:
                    # 检查频道排除
                    skip = False
                    if excluded_channels:
                        storage_path = archive.get('storage_path', '')
                        for channel_id in excluded_channels:
                            if storage_path.startswith(f"telegram:{channel_id}:"):
                                skip = True
                                break
                    
                    # 检查标签排除
                    if not skip and excluded_tags:
                        archive_tags = archive.get('tags', [])
                        for tag in excluded_tags:
                            if tag in archive_tags:
                                skip = True
                                break
                    
                    if not skip:
                        filtered_results.append(archive)
                
                results = filtered_results
                logger.debug(f"Search filtered: {len(search_result.get('results', []))} -> {len(results)} results")
        
        # 格式化结果 - 返回完整的archive对象以便后续格式化
        formatted_results = []
        for archive in results:
            # Return full archive object for proper formatting
            formatted_results.append(archive)
        
        return {
            'keyword': keyword,
            'total_count': len(formatted_results),  # 使用过滤后的实际数量
            'results': formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error searching archives: {e}", exc_info=True)
        return {'error': str(e)}


def register(registry):
    """Register search functions"""
    registry.register(
        'search_archives',
        search_archives,
        schema={
            'description': '使用关键词全文搜索归档内容，支持标题和内容搜索',
            'parameters': {
                'type': 'object',
                'properties': {
                    'keyword': {
                        'type': 'string',
                        'description': '搜索关键词（必填），使用用户原语言，不要翻译'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '返回结果数量，范围1-50',
                        'minimum': 1,
                        'maximum': 50,
                        'default': 10
                    }
                },
                'required': ['keyword']
            }
        }
    )
