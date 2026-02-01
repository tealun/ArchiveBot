"""
Language callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)


@with_language_context
async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle language selection callback
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        callback_data = query.data
        
        if callback_data.startswith('lang_'):
            language = callback_data[5:]  # Remove 'lang_' prefix
            
            # Set language via i18n first (validate language)
            from ...utils.i18n import get_i18n
            i18n = get_i18n()
            
            if i18n.set_language(language):
                # Update config
                config = get_config()
                config.set('bot.language', language)
                config.save()
                # Update current language context using property setter
                lang_ctx.language = language
                
                # 同步更新用户的命令菜单语言
                try:
                    from telegram import BotCommand, BotCommandScopeChat
                    
                    # 定义命令列表（根据语言）
                    if language in ['zh-CN', 'zh-TW']:
                        # 中文命令
                        commands = [
                            BotCommand("start", "开始使用"),
                            BotCommand("help", "查看帮助"),
                            BotCommand("search", "搜索归档 (简写: /s)"),
                            BotCommand("note", "添加笔记 (简写: /n)"),
                            BotCommand("notes", "查看笔记"),
                            BotCommand("tags", "标签列表 (简写: /t)"),
                            BotCommand("stats", "统计信息 (简写: /st)"),
                            BotCommand("setting", "系统配置 (简写: /set)"),
                            BotCommand("review", "存档回顾"),
                            BotCommand("trash", "垃圾箱"),
                            BotCommand("export", "导出数据"),
                            BotCommand("backup", "备份管理"),
                            BotCommand("ai", "AI状态"),
                            BotCommand("language", "切换语言 (简写: /la)"),
                        ]
                        telegram_lang = "zh"  # Telegram 使用 zh 作为中文语言代码
                    elif language == 'ja':
                        # 日语命令
                        commands = [
                            BotCommand("start", "ボット初期化"),
                            BotCommand("help", "ヘルプ表示"),
                            BotCommand("search", "アーカイブ検索 (/s)"),
                            BotCommand("note", "ノート追加 (/n)"),
                            BotCommand("notes", "ノート表示"),
                            BotCommand("tags", "タグ一覧 (/t)"),
                            BotCommand("stats", "統計情報 (/st)"),
                            BotCommand("setting", "システム設定 (/set)"),
                            BotCommand("review", "アーカイブレビュー"),
                            BotCommand("trash", "ゴミ箱"),
                            BotCommand("export", "データエクスポート"),
                            BotCommand("backup", "バックアップ管理"),
                            BotCommand("ai", "AIステータス"),
                            BotCommand("language", "言語変更 (/la)"),
                        ]
                        telegram_lang = "ja"
                    elif language == 'ko':
                        # 韩语命令
                        commands = [
                            BotCommand("start", "봇 초기화"),
                            BotCommand("help", "도움말 표시"),
                            BotCommand("search", "아카이브 검색 (/s)"),
                            BotCommand("note", "노트 추가 (/n)"),
                            BotCommand("notes", "노트 표시"),
                            BotCommand("tags", "태그 목록 (/t)"),
                            BotCommand("stats", "통계 표시 (/st)"),
                            BotCommand("setting", "시스템 설정 (/set)"),
                            BotCommand("review", "아카이브 리뷰"),
                            BotCommand("trash", "휴지통"),
                            BotCommand("export", "데이터 내보내기"),
                            BotCommand("backup", "백업 관리"),
                            BotCommand("ai", "AI 상태"),
                            BotCommand("language", "언어 변경 (/la)"),
                        ]
                        telegram_lang = "ko"
                    elif language == 'es':
                        # 西班牙语命令
                        commands = [
                            BotCommand("start", "Inicializar bot"),
                            BotCommand("help", "Mostrar ayuda"),
                            BotCommand("search", "Buscar archivos (/s)"),
                            BotCommand("note", "Añadir nota (/n)"),
                            BotCommand("notes", "Ver notas"),
                            BotCommand("tags", "Lista de etiquetas (/t)"),
                            BotCommand("stats", "Mostrar estadísticas (/st)"),
                            BotCommand("setting", "Configuración (/set)"),
                            BotCommand("review", "Revisar archivos"),
                            BotCommand("trash", "Papelera"),
                            BotCommand("export", "Exportar datos"),
                            BotCommand("backup", "Gestión de copias"),
                            BotCommand("ai", "Estado de IA"),
                            BotCommand("language", "Cambiar idioma (/la)"),
                        ]
                        telegram_lang = "es"
                    else:
                        # 英文命令
                        commands = [
                            BotCommand("start", "Start bot"),
                            BotCommand("help", "Show help"),
                            BotCommand("search", "Search archives (/s)"),
                            BotCommand("note", "Add note (/n)"),
                            BotCommand("notes", "View notes"),
                            BotCommand("tags", "List tags (/t)"),
                            BotCommand("stats", "Show statistics (/st)"),
                            BotCommand("setting", "System settings (/set)"),
                            BotCommand("review", "Review archives"),
                            BotCommand("trash", "Trash bin"),
                            BotCommand("export", "Export data"),
                            BotCommand("backup", "Backup management"),
                            BotCommand("ai", "AI status"),
                            BotCommand("language", "Change language (/la)"),
                        ]
                        telegram_lang = "en"
                    
                    # 为当前用户的私聊设置命令菜单
                    user_id = update.effective_user.id
                    scope = BotCommandScopeChat(chat_id=user_id)
                    
                    await context.bot.set_my_commands(
                        commands=commands,
                        scope=scope,
                        language_code=telegram_lang
                    )
                    
                    logger.info(f"Updated command menu to {telegram_lang} for user {user_id}")
                except Exception as menu_error:
                    logger.warning(f"Failed to update command menu: {menu_error}")
                    # 不影响语言切换主流程
                
                # Send confirmation
                await query.edit_message_text(lang_ctx.t('language_changed'))
                
                logger.info(f"Language changed to: {language}")
            else:
                await query.edit_message_text(f"Unsupported language: {language}")
        
    except Exception as e:
        logger.error(f"Error handling language callback: {e}", exc_info=True)
        try:
            await query.edit_message_text(f"Error: {e}")
        except Exception as edit_err:
            logger.debug(f"Failed to edit message with error: {edit_err}")
