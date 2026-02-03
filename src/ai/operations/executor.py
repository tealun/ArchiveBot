"""
AI Action Executor

Executes confirmed AI operations safely.
Handles action execution after user confirmation from AI chat.
"""

import logging
from typing import Dict, Any, Tuple
from telegram.ext import ContextTypes
from .message_helper import (
    get_action_success_message,
    get_action_error_message
)

logger = logging.getLogger(__name__)


async def execute_confirmed_action(
    action_type: str,
    action_params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str = 'zh-CN'
) -> Tuple[bool, str]:
    """
    Execute confirmed AI action
    
    Args:
        action_type: Type of action (delete_archive, clear_trash, create_note, etc.)
        action_params: Action parameters
        context: Bot context
        language: User language code
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        logger.info(f"Executing confirmed action: {action_type} with params: {action_params}")
        
        # Log audit event
        from ...ai.chat_router import _log_audit_event
        
        # Delete archive (move to trash)
        if action_type == 'delete_archive':
            result = await _execute_delete_archive(action_params, context, language)
            _log_audit_event('write_confirmed', action_type, action_params, context, language, result[1])
            return result
        
        # Clear trash (permanently delete all)
        elif action_type == 'clear_trash':
            result = await _execute_clear_trash(context, language)
            _log_audit_event('write_confirmed', action_type, action_params, context, language, result[1])
            return result
        
        # Create note
        elif action_type == 'create_note':
            result = await _execute_create_note(action_params, context, language)
            _log_audit_event('write_confirmed', action_type, action_params, context, language, result[1])
            return result
        
        # Add tag to archive
        elif action_type == 'add_tag':
            result = await _execute_add_tag(action_params, context, language)
            _log_audit_event('write_confirmed', action_type, action_params, context, language, result[1])
            return result
        
        # Remove tag from archive
        elif action_type == 'remove_tag':
            result = await _execute_remove_tag(action_params, context, language)
            _log_audit_event('write_confirmed', action_type, action_params, context, language, result[1])
            return result
        
        # Toggle favorite
        elif action_type == 'toggle_favorite':
            result = await _execute_toggle_favorite(action_params, context, language)
            _log_audit_event('write_confirmed', action_type, action_params, context, language, result[1])
            return result
        
        # Unknown action type
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return False, _get_error_message('unknown_action', language, action_type)
    
    except Exception as e:
        logger.error(f"Error executing action {action_type}: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


async def _execute_delete_archive(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str]:
    """Execute delete archive action (move to trash)"""
    try:
        archive_id = params.get('archive_id')
        if not archive_id:
            return False, _get_error_message('missing_archive_id', language)
        
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            return False, _get_error_message('manager_not_found', language, 'trash_manager')
        
        # Move to trash
        success = trash_manager.move_to_trash(archive_id)
        
        if success:
            return True, _get_success_message('delete_archive', language, archive_id)
        else:
            return False, _get_error_message('delete_failed', language, archive_id)
    
    except Exception as e:
        logger.error(f"Error deleting archive: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


async def _execute_clear_trash(
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str]:
    """Execute clear trash action (permanent delete)"""
    try:
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            return False, _get_error_message('manager_not_found', language, 'trash_manager')
        
        # Clear trash
        count = trash_manager.empty_trash()
        
        return True, _get_success_message('clear_trash', language, count)
    
    except Exception as e:
        logger.error(f"Error clearing trash: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


async def _execute_create_note(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str]:
    """Execute create note action"""
    try:
        note_content = params.get('content')
        archive_id = params.get('archive_id')  # Optional: can be standalone note
        
        if not note_content:
            return False, _get_error_message('missing_content', language)
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            return False, _get_error_message('manager_not_found', language, 'note_manager')
        
        # Create note
        note_id = note_manager.add_note(
            content=note_content,
            archive_id=archive_id
        )
        
        if note_id:
            return True, _get_success_message('create_note', language, note_id)
        else:
            return False, _get_error_message('create_note_failed', language)
    
    except Exception as e:
        logger.error(f"Error creating note: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


async def _execute_add_tag(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str]:
    """Execute add tag action"""
    try:
        archive_id = params.get('archive_id')
        tag_name = params.get('tag_name')
        
        if not archive_id or not tag_name:
            return False, _get_error_message('missing_params', language)
        
        tag_manager = context.bot_data.get('tag_manager')
        if not tag_manager:
            return False, _get_error_message('manager_not_found', language, 'tag_manager')
        
        # Add tag
        success = tag_manager.add_tag_to_archive(archive_id, tag_name, tag_type='manual')
        
        if success:
            return True, _get_success_message('add_tag', language, archive_id, tag_name)
        else:
            return False, _get_error_message('add_tag_failed', language)
    
    except Exception as e:
        logger.error(f"Error adding tag: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


async def _execute_remove_tag(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str]:
    """Execute remove tag action"""
    try:
        archive_id = params.get('archive_id')
        tag_name = params.get('tag_name')
        
        if not archive_id or not tag_name:
            return False, _get_error_message('missing_params', language)
        
        tag_manager = context.bot_data.get('tag_manager')
        if not tag_manager:
            return False, _get_error_message('manager_not_found', language, 'tag_manager')
        
        # Remove tag
        success = tag_manager.remove_tag_from_archive(archive_id, tag_name)
        
        if success:
            return True, _get_success_message('remove_tag', language, archive_id, tag_name)
        else:
            return False, _get_error_message('remove_tag_failed', language)
    
    except Exception as e:
        logger.error(f"Error removing tag: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


async def _execute_toggle_favorite(
    params: Dict[str, Any],
    context: ContextTypes.DEFAULT_TYPE,
    language: str
) -> Tuple[bool, str]:
    """Execute toggle favorite action"""
    try:
        archive_id = params.get('archive_id')
        
        if not archive_id:
            return False, _get_error_message('missing_archive_id', language)
        
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            return False, _get_error_message('manager_not_found', language, 'db_storage')
        
        # Toggle favorite
        success = db_storage.toggle_favorite(archive_id)
        
        if success:
            # Check current favorite status
            archive = db_storage.get_archive(archive_id)
            is_favorite = archive.get('favorite', 0) if archive else 0
            return True, _get_success_message('toggle_favorite', language, archive_id, is_favorite)
        else:
            return False, _get_error_message('toggle_favorite_failed', language)
    
    except Exception as e:
        logger.error(f"Error toggling favorite: {e}", exc_info=True)
        return False, _get_error_message('execution_error', language, str(e))


# Message helper functions now imported from message_helper module
_get_success_message = get_action_success_message
_get_error_message = get_action_error_message
