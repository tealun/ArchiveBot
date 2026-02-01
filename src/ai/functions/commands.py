"""
Command Execution Functions
Bridge between Function Calling and existing command handlers
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def execute_command(
    context,
    command: str,
    params: Dict[str, Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    执行系统命令
    
    Args:
        context: Bot context
        command: 命令名称 ('status', 'notes', 'search', 'tags', 'review')
        params: 命令参数
        
    Returns:
        {
            "success": bool,
            "command": str,
            "message": str,
            "data": dict
        }
    """
    try:
        from ..operations.safe_executor import execute_safe_operation
        from ...utils.language_context import get_user_language
        
        if params is None:
            params = {}
        
        # 映射命令名到operation_type
        command_mapping = {
            'status': 'stats',
            'stats': 'stats',
            'notes': 'notes',
            'search': 'search',
            'tags': 'tags',
            'review': 'review',
            '回顾': 'review',
            '統計': 'stats',
            '统计': 'stats',
            '標籤': 'tags',
            '标签': 'tags',
            '筆記': 'notes',
            '笔记': 'notes',
            '搜索': 'search',
            '搜尋': 'search'
        }
        
        operation_type = command_mapping.get(command.lower(), command.lower())
        
        # 获取用户语言（优先级：用户设置 > 配置 > 系统默认）
        language = get_user_language(context)
        
        # 执行命令
        success, message, data = await execute_safe_operation(
            operation_type=operation_type,
            operation_params=params,
            context=context,
            language=language
        )
        
        logger.info(f"✓ Command executed: {command} -> {operation_type}")
        
        return {
            'success': success,
            'command': command,
            'operation_type': operation_type,
            'message': message,
            'data': data or {}
        }
        
    except Exception as e:
        logger.error(f"Error executing command: {e}", exc_info=True)
        return {
            'success': False,
            'command': command,
            'error': str(e)
        }


def register(registry):
    """Register command execution function"""
    registry.register(
        'execute_command',
        execute_command,
        schema={
            'description': '执行系统命令，支持status(统计)/notes(笔记列表)/search(搜索)/tags(标签列表)/review(回顾)等命令',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'enum': ['status', 'stats', 'notes', 'search', 'tags', 'review', '统计', '笔记', '搜索', '标签', '回顾'],
                        'description': '命令名称：status/stats=系统统计, notes/笔记=笔记列表, search/搜索=搜索归档, tags/标签=标签列表, review/回顾=随机回顾'
                    },
                    'params': {
                        'type': 'object',
                        'description': '命令参数（可选），如search需要keyword参数，review可指定type/content_type/period等',
                        'properties': {
                            'keyword': {
                                'type': 'string',
                                'description': 'search命令的搜索关键词'
                            },
                            'type': {
                                'type': 'string',
                                'description': 'review命令的类型：random=随机回顾, summary=活动摘要'
                            },
                            'content_type': {
                                'type': 'string',
                                'description': 'review命令的内容类型筛选：text/link/image/video/audio/file'
                            },
                            'period': {
                                'type': 'string',
                                'description': 'review命令的时间范围：today/yesterday/week/month/quarter/year'
                            },
                            'limit': {
                                'type': 'integer',
                                'description': '返回数量限制'
                            }
                        }
                    }
                },
                'required': ['command']
            }
        }
    )
