"""
Bot commands implementation
Handles /start, /help, /search, /tags, /stats, /language
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.i18n import get_i18n
from ..utils.config import get_config
from ..utils.helpers import format_file_size
from ..core.search_engine import SearchEngine
from ..core.tag_manager import TagManager
from ..storage.database import DatabaseStorage
from ..ai.summarizer import get_ai_summarizer

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        config = get_config()
        
        # Set language from config
        i18n.set_language(config.language)
        
        welcome_msg = i18n.t('welcome')
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.HTML)
        
        logger.info(f"Start command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        help_msg = i18n.t('help')
        
        await update.message.reply_text(
            help_msg,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Help command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /search command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # Get search query
        query = ' '.join(context.args) if context.args else None
        
        if not query:
            await update.message.reply_text(i18n.t('search_no_keyword'))
            return
        
        # Get search engine from context
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        
        if not search_engine:
            await update.message.reply_text("Search engine not initialized")
            return
        
        # Send processing message
        processing_msg = await update.message.reply_text(i18n.t('processing'))
        
        # Perform search with pagination
        page_size = 10
        page = 0  # First page
        offset = page * page_size
        search_result = search_engine.search(query, limit=page_size, offset=offset)
        
        # Get total count for pagination
        total_count = search_result.get('total_count', 0)
        
        # Get database instance for checking status
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        
        # Format and send results (with HTML links and per-item keyboards)
        result_text, keyboards_per_item = search_engine.format_results(
            search_result, 
            with_links=True,
            db_instance=db
        )
        
        # Build final keyboard: only pagination buttons (no per-item buttons)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from urllib.parse import quote
        
        keyboard = []
        
        # 分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages > 1:
            nav_row = []
            encoded_query = quote(query)
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    i18n.t('button_previous_page'),
                    callback_data=f"search_page:{encoded_query}:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                i18n.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="search_noop"
            ))
            
            if (page + 1) * page_size < total_count:
                nav_row.append(InlineKeyboardButton(
                    i18n.t('button_next_page'),
                    callback_data=f"search_page:{encoded_query}:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        # 发送结果
        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_msg.edit_text(
                result_text, 
                parse_mode=ParseMode.HTML, 
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        else:
            await processing_msg.edit_text(result_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
        logger.info(f"Search command: query='{query}', results={search_result.get('count', 0)}")
        
    except Exception as e:
        logger.error(f"Error in search_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def tags_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tags command - 显示标签按钮矩阵
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        tag_manager: TagManager = context.bot_data.get('tag_manager')
        
        if not tag_manager:
            await update.message.reply_text("Tag manager not initialized")
            return
        
        # Get all tags (sorted by count descending)
        tags = tag_manager.get_all_tags(limit=100)
        
        if not tags:
            await update.message.reply_text(i18n.t('tags_empty'))
            return
        
        # 构建按钮矩阵（3列，分页显示）
        page = 0  # 当前页
        page_size = 30  # 每页30个标签
        
        # 获取当前页的标签
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_tags = tags[start_idx:end_idx]
        
        # 构建按钮
        keyboard = []
        row = []
        for i, tag in enumerate(page_tags):
            tag_name = tag.get('tag_name')
            count = tag.get('count', 0)
            
            # 按钮文本：标签名 (数量)
            button_text = f"#{tag_name} ({count})"
            # 回调数据：tag:标签名:页码
            callback_data = f"tag:{tag_name}:0"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            # 每3个按钮一行
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        # 添加最后一行（如果有）
        if row:
            keyboard.append(row)
        
        # 添加分页按钮
        nav_row = []
        total_pages = (len(tags) + page_size - 1) // page_size
        
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f"tags_page:{page-1}"))
        
        nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="tags_noop"))
        
        if end_idx < len(tags):
            nav_row.append(InlineKeyboardButton("➡️ 下一页", callback_data=f"tags_page:{page+1}"))
        
        if nav_row:
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = i18n.t('tags_button_list_header', count=len(tags))
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
        logger.info(f"Tags command executed: {len(tags)} tags, page {page}")
        
    except Exception as e:
        logger.error(f"Error in tags_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /stats command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        db_storage: DatabaseStorage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await update.message.reply_text("Database storage not initialized")
            return
        
        # Get stats from database
        stats = db_storage.db.get_stats()
        
        # Get database file size
        import os
        db_path = db_storage.db.db_path
        db_size = 0
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
        
        # Format stats
        total_archives = stats.get('total_archives', 0)
        total_tags = stats.get('total_tags', 0)
        total_size = format_file_size(stats.get('total_size', 0))
        db_size_formatted = format_file_size(db_size)
        last_archive = stats.get('last_archive', 'N/A')
        
        message = i18n.t(
            'stats',
            total_archives=total_archives,
            total_tags=total_tags,
            storage_used=total_size,
            db_size=db_size_formatted,
            last_archive=last_archive
        )
        
        await update.message.reply_text(message)
        
        logger.info(f"Stats command executed")
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /language command
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # Create language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("English", callback_data="lang_en"),
                InlineKeyboardButton("简体中文", callback_data="lang_zh-CN"),
            ],
            [
                InlineKeyboardButton("繁體中文", callback_data="lang_zh-TW"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            i18n.t('language_select'),
            reply_markup=reply_markup
        )
        
        logger.info(f"Language command executed")
        
    except Exception as e:
        logger.error(f"Error in language_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ai command - 显示AI功能状态
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        config = get_config()
        ai_config = config.ai
        
        status_text = i18n.t('ai_status_title')
        
        # 检查是否启用
        if ai_config.get('enabled', False):
            status_text += i18n.t('ai_status_enabled') + "\n"
            
            # 获取AI总结器
            summarizer = get_ai_summarizer(ai_config)
            
            if summarizer and summarizer.is_available():
                status_text += i18n.t('ai_status_available')
                
                api_config = ai_config.get('api', {})
                provider = api_config.get('provider', 'unknown')
                model = api_config.get('model', 'unknown')
                
                status_text += i18n.t('ai_status_config_title')
                status_text += i18n.t('ai_status_provider', provider=provider)
                status_text += i18n.t('ai_status_model', model=model)
                status_text += i18n.t('ai_status_max_tokens', max_tokens=api_config.get('max_tokens', 1000))
                status_text += i18n.t('ai_status_timeout', timeout=api_config.get('timeout', 30))
                
                status_text += i18n.t('ai_status_features_title')
                auto_summarize_status = '✅' if ai_config.get('auto_summarize') else '❌'
                auto_tags_status = '✅' if ai_config.get('auto_generate_tags') else '❌'
                status_text += i18n.t('ai_status_auto_summarize', status=auto_summarize_status)
                status_text += i18n.t('ai_status_auto_tags', status=auto_tags_status)
            else:
                status_text += i18n.t('ai_status_unavailable')
        else:
            status_text += i18n.t('ai_status_disabled')
            status_text += i18n.t('ai_status_enable_guide')
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"AI status command executed")
        
    except Exception as e:
        logger.error(f"Error in ai_status_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /notes command - 显示所有笔记列表
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # 获取note_manager
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await update.message.reply_text(i18n.t('note_manager_not_initialized'))
            return
        
        # 获取所有笔记（分页显示）
        page = 0
        page_size = 20
        results = note_manager.get_all_notes(limit=page_size, offset=page * page_size)
        
        if not results:
            await update.message.reply_text(i18n.t('notes_list_empty'))
            return
        
        # 构建输出
        result_text = i18n.t('notes_list_header', count=len(results)) + "\n\n"
        
        for note in results:
            # 笔记内容截断
            from ..utils.helpers import truncate_text
            content_preview = truncate_text(note['content'], 50)
            
            result_text += f"📝 {i18n.t('note_id')}: #{note['id']}\n"
            
            # 如果关联了归档，显示归档ID
            if note.get('archive_id'):
                result_text += f"📎 {i18n.t('archive')} #{note['archive_id']}\n"
            
            result_text += f"📅 {note['created_at']}\n"
            result_text += f"💬 {content_preview}\n\n"
        
        await update.message.reply_text(result_text)
        
        logger.info(f"Notes list command executed")
        
    except Exception as e:
        logger.error(f"Error in notes_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def trash_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /trash command - 管理垃圾箱
    
    Usage:
        /trash - 查看垃圾箱
        /trash restore <id> - 恢复归档
        /trash delete <id> - 永久删除
        /trash empty - 清空垃圾箱
        /trash empty <days> - 清空N天前的归档
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await update.message.reply_text(i18n.t('trash_manager_not_initialized'))
            return
        
        # 解析子命令
        if not context.args:
            # 查看垃圾箱
            items = trash_manager.list_trash()
            count = len(items)
            
            if count == 0:
                await update.message.reply_text(i18n.t('trash_empty'))
                return
            
            result_text = i18n.t('trash_list', count=count) + "\n\n"
            
            for item in items[:20]:  # 只显示前20条
                result_text += f"🗑️ ID: #{item['id']}\n"
                result_text += f"📝 {item['title']}\n"
                result_text += f"🏷️ {', '.join(item['tags'][:3])}{'...' if len(item['tags']) > 3 else ''}\n"
                result_text += f"🕐 {i18n.t('deleted_at')}: {item['deleted_at']}\n\n"
            
            if count > 20:
                result_text += i18n.t('trash_more', count=count-20)
            
            await update.message.reply_text(result_text)
            
        elif context.args[0] == 'restore':
            # 恢复归档
            if len(context.args) < 2:
                await update.message.reply_text(i18n.t('trash_restore_usage'))
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(i18n.t('invalid_archive_id'))
                return
            
            if trash_manager.restore_archive(archive_id):
                await update.message.reply_text(i18n.t('trash_restore_success', archive_id=archive_id))
            else:
                await update.message.reply_text(i18n.t('trash_restore_failed', archive_id=archive_id))
        
        elif context.args[0] == 'delete':
            # 永久删除
            if len(context.args) < 2:
                await update.message.reply_text(i18n.t('trash_delete_usage'))
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(i18n.t('invalid_archive_id'))
                return
            
            if trash_manager.delete_permanently(archive_id):
                await update.message.reply_text(i18n.t('trash_delete_success', archive_id=archive_id))
            else:
                await update.message.reply_text(i18n.t('trash_delete_failed', archive_id=archive_id))
        
        elif context.args[0] == 'empty':
            # 清空垃圾箱
            days_old = None
            if len(context.args) > 1:
                try:
                    days_old = int(context.args[1])
                except ValueError:
                    await update.message.reply_text(i18n.t('invalid_days'))
                    return
            
            count = trash_manager.empty_trash(days_old)
            
            if days_old:
                await update.message.reply_text(i18n.t('trash_empty_success_days', count=count, days=days_old))
            else:
                await update.message.reply_text(i18n.t('trash_empty_success', count=count))
        
        else:
            await update.message.reply_text(i18n.t('trash_invalid_command'))
        
        logger.info(f"Trash command executed: {' '.join(context.args) if context.args else 'list'}")
        
    except Exception as e:
        logger.error(f"Error in trash_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /export command - 导出数据
    
    Usage:
        /export - 导出为Markdown
        /export json - 导出为JSON
        /export csv - 导出为CSV
        /export tag <tag_name> [format] - 按标签导出
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        i18n = get_i18n()
        
        # 获取export_manager
        export_manager = context.bot_data.get('export_manager')
        if not export_manager:
            await update.message.reply_text(i18n.t('export_manager_not_initialized'))
            return
        
        # 发送处理中提示
        processing_msg = await update.message.reply_text(i18n.t('export_processing'))
        
        # 解析命令参数
        format_type = 'markdown'  # 默认格式
        tag_name = None
        
        if context.args:
            if context.args[0] == 'tag':
                # 按标签导出
                if len(context.args) < 2:
                    await processing_msg.edit_text(i18n.t('export_tag_usage'))
                    return
                tag_name = context.args[1]
                format_type = context.args[2] if len(context.args) > 2 else 'markdown'
            else:
                # 指定格式
                format_type = context.args[0].lower()
        
        # 验证格式
        if format_type not in ['markdown', 'json', 'csv', 'md']:
            await processing_msg.edit_text(i18n.t('export_invalid_format'))
            return
        
        # 导出数据
        if tag_name:
            # 按标签导出
            data = export_manager.export_archives_by_tag(tag_name, format_type)
            filename = f"archives_tag_{tag_name}"
        else:
            # 全量导出
            if format_type in ['markdown', 'md']:
                data = export_manager.export_to_markdown()
                format_type = 'markdown'
            elif format_type == 'json':
                data = export_manager.export_to_json()
            else:  # csv
                data = export_manager.export_to_csv()
            
            filename = "archives_export"
        
        if not data:
            await processing_msg.edit_text(i18n.t('export_failed'))
            return
        
        # 确定文件扩展名
        if format_type in ['markdown', 'md']:
            ext = 'md'
        elif format_type == 'json':
            ext = 'json'
        else:
            ext = 'csv'
        
        # 生成文件名（带时间戳）
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        full_filename = f"{filename}_{timestamp}.{ext}"
        
        # 发送文件
        from io import BytesIO
        file_data = BytesIO(data.encode('utf-8'))
        file_data.name = full_filename
        
        await update.message.reply_document(
            document=file_data,
            filename=full_filename,
            caption=i18n.t('export_success', filename=full_filename, size=len(data))
        )
        
        # 删除处理中提示
        await processing_msg.delete()
        
        logger.info(f"Export command executed: format={format_type}, tag={tag_name}, size={len(data)}")
        
    except Exception as e:
        logger.error(f"Error in export_command: {e}", exc_info=True)
        i18n = get_i18n()
        try:
            await update.message.reply_text(i18n.t('error_occurred', error=str(e)))
        except:
            pass


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /backup command - 备份与恢复
    
    Usage:
        /backup              - 查看备份列表
        /backup create [desc]- 创建备份，可附描述
        /backup restore <file> - 从备份恢复
        /backup delete <file>  - 删除备份
        /backup cleanup [keep] - 只保留最近N个（默认10）
        /backup status       - 查看数据库状态
    """
    try:
        i18n = get_i18n()
        backup_manager = context.bot_data.get('backup_manager')

        if not backup_manager:
            await update.message.reply_text(i18n.t('backup_manager_not_initialized'))
            return

        # 无参数 -> 列表
        if not context.args:
            backups = backup_manager.list_backups()
            if not backups:
                await update.message.reply_text(i18n.t('backup_none'))
                return

            lines = [i18n.t('backup_list_header', count=len(backups))]
            for b in backups[:10]:
                lines.append(i18n.t(
                    'backup_list_item',
                    filename=b.get('filename'),
                    created_at=b.get('created_at'),
                    size=b.get('size'),
                    description=b.get('description', '')
                ))
            if len(backups) > 10:
                lines.append(i18n.t('backup_list_more', count=len(backups) - 10))

            await update.message.reply_text('\n'.join(lines))
            return

        subcmd = context.args[0].lower()

        if subcmd == 'create':
            desc = ' '.join(context.args[1:]) if len(context.args) > 1 else ''
            result = backup_manager.create_backup(description=desc)
            if result:
                await update.message.reply_text(i18n.t('backup_created', filename=result))
            else:
                await update.message.reply_text(i18n.t('backup_create_failed'))
            return

        if subcmd == 'restore':
            if len(context.args) < 2:
                await update.message.reply_text(i18n.t('backup_restore_usage'))
                return
            filename = context.args[1]
            ok = backup_manager.restore_backup(filename)
            if ok:
                await update.message.reply_text(i18n.t('backup_restored', filename=filename))
            else:
                await update.message.reply_text(i18n.t('backup_restore_failed', filename=filename))
            return

        if subcmd == 'delete':
            if len(context.args) < 2:
                await update.message.reply_text(i18n.t('backup_delete_usage'))
                return
            filename = context.args[1]
            ok = backup_manager.delete_backup(filename)
            if ok:
                await update.message.reply_text(i18n.t('backup_deleted', filename=filename))
            else:
                await update.message.reply_text(i18n.t('backup_delete_failed', filename=filename))
            return

        if subcmd == 'cleanup':
            keep = 10
            if len(context.args) > 1:
                try:
                    keep = int(context.args[1])
                except ValueError:
                    await update.message.reply_text(i18n.t('backup_invalid_keep'))
                    return
            deleted = backup_manager.cleanup_old_backups(keep_count=keep)
            await update.message.reply_text(i18n.t('backup_cleanup_done', deleted=deleted, keep=keep))
            return

        if subcmd == 'status':
            stats = backup_manager.get_database_stats()
            if not stats:
                await update.message.reply_text(i18n.t('backup_status_failed'))
                return
            msg = i18n.t(
                'backup_status',
                size=stats.get('size', 0),
                archives=stats.get('archives_count', 0),
                notes=stats.get('notes_count', 0),
                deleted=stats.get('deleted_count', 0),
                last=stats.get('last_archive', 'N/A')
            )
            await update.message.reply_text(msg)
            return

        # 未知子命令
        await update.message.reply_text(i18n.t('backup_invalid_command'))

    except Exception as e:
        logger.error(f"Error in backup_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /review command - 活动回顾与统计
    
    Usage:
        /review              - 显示期间选择按钮
    """
    try:
        i18n = get_i18n()
        review_manager = context.bot_data.get('review_manager')

        if not review_manager:
            await update.message.reply_text(i18n.t('review_manager_not_initialized'))
            return

        # 显示期间选择按钮
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📅 {i18n.t('review_period_week')}",
                    callback_data='review:week'
                ),
                InlineKeyboardButton(
                    f"📅 {i18n.t('review_period_month')}",
                    callback_data='review:month'
                )
            ],
            [
                InlineKeyboardButton(
                    f"📅 {i18n.t('review_period_year')}",
                    callback_data='review:year'
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            i18n.t('review_usage'),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in review_command: {e}", exc_info=True)
        i18n = get_i18n()
        await update.message.reply_text(i18n.t('error_occurred', error=str(e)))
