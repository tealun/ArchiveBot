"""
AI Safe Operation Executor

Executes safe read-only operations directly without user confirmation.
Phase 1: Search, stats, tags, notes, review (read-only operations)
"""

import logging
from typing import Dict, Any, Optional, Tuple
from telegram.ext import ContextTypes
from .message_helper import (
    get_query_success_message,
    get_query_error_message
)

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


# Message helper functions now imported from message_helper module
_get_success_message = get_query_success_message
_get_error_message = get_query_error_message
