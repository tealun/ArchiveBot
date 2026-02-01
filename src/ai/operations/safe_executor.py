"""
AI Safe Operation Executor

Executes safe read-only operations directly without user confirmation.
Phase 1: Search, stats, tags, notes, review (read-only operations)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def execute_safe_operation(
    operation_type: str,
    operation_params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str = 'zh-CN'
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute safe read-only operations (Phase 1)
    
    Args:
        operation_type: Type of operation (search, stats, tags, notes, review)
        operation_params: Operation parameters
        context: Bot context
        language: User language code
        
    Returns:
        Tuple of (success: bool, message: str, data: Optional[Dict])
    """
    try:
        logger.info(f"🔍 AI executing safe operation: {operation_type} with params: {operation_params}")
        
        # Log audit event
        from ...ai.chat_router import _log_audit_event
        
        # Search operation
        if operation_type == 'search':
            result = await _execute_search(operation_params, context, language)
            _log_audit_event('safe_executed', operation_type, operation_params, context, language, result[1])
            return result
        
        # Stats operation
        elif operation_type == 'stats':
            result = await _execute_stats(context, language)
            _log_audit_event('safe_executed', operation_type, operation_params, context, language, result[1])
            return result
        
        # Tags operation
        elif operation_type == 'tags':
            result = await _execute_tags(operation_params, context, language)
            _log_audit_event('safe_executed', operation_type, operation_params, context, language, result[1])
            return result
        
        # Notes operation
        elif operation_type == 'notes':
            result = await _execute_notes(operation_params, context, language)
            _log_audit_event('safe_executed', operation_type, operation_params, context, language, result[1])
            return result
        
        # Review operation
        elif operation_type == 'review':
            result = await _execute_review(operation_params, context, language)
            _log_audit_event('safe_executed', operation_type, operation_params, context, language, result[1])
            return result
        
        # Unknown operation type
        else:
            logger.warning(f"Unknown safe operation type: {operation_type}")
            return False, _get_error_message('unknown_operation', language, operation_type), None
    
    except Exception as e:
        logger.error(f"Error executing safe operation {operation_type}: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e)), None


async def _execute_search(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Execute search operation"""
    try:
        keyword = params.get('keyword') or params.get('query')
        if not keyword:
            return False, _get_error_message('missing_keyword', language), None
        
        search_engine = context.bot_data.get('search_engine')
        if not search_engine:
            return False, _get_error_message('manager_not_found', language, 'search_engine'), None
        
        # Execute search with optional limit
        limit = params.get('limit', 10)
        search_result = search_engine.search(keyword, limit=limit, offset=0)
        
        # search_engine.search() returns a dict with structure:
        # {'success': bool, 'count': int, 'total_count': int, 'results': list, ...}
        if not search_result or not search_result.get('success'):
            return True, _get_success_message('search_no_results', language, keyword), {'count': 0, 'results': []}
        
        # Extract actual results array
        results_list = search_result.get('results', [])
        
        if not results_list:
            return True, _get_success_message('search_no_results', language, keyword), {'count': 0, 'results': []}
        
        # Format results for AI
        data = {
            'count': len(results_list),
            'keyword': keyword,
            'results': results_list
        }
        
        return True, _get_success_message('search_results', language, len(results_list), keyword), data
    
    except Exception as e:
        logger.error(f"Error executing search: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e)), None


async def _execute_stats(
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Execute stats operation"""
    try:
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            return False, _get_error_message('manager_not_found', language, 'db_storage'), None
        
        # Get statistics
        stats = db_storage.db.get_stats()
        
        data = {
            'total_archives': stats.get('total_archives', 0),
            'total_tags': stats.get('total_tags', 0),
            'storage_used': stats.get('storage_used', 'N/A'),
            'last_archive': stats.get('last_archive', 'N/A')
        }
        
        return True, _get_success_message('stats', language), data
    
    except Exception as e:
        logger.error(f"Error executing stats: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e)), None


async def _execute_tags(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Execute tags operation"""
    try:
        tag_manager = context.bot_data.get('tag_manager')
        if not tag_manager:
            return False, _get_error_message('manager_not_found', language, 'tag_manager'), None
        
        # Get all tags with counts (支持limit参数)
        limit = params.get('limit', 100)
        tags = tag_manager.get_all_tags(limit=limit)
        
        if not tags:
            return True, _get_success_message('tags_empty', language), {'count': 0, 'tags': []}
        
        # Sort by count descending
        tags_sorted = sorted(tags, key=lambda x: x.get('count', 0), reverse=True)
        
        data = {
            'count': len(tags_sorted),
            'tags': tags_sorted
        }
        
        return True, _get_success_message('tags_list', language, len(tags_sorted)), data
    
    except Exception as e:
        logger.error(f"Error executing tags: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e)), None


async def _execute_notes(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Execute notes operation"""
    try:
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            return False, _get_error_message('manager_not_found', language, 'note_manager'), None
        
        # Check if searching or listing
        query = params.get('query') or params.get('keyword')
        archive_id = params.get('archive_id')
        
        if archive_id:
            # Get notes for specific archive
            notes = note_manager.get_notes(archive_id)
            if not notes:
                return True, _get_success_message('no_notes_for_archive', language, archive_id), {'count': 0, 'notes': []}
            
            data = {
                'count': len(notes),
                'archive_id': archive_id,
                'notes': notes
            }
            return True, _get_success_message('notes_for_archive', language, archive_id, len(notes)), data
        
        elif query:
            # Search notes with optional limit
            limit = params.get('limit', 10)
            notes = note_manager.search_notes(query, limit=limit)
            if not notes:
                return True, _get_success_message('no_notes_search_results', language, query), {'count': 0, 'notes': []}
            
            data = {
                'count': len(notes),
                'query': query,
                'notes': notes
            }
            return True, _get_success_message('notes_search_results', language, len(notes), query), data
        
        else:
            # Get all notes with optional limit
            limit = params.get('limit', 100)
            notes = note_manager.get_all_notes(limit=limit)
            if not notes:
                return True, _get_success_message('no_notes_found', language), {'count': 0, 'notes': []}
            
            data = {
                'count': len(notes),
                'notes': notes
            }
            return True, _get_success_message('all_notes', language, len(notes)), data
    
    except Exception as e:
        logger.error(f"Error executing notes: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e)), None


async def _execute_review(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Execute review operation (random or summary)"""
    try:
        review_manager = context.bot_data.get('review_manager')
        if not review_manager:
            return False, _get_error_message('manager_not_found', language, 'review_manager'), None
        
        review_type = params.get('type', 'random')  # 'random' or 'summary'
        content_type = params.get('content_type')  # Optional: text/link/image/video/audio/document/ebook
        period = params.get('period', 'month')  # For summary: week/month/year
        limit = params.get('limit', 1)  # Number of random archives to return
        
        if review_type == 'random':
            # Get random archive(s) with optional content type filter
            if limit > 1:
                # Multiple random archives - use search to get random selection
                storage = context.bot_data.get('db_storage')
                if not storage:
                    return False, _get_error_message('manager_not_found', language, 'storage'), None
                
                # Get more archives than needed to filter out deleted ones
                archives = storage.search_archives(
                    content_type=content_type,
                    limit=limit * 3  # Get extra to account for filtering
                )
                
                # Filter out deleted archives
                archives = [a for a in archives if not a.get('deleted')]
                
                # Randomize the results
                import random
                random.shuffle(archives)
                
                # Limit to requested number
                archives = archives[:limit]
                
                if not archives:
                    return True, _get_success_message('no_archives', language), {'count': 0}
                
                data = {
                    'type': 'random',
                    'archives': archives,  # Note: plural for multiple
                    'count': len(archives)
                }
                if content_type:
                    data['content_type'] = content_type
                return True, _get_success_message('review_random', language), data
            else:
                # Single random archive
                archive = review_manager.get_random_archive(content_type=content_type)
                if not archive:
                    return True, _get_success_message('no_archives', language), {'count': 0}
                
                data = {
                    'type': 'random',
                    'archive': archive
                }
                if content_type:
                    data['content_type'] = content_type
                return True, _get_success_message('review_random', language), data
        
        elif review_type == 'summary':
            # Get activity summary with period
            summary = review_manager.get_activity_summary(period=period)
            data = {
                'type': 'summary',
                'period': period,
                'summary': summary
            }
            return True, _get_success_message('review_summary', language), data
        
        else:
            return False, _get_error_message('invalid_review_type', language), None
    
    except Exception as e:
        logger.error(f"Error executing review: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e)), None


def _get_success_message(msg_type: str, language: str, *args) -> str:
    """Get success message"""
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    
    # Determine language key
    lang_key = 'zh' if language.startswith('zh') else language[:2]
    
    # Define messages by type (lazy evaluation to avoid index errors)
    if msg_type == 'search_no_results':
        messages = {
            'zh': f"🔍 未找到包含「{args[0]}」的归档" if not is_traditional else f"🔍 未找到包含「{args[0]}」的歸檔",
            'en': f"🔍 No archives found containing '{args[0]}'",
            'ja': f"🔍 「{args[0]}」を含むアーカイブが見つかりませんでした",
            'ko': f"🔍 '{args[0]}'을 포함하는 아카이브를 찾을 수 없습니다",
            'es': f"🔍 No se encontraron archivos que contengan '{args[0]}'"
        }
    elif msg_type == 'search_results':
        messages = {
            'zh': f"🔍 找到 {args[0]} 个相关归档（关键词：{args[1]}）" if not is_traditional else f"🔍 找到 {args[0]} 個相關歸檔（關鍵詞：{args[1]}）",
            'en': f"🔍 Found {args[0]} related archives (keyword: {args[1]})",
            'ja': f"🔍 {args[0]} 件の関連アーカイブが見つかりました（キーワード：{args[1]}）",
            'ko': f"🔍 {args[0]}개의 관련 아카이브를 찾았습니다 (키워드: {args[1]})",
            'es': f"🔍 Se encontraron {args[0]} archivos relacionados (palabra clave: {args[1]})"
        }
    elif msg_type == 'stats':
        messages = {
            'zh': "📊 系统统计信息已获取" if not is_traditional else "📊 系統統計資訊已獲取",
            'en': "📊 System statistics retrieved",
            'ja': "📊 システム統計情報を取得しました",
            'ko': "📊 시스템 통계 정보를 가져왔습니다",
            'es': "📊 Estadísticas del sistema obtenidas"
        }
    elif msg_type == 'tags_empty':
        messages = {
            'zh': "🏷️ 暂无标签" if not is_traditional else "🏷️ 暫無標籤",
            'en': "🏷️ No tags yet",
            'ja': "🏷️ タグはまだありません",
            'ko': "🏷️ 아직 태그가 없습니다",
            'es': "🏷️ Aún no hay etiquetas"
        }
    elif msg_type == 'tags_list':
        messages = {
            'zh': f"🏷️ 共有 {args[0]} 个标签" if not is_traditional else f"🏷️ 共有 {args[0]} 個標籤",
            'en': f"🏷️ Total {args[0]} tags",
            'ja': f"🏷️ 合計 {args[0]} 個のタグ",
            'ko': f"🏷️ 총 {args[0]}개의 태그",
            'es': f"🏷️ Total {args[0]} etiquetas"
        }
    else:
        # Fallback for unknown message types
        return f"✅ Operation {msg_type} completed"
    
    return messages.get(lang_key, messages.get('en', '✅ Operation completed'))


def _get_error_message(error_type: str, language: str, *args) -> str:
    """Get error message"""
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    
    if error_type == 'missing_keyword':
        if language.startswith('zh'):
            return "❌ 缺少搜索关键词" if not is_traditional else "❌ 缺少搜尋關鍵詞"
        elif language == 'ja':
            return "❌ 検索キーワードがありません"
        elif language == 'ko':
            return "❌ 검색 키워드가 없습니다"
        elif language == 'es':
            return "❌ Falta palabra clave de búsqueda"
        else:
            return "❌ Missing search keyword"
    
    elif error_type == 'manager_not_found':
        manager_name = args[0] if args else 'unknown'
        if language.startswith('zh'):
            return f"❌ 系统模块未初始化：{manager_name}" if not is_traditional else f"❌ 系統模組未初始化：{manager_name}"
        elif language == 'ja':
            return f"❌ システムモジュールが初期化されていません：{manager_name}"
        elif language == 'ko':
            return f"❌ 시스템 모듈이 초기화되지 않았습니다: {manager_name}"
        elif language == 'es':
            return f"❌ Módulo del sistema no inicializado: {manager_name}"
        else:
            return f"❌ System module not initialized: {manager_name}"
    
    elif error_type == 'execution_error':
        error_msg = args[0] if args else 'unknown error'
        if language.startswith('zh'):
            return f"❌ 执行错误：{error_msg}" if not is_traditional else f"❌ 執行錯誤：{error_msg}"
        elif language == 'ja':
            return f"❌ 実行エラー：{error_msg}"
        elif language == 'ko':
            return f"❌ 실행 오류: {error_msg}"
        elif language == 'es':
            return f"❌ Error de ejecución: {error_msg}"
        else:
            return f"❌ Execution error: {error_msg}"
    
    elif error_type == 'unknown_operation':
        op_type = args[0] if args else 'unknown'
        if language.startswith('zh'):
            return f"❌ 未知的操作类型：{op_type}" if not is_traditional else f"❌ 未知的操作類型：{op_type}"
        elif language == 'ja':
            return f"❌ 不明な操作タイプ：{op_type}"
        elif language == 'ko':
            return f"❌ 알 수 없는 작업 유형: {op_type}"
        elif language == 'es':
            return f"❌ Tipo de operación desconocido: {op_type}"
        else:
            return f"❌ Unknown operation type: {op_type}"
    
    return "❌ Error"
