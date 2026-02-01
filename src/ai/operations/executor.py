"""
AI Action Executor

Executes confirmed AI operations safely.
Handles action execution after user confirmation from AI chat.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from telegram.ext import ContextTypes

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


def _get_success_message(action: str, language: str, *args) -> str:
    """Get success message for action"""
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    
    if action == 'delete_archive':
        archive_id = args[0] if args else '?'
        if language.startswith('zh'):
            return f"✅ 已將歸檔 #{archive_id} 移至回收站" if is_traditional else f"✅ 已将归档 #{archive_id} 移至回收站"
        elif language == 'ja':
            return f"✅ アーカイブ #{archive_id} をゴミ箱に移動しました"
        elif language == 'ko':
            return f"✅ 아카이브 #{archive_id}를 휴지통으로 이동했습니다"
        elif language == 'es':
            return f"✅ Archivo #{archive_id} movido a la papelera"
        else:
            return f"✅ Archive #{archive_id} moved to trash"
    
    elif action == 'clear_trash':
        count = args[0] if args else 0
        if language.startswith('zh'):
            return f"✅ 已清空回收站，永久刪除 {count} 個歸檔" if is_traditional else f"✅ 已清空回收站，永久删除 {count} 个归档"
        elif language == 'ja':
            return f"✅ ゴミ箱をクリアし、{count} 件のアーカイブを完全に削除しました"
        elif language == 'ko':
            return f"✅ 휴지통을 비웠습니다. {count}개의 아카이브를 영구 삭제했습니다"
        elif language == 'es':
            return f"✅ Papelera vaciada, {count} archivos eliminados permanentemente"
        else:
            return f"✅ Trash cleared, {count} archives permanently deleted"
    
    elif action == 'create_note':
        note_id = args[0] if args else '?'
        if language.startswith('zh'):
            return f"✅ 已創建筆記 #{note_id}" if is_traditional else f"✅ 已创建笔记 #{note_id}"
        elif language == 'ja':
            return f"✅ ノート #{note_id} を作成しました"
        elif language == 'ko':
            return f"✅ 노트 #{note_id}를 생성했습니다"
        elif language == 'es':
            return f"✅ Nota #{note_id} creada"
        else:
            return f"✅ Note #{note_id} created"
    
    elif action == 'add_tag':
        archive_id = args[0] if len(args) > 0 else '?'
        tag_name = args[1] if len(args) > 1 else '?'
        if language.startswith('zh'):
            return f"✅ 已為歸檔 #{archive_id} 添加標籤 {tag_name}" if is_traditional else f"✅ 已为归档 #{archive_id} 添加标签 {tag_name}"
        elif language == 'ja':
            return f"✅ アーカイブ #{archive_id} にタグ {tag_name} を追加しました"
        elif language == 'ko':
            return f"✅ 아카이브 #{archive_id}에 태그 {tag_name}를 추가했습니다"
        elif language == 'es':
            return f"✅ Etiqueta {tag_name} añadida al archivo #{archive_id}"
        else:
            return f"✅ Tag {tag_name} added to archive #{archive_id}"
    
    elif action == 'remove_tag':
        archive_id = args[0] if len(args) > 0 else '?'
        tag_name = args[1] if len(args) > 1 else '?'
        if language.startswith('zh'):
            return f"✅ 已從歸檔 #{archive_id} 移除標籤 {tag_name}" if is_traditional else f"✅ 已从归档 #{archive_id} 移除标签 {tag_name}"
        elif language == 'ja':
            return f"✅ アーカイブ #{archive_id} からタグ {tag_name} を削除しました"
        elif language == 'ko':
            return f"✅ 아카이브 #{archive_id}에서 태그 {tag_name}를 제거했습니다"
        elif language == 'es':
            return f"✅ Etiqueta {tag_name} eliminada del archivo #{archive_id}"
        else:
            return f"✅ Tag {tag_name} removed from archive #{archive_id}"
    
    elif action == 'toggle_favorite':
        archive_id = args[0] if len(args) > 0 else '?'
        is_favorite = args[1] if len(args) > 1 else 0
        status = '精選' if is_favorite else '取消精選'
        status_en = 'favorited' if is_favorite else 'unfavorited'
        if language.startswith('zh'):
            status_tw = '精選' if is_favorite else '取消精選'
            status_cn = '精选' if is_favorite else '取消精选'
            return f"✅ 已{status_tw}歸檔 #{archive_id}" if is_traditional else f"✅ 已{status_cn}归档 #{archive_id}"
        elif language == 'ja':
            status_ja = 'お気に入りに追加' if is_favorite else 'お気に入りから削除'
            return f"✅ アーカイブ #{archive_id} を{status_ja}しました"
        elif language == 'ko':
            status_ko = '즐겨찾기에 추가' if is_favorite else '즐겨찾기에서 제거'
            return f"✅ 아카이브 #{archive_id}를 {status_ko}했습니다"
        elif language == 'es':
            status_es = 'marcado como favorito' if is_favorite else 'desmarcado como favorito'
            return f"✅ Archivo #{archive_id} {status_es}"
        else:
            return f"✅ Archive #{archive_id} {status_en}"
    
    return "✅ Operation completed"


def _get_error_message(error_type: str, language: str, *args) -> str:
    """Get error message"""
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    
    if error_type == 'unknown_action':
        action_type = args[0] if args else 'unknown'
        if language.startswith('zh'):
            return f"❌ 未知的操作類型：{action_type}" if is_traditional else f"❌ 未知的操作类型：{action_type}"
        elif language == 'ja':
            return f"❌ 不明な操作タイプ：{action_type}"
        elif language == 'ko':
            return f"❌ 알 수 없는 작업 유형: {action_type}"
        elif language == 'es':
            return f"❌ Tipo de operación desconocido: {action_type}"
        else:
            return f"❌ Unknown action type: {action_type}"
    
    elif error_type == 'missing_archive_id':
        if language.startswith('zh'):
            return "❌ 缺少歸檔ID參數" if is_traditional else "❌ 缺少归档ID参数"
        elif language == 'ja':
            return "❌ アーカイブIDパラメータが不足しています"
        elif language == 'ko':
            return "❌ 아카이브 ID 매개변수가 없습니다"
        elif language == 'es':
            return "❌ Falta el parámetro de ID de archivo"
        else:
            return "❌ Missing archive ID parameter"
    
    elif error_type == 'missing_content':
        if language.startswith('zh'):
            return "❌ 缺少內容參數" if is_traditional else "❌ 缺少内容参数"
        elif language == 'ja':
            return "❌ コンテンツパラメータが不足しています"
        elif language == 'ko':
            return "❌ 콘텐츠 매개변수가 없습니다"
        elif language == 'es':
            return "❌ Falta el parámetro de contenido"
        else:
            return "❌ Missing content parameter"
    
    elif error_type == 'missing_params':
        if language.startswith('zh'):
            return "❌ 缺少必需參數" if is_traditional else "❌ 缺少必需参数"
        elif language == 'ja':
            return "❌ 必須パラメータが不足しています"
        elif language == 'ko':
            return "❌ 필수 매개변수가 없습니다"
        elif language == 'es':
            return "❌ Faltan parámetros requeridos"
        else:
            return "❌ Missing required parameters"
    
    elif error_type == 'manager_not_found':
        manager_name = args[0] if args else 'unknown'
        if language.startswith('zh'):
            return f"❌ 未找到管理器：{manager_name}" if is_traditional else f"❌ 未找到管理器：{manager_name}"
        elif language == 'ja':
            return f"❌ マネージャが見つかりません：{manager_name}"
        elif language == 'ko':
            return f"❌ 관리자를 찾을 수 없습니다: {manager_name}"
        elif language == 'es':
            return f"❌ Gestor no encontrado: {manager_name}"
        else:
            return f"❌ Manager not found: {manager_name}"
    
    elif error_type == 'execution_error':
        error_msg = args[0] if args else 'unknown error'
        if language.startswith('zh'):
            return f"❌ 執行錯誤：{error_msg}" if is_traditional else f"❌ 执行错误：{error_msg}"
        elif language == 'ja':
            return f"❌ 実行エラー：{error_msg}"
        elif language == 'ko':
            return f"❌ 실행 오류: {error_msg}"
        elif language == 'es':
            return f"❌ Error de ejecución: {error_msg}"
        else:
            return f"❌ Execution error: {error_msg}"
    
    elif error_type in ['delete_failed', 'create_note_failed', 'add_tag_failed', 
                        'remove_tag_failed', 'toggle_favorite_failed']:
        if language.startswith('zh'):
            return "❌ 操作失敗" if is_traditional else "❌ 操作失败"
        elif language == 'ja':
            return "❌ 操作に失敗しました"
        elif language == 'ko':
            return "❌ 작업 실패"
        elif language == 'es':
            return "❌ Operación fallida"
        else:
            return "❌ Operation failed"
    
    return "❌ Error"
