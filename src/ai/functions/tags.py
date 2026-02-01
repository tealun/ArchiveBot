"""
Tags Functions
Provides tag analysis and statistics
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def get_tag_analysis(
    context,
    limit: int = 15,
    **kwargs
) -> Dict[str, Any]:
    """
    获取标签使用统计分析
    
    Args:
        context: Bot context
        limit: 返回标签数量 (1-50)
        
    Returns:
        {
            "total_tags": int,
            "top_tags": [
                {
                    "name": str,
                    "count": int,
                    "percentage": float
                }
            ]
        }
    """
    try:
        ai_cache = context.bot_data.get('ai_data_cache')
        if not ai_cache:
            return {
                'total_tags': 0,
                'top_tags': [],
                'error': 'AI cache not available'
            }
        
        # 验证limit
        if limit < 1:
            limit = 15
        if limit > 50:
            limit = 50
        
        # 获取标签分析
        tag_analysis = ai_cache.get_tag_analysis(limit=limit)
        
        if not tag_analysis:
            return {
                'total_tags': 0,
                'top_tags': []
            }
        
        # 计算总使用次数
        total_usage = sum(tag.get('count', 0) for tag in tag_analysis)
        
        # 格式化结果
        formatted_tags = []
        for tag in tag_analysis:
            count = tag.get('count', 0)
            tag_name = tag.get('tag', '') or tag.get('tag_name', '')
            
            # 跳过空标签名（防止AI编造数据）
            if not tag_name or not tag_name.strip():
                logger.warning(f"Skipping empty tag name in analysis")
                continue
            
            formatted_tags.append({
                'name': tag_name,
                'count': count,
                'percentage': round(count / total_usage * 100, 1) if total_usage > 0 else 0
            })
        
        return {
            'total_tags': len(tag_analysis),
            'top_tags': formatted_tags
        }
        
    except Exception as e:
        logger.error(f"Error getting tag analysis: {e}", exc_info=True)
        return {'error': str(e)}


def register(registry):
    """Register tags functions"""
    registry.register(
        'get_tag_analysis',
        get_tag_analysis,
        schema={
            'description': '获取标签使用统计和分析，显示最常用的标签及其使用次数',
            'parameters': {
                'type': 'object',
                'properties': {
                    'limit': {
                        'type': 'integer',
                        'description': '返回标签数量，范围1-50',
                        'minimum': 1,
                        'maximum': 50,
                        'default': 15
                    }
                },
                'required': []
            }
        }
    )
