"""
Shared message helper for AI operations
Consolidates duplicate message functions from executor.py and safe_executor.py
"""

def is_traditional_chinese(language: str) -> bool:
    """Check if language is traditional Chinese variant"""
    return language in ['zh-TW', 'zh-HK', 'zh-MO']


def get_action_success_message(action: str, language: str, *args) -> str:
    """
    Get success message for action operations
    Used by executor.py for action-based operations
    """
    is_traditional = is_traditional_chinese(language)
    
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
            status_en = 'favorited' if is_favorite else 'unfavorited'
            return f"✅ Archive #{archive_id} {status_en}"
    
    return "✅ Operation completed"


def get_query_success_message(msg_type: str, language: str, *args) -> str:
    """
    Get success message for query operations
    Used by safe_executor.py for read-only query operations
    """
    is_traditional = is_traditional_chinese(language)
    lang_key = 'zh' if language.startswith('zh') else language[:2]
    
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
        return f"✅ Operation {msg_type} completed"
    
    return messages.get(lang_key, messages.get('en', '✅ Operation completed'))


def get_action_error_message(error_type: str, language: str, *args) -> str:
    """
    Get error message for action operations
    Used by executor.py
    """
    is_traditional = is_traditional_chinese(language)
    
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


def get_query_error_message(error_type: str, language: str, *args) -> str:
    """
    Get error message for query operations
    Used by safe_executor.py
    """
    is_traditional = is_traditional_chinese(language)
    
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
