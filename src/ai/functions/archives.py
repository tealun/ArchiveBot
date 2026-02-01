"""
Archives Functions
Provides archive query and analysis by type, ID, period
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .filter_utils import apply_exclusion_to_query

logger = logging.getLogger(__name__)


def get_archives_by_type(
    context,
    content_type: str,
    limit: int = 20,
    **kwargs
) -> Dict[str, Any]:
    """
    根据内容类型获取归档列表
    
    Args:
        context: Bot context
        content_type: 内容类型 ('text', 'link', 'image', 'video', 'audio', 'file')
        limit: 返回数量 (1-100)
        
    Returns:
        {
            "content_type": str,
            "total_count": int,
            "sample_count": int,
            "archives": [...]
        }
    """
    try:
        storage = context.bot_data.get('db_storage')
        if not storage:
            return {
                'content_type': content_type,
                'total_count': 0,
                'sample_count': 0,
                'archives': [],
                'error': 'Storage not available'
            }
        
        # 验证content_type
        valid_types = ['text', 'link', 'image', 'video', 'audio', 'file']
        if content_type not in valid_types:
            return {
                'error': f'Invalid content_type. Must be one of: {", ".join(valid_types)}'
            }
        
        # 验证limit
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100
        
        # 应用排除规则
        where_clause, params = apply_exclusion_to_query(
            context, 
            storage, 
            base_where="content_type = ? AND deleted = 0",
            base_params=[content_type]
        )
        
        # 查询该类型的归档
        query = f"""
            SELECT id, title, content, content_type, storage_path, created_at
            FROM archives
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        rows = storage.db.execute(query, tuple(params)).fetchall()
        
        # 转换为archive对象格式
        archives_list = []
        for row in rows:
            archives_list.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'content_type': row[3],
                'storage_path': row[4],
                'created_at': row[5]
            })
        
        # 统计总数（应用相同的排除规则）
        count_where, count_params = apply_exclusion_to_query(
            context,
            storage,
            base_where="content_type = ? AND deleted = 0",
            base_params=[content_type]
        )
        count_query = f"SELECT COUNT(*) FROM archives WHERE {count_where}"
        total_count = storage.db.execute(count_query, tuple(count_params)).fetchone()[0]
        
        return {
            'content_type': content_type,
            'total_count': total_count,
            'sample_count': len(archives_list),
            'archives': archives_list
        }
        
    except Exception as e:
        logger.error(f"Error getting archives by type: {e}", exc_info=True)
        return {'error': str(e)}


def get_content_type_stats(context, **kwargs) -> Dict[str, Any]:
    """
    获取各内容类型的统计数据
    
    Args:
        context: Bot context
        
    Returns:
        {
            "total_archives": int,
            "by_type": {
                "text": int,
                "link": int,
                "image": int,
                "video": int,
                "audio": int,
                "file": int
            }
        }
    """
    try:
        storage = context.bot_data.get('db_storage')
        if not storage:
            return {
                'total_archives': 0,
                'by_type': {},
                'error': 'Storage not available'
            }
        
        # 应用排除规则
        where_clause, params = apply_exclusion_to_query(
            context,
            storage,
            base_where="deleted = 0"
        )
        
        # 统计各类型数量
        query = f"""
            SELECT content_type, COUNT(*) as cnt
            FROM archives
            WHERE {where_clause}
            GROUP BY content_type
        """
        
        rows = storage.db.execute(query, tuple(params)).fetchall()
        
        by_type = {}
        total = 0
        for row in rows:
            content_type = row[0]
            count = row[1]
            by_type[content_type] = count
            total += count
        
        return {
            'total_archives': total,
            'by_type': by_type
        }
        
    except Exception as e:
        logger.error(f"Error getting content type stats: {e}", exc_info=True)
        return {'error': str(e)}


def get_archive_by_id(
    context,
    archive_id: int,
    **kwargs
) -> Dict[str, Any]:
    """
    根据ID获取归档详情
    
    Args:
        context: Bot context
        archive_id: 归档ID
        
    Returns:
        {
            "id": int,
            "title": str,
            "content_type": str,
            "storage_path": str,
            "created_at": str,
            "tags": [str],
            "has_note": bool
        }
    """
    try:
        storage = context.bot_data.get('db_storage')
        if not storage:
            return {'error': 'Storage not available'}
        
        # 查询归档
        query = """
            SELECT id, title, content_type, storage_path, created_at
            FROM archives
            WHERE id = ? AND deleted = 0
        """
        
        row = storage.db.execute(query, (archive_id,)).fetchone()
        
        if not row:
            return {'error': f'Archive {archive_id} not found'}
        
        # 查询标签
        tags_query = """
            SELECT t.tag_name
            FROM tags t
            JOIN archive_tags at ON t.id = at.tag_id
            WHERE at.archive_id = ?
        """
        tag_rows = storage.db.execute(tags_query, (archive_id,)).fetchall()
        tags = [row[0] for row in tag_rows]
        
        # 检查是否有笔记
        note_query = """
            SELECT COUNT(*) FROM notes
            WHERE storage_path = ? AND deleted = 0
        """
        storage_path = row[3]
        has_note = storage.db.execute(note_query, (storage_path,)).fetchone()[0] > 0
        
        return {
            'id': row[0],
            'title': row[1] or '',
            'content_type': row[2],
            'storage_path': row[3],
            'created_at': row[4],
            'tags': tags,
            'has_note': has_note
        }
        
    except Exception as e:
        logger.error(f"Error getting archive by ID: {e}", exc_info=True)
        return {'error': str(e)}


def get_note_by_id(
    context,
    note_id: int,
    **kwargs
) -> Dict[str, Any]:
    """
    根据ID获取笔记详情
    
    Args:
        context: Bot context
        note_id: 笔记ID
        
    Returns:
        {
            "id": int,
            "title": str,
            "content": str,
            "storage_path": str,
            "created_at": str,
            "is_standalone": bool
        }
    """
    try:
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            return {'error': 'Note manager not available'}
        
        # 查询笔记
        query = """
            SELECT id, title, content, storage_path, created_at
            FROM notes
            WHERE id = ? AND deleted = 0
        """
        
        storage = context.bot_data.get('db_storage')
        row = storage.db.execute(query, (note_id,)).fetchone()
        
        if not row:
            return {'error': f'Note {note_id} not found'}
        
        return {
            'id': row[0],
            'title': row[1] or '',
            'content': row[2] or '',
            'storage_path': row[3],
            'created_at': row[4],
            'is_standalone': not bool(row[3])  # 无storage_path即为独立笔记
        }
        
    except Exception as e:
        logger.error(f"Error getting note by ID: {e}", exc_info=True)
        return {'error': str(e)}


def get_archives_by_period(
    context,
    period: str = 'week',
    **kwargs
) -> Dict[str, Any]:
    """
    根据时间周期获取归档
    
    Args:
        context: Bot context
        period: 时间周期 ('today', 'yesterday', 'week', 'month', 'quarter', 'year')
        
    Returns:
        {
            "period": str,
            "start_date": str,
            "end_date": str,
            "total_count": int,
            "archives": [...]
        }
    """
    try:
        storage = context.bot_data.get('db_storage')
        if not storage:
            return {'error': 'Storage not available'}
        
        # 计算时间范围
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if period == 'today':
            start_date = today_start
            end_date = now
        elif period == 'yesterday':
            start_date = today_start - timedelta(days=1)
            end_date = today_start
        elif period == 'week':
            start_date = today_start - timedelta(days=7)
            end_date = now
        elif period == 'month':
            start_date = today_start - timedelta(days=30)
            end_date = now
        elif period == 'quarter':
            start_date = today_start - timedelta(days=90)
            end_date = now
        elif period == 'year':
            start_date = today_start - timedelta(days=365)
            end_date = now
        else:
            return {'error': f'Invalid period. Must be one of: today, yesterday, week, month, quarter, year'}
        
        start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # 应用排除规则
        where_clause, params = apply_exclusion_to_query(
            context,
            storage,
            base_where="created_at >= ? AND created_at <= ? AND deleted = 0",
            base_params=[start_str, end_str]
        )
        
        # 查询该时间段的归档
        query = f"""
            SELECT id, title, content_type, created_at
            FROM archives
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT 50
        """
        
        rows = storage.db.execute(query, tuple(params)).fetchall()
        
        # 统计总数（应用相同的排除规则）
        count_where, count_params = apply_exclusion_to_query(
            context,
            storage,
            base_where="created_at >= ? AND created_at <= ? AND deleted = 0",
            base_params=[start_str, end_str]
        )
        count_query = f"SELECT COUNT(*) FROM archives WHERE {count_where}"
        total_count = storage.db.execute(count_query, tuple(count_params)).fetchone()[0]
        
        # 格式化结果
        archives = []
        for row in rows:
            archives.append({
                'id': row[0],
                'title': row[1] or '',
                'content_type': row[2],
                'created_at': row[3]
            })
        
        return {
            'period': period,
            'start_date': start_str,
            'end_date': end_str,
            'total_count': total_count,
            'sample_count': len(archives),
            'archives': archives
        }
        
    except Exception as e:
        logger.error(f"Error getting archives by period: {e}", exc_info=True)
        return {'error': str(e)}


def register(registry):
    """Register archives functions"""
    registry.register(
        'get_archives_by_type',
        get_archives_by_type,
        schema={
            'description': '根据内容类型获取归档列表，支持text/link/image/video/audio/file',
            'parameters': {
                'type': 'object',
                'properties': {
                    'content_type': {
                        'type': 'string',
                        'enum': ['text', 'link', 'image', 'video', 'audio', 'file'],
                        'description': '内容类型：text=纯文本, link=链接, image=图片, video=视频, audio=音频, file=文件'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': '返回数量，范围1-100',
                        'minimum': 1,
                        'maximum': 100,
                        'default': 20
                    }
                },
                'required': ['content_type']
            }
        }
    )
    
    registry.register(
        'get_content_type_stats',
        get_content_type_stats,
        schema={
            'description': '获取各内容类型的统计数据，显示每种类型的归档数量',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }
    )
    
    registry.register(
        'get_archive_by_id',
        get_archive_by_id,
        schema={
            'description': '根据ID获取归档详情，包括标题、类型、标签、是否有笔记等',
            'parameters': {
                'type': 'object',
                'properties': {
                    'archive_id': {
                        'type': 'integer',
                        'description': '归档ID'
                    }
                },
                'required': ['archive_id']
            }
        }
    )
    
    registry.register(
        'get_note_by_id',
        get_note_by_id,
        schema={
            'description': '根据ID获取笔记详情，包括标题、内容、创建时间、是否独立笔记等',
            'parameters': {
                'type': 'object',
                'properties': {
                    'note_id': {
                        'type': 'integer',
                        'description': '笔记ID'
                    }
                },
                'required': ['note_id']
            }
        }
    )
    
    registry.register(
        'get_archives_by_period',
        get_archives_by_period,
        schema={
            'description': '根据时间周期获取归档，支持today/yesterday/week/month/quarter/year',
            'parameters': {
                'type': 'object',
                'properties': {
                    'period': {
                        'type': 'string',
                        'enum': ['today', 'yesterday', 'week', 'month', 'quarter', 'year'],
                        'description': '时间周期：today=今天, yesterday=昨天, week=最近7天, month=最近30天, quarter=最近90天, year=最近365天',
                        'default': 'week'
                    }
                },
                'required': []
            }
        }
    )
