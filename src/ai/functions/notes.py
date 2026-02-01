"""
Notes Functions
Provides note query and management
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def get_notes_list(
    context,
    limit: int = 10,
    sort: str = 'recent',
    has_link: bool = None,
    **kwargs
) -> Dict[str, Any]:
    """
    获取笔记列表
    
    Args:
        context: Bot context
        limit: 返回数量 (1-100)
        sort: 排序方式 ('recent' 或 'oldest')
        has_link: 是否筛选有链接的笔记 (true/false/null)
        
    Returns:
        {
            "total_count": int,     # 笔记总数
            "sample_count": int,    # 返回的样本数
            "notes": [
                {
                    "id": int,
                    "title": str,
                    "content_preview": str,
                    "has_link": bool,
                    "created_at": str
                }
            ]
        }
    """
    try:
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            return {
                'total_count': 0,
                'sample_count': 0,
                'notes': [],
                'error': 'Note manager not available'
            }
        
        # 验证limit范围
        if limit < 1:
            limit = 10
        if limit > 100:
            limit = 100
        
        # 获取所有笔记
        all_notes = note_manager.get_all_notes(limit=100)
        
        if not all_notes:
            return {
                'total_count': 0,
                'sample_count': 0,
                'notes': []
            }
        
        # 添加has_link字段
        for note in all_notes:
            note['has_link'] = bool(note.get('storage_path'))
        
        # 筛选条件
        if has_link is not None:
            if has_link:
                all_notes = [n for n in all_notes if n.get('has_link')]
            else:
                all_notes = [n for n in all_notes if not n.get('has_link')]
        
        # 排序
        if sort == 'oldest':
            all_notes.sort(key=lambda x: x.get('created_at', ''))
        else:
            all_notes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 限制数量
        notes_sample = all_notes[:limit]
        
        # 格式化返回
        formatted_notes = []
        for note in notes_sample:
            formatted_notes.append({
                'id': note.get('id'),
                'title': note.get('title', ''),
                'content_preview': (note.get('content', '') or '')[:100],
                'has_link': note.get('has_link', False),
                'created_at': note.get('created_at', '')
            })
        
        return {
            'total_count': len(all_notes),
            'sample_count': len(formatted_notes),
            'notes': formatted_notes
        }
        
    except Exception as e:
        logger.error(f"Error getting notes list: {e}", exc_info=True)
        return {'error': str(e)}


def get_notes_count(context, **kwargs) -> Dict[str, Any]:
    """
    获取笔记总数统计
    
    Args:
        context: Bot context
        
    Returns:
        {
            "total_count": int,      # 笔记总数
            "attached": int,         # 关联归档的笔记数
            "standalone": int        # 独立笔记数
        }
    """
    try:
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            return {
                'total_count': 0,
                'with_link': 0,
                'standalone': 0,
                'error': 'Note manager not available'
            }
        
        all_notes = note_manager.get_all_notes(limit=100)
        
        if not all_notes:
            return {
                'total_count': 0,
                'attached': 0,
                'standalone': 0
            }
        
        # 有storage_path表示关联了归档
        attached = sum(1 for n in all_notes if n.get('storage_path'))
        standalone = len(all_notes) - attached
        
        return {
            'total_count': len(all_notes),
            'attached': attached,       # 关联归档的笔记
            'standalone': standalone    # 独立笔记
        }
        
    except Exception as e:
        logger.error(f"Error getting notes count: {e}", exc_info=True)
        return {'error': str(e)}


def register(registry):
    """Register notes functions"""
    registry.register(
        'get_notes_list',
        get_notes_list,
        schema={
            'description': '获取笔记列表，可以指定排序方式和筛选条件',
            'parameters': {
                'type': 'object',
                'properties': {
                    'limit': {
                        'type': 'integer',
                        'description': '返回的笔记数量，范围1-100',
                        'minimum': 1,
                        'maximum': 100,
                        'default': 10
                    },
                    'sort': {
                        'type': 'string',
                        'enum': ['recent', 'oldest'],
                        'description': '排序方式：recent=最新优先，oldest=最早优先',
                        'default': 'recent'
                    },
                    'has_link': {
                        'type': 'boolean',
                        'description': '是否筛选有链接的笔记：true=仅有链接，false=仅无链接，null=不限'
                    }
                },
                'required': []
            }
        }
    )
    
    registry.register(
        'get_notes_count',
        get_notes_count,
        schema={
            'description': '获取笔记总数统计，包括总数、关联归档的笔记数量、独立笔记数量',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    )
