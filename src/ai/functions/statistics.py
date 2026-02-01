"""
Statistics Functions
Provides archive system statistics
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_statistics(context, **kwargs) -> Dict[str, Any]:
    """
    获取归档系统统计数据
    
    Args:
        context: Bot context
        
    Returns:
        {
            "total_archives": int,  # 归档总数
            "total_tags": int,      # 标签总数
            "recent_week": int,     # 最近7天归档数
            "has_data": bool        # 是否有数据
        }
    """
    try:
        ai_cache = context.bot_data.get('ai_data_cache')
        if not ai_cache:
            return {
                'total_archives': 0,
                'total_tags': 0,
                'recent_week': 0,
                'has_data': False,
                'error': 'AI cache not available'
            }
        
        stats = ai_cache.get_statistics()
        
        return {
            'total_archives': stats.get('total', 0),
            'total_tags': stats.get('tags', 0),
            'recent_week': stats.get('recent_week', 0),
            'has_data': stats.get('total', 0) > 0
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        return {'error': str(e)}


def register(registry):
    """Register statistics functions"""
    registry.register(
        'get_statistics',
        get_statistics,
        schema={
            'description': '获取归档系统的统计数据，包括归档总数、标签总数、最近7天归档数',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    )
