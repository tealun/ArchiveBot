"""
Callback query handlers
Handles button clicks and inline keyboard callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.language_context import with_language_context, get_language_context
from ..utils.config import get_config
from ..core.tag_manager import TagManager
from ..core.search_engine import SearchEngine
from ..utils.helpers import truncate_text, format_datetime, get_content_type_emoji

logger = logging.getLogger(__name__)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    统一处理所有callback query
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        lang_ctx = get_language_context(update, context)
        callback_data = query.data
        
        # 路由到具体处理函数
        if callback_data.startswith('lang_'):
            await handle_language_callback(update, context)
        elif callback_data.startswith('tag:'):
            await handle_tag_callback(update, context)
        elif callback_data.startswith('tags_page:'):
            await handle_tags_page_callback(update, context)
        elif callback_data == 'tags_noop':
            # 不做任何操作（页码显示按钮）
            pass
        elif callback_data.startswith('tag_list:'):
            await handle_tag_list_page_callback(update, context)
        elif callback_data.startswith('search_page:'):
            await handle_search_page_callback(update, context)
        elif callback_data == 'search_noop':
            # 不做任何操作（页码显示按钮）
            pass
        elif callback_data.startswith('ai_view:'):
            await handle_ai_view_callback(update, context)
        elif callback_data.startswith('delete:'):
            await handle_delete_callback(update, context)
        elif callback_data.startswith('trash_restore:'):
            await handle_trash_restore_callback(update, context)
        elif callback_data.startswith('trash_delete:'):
            await handle_trash_delete_callback(update, context)
        elif callback_data.startswith('review:'):
            await handle_review_callback(update, context)
        elif callback_data.startswith('note:'):
            await handle_note_callback(update, context)
        elif callback_data.startswith('note_add:'):
            await handle_note_add_callback(update, context)
        elif callback_data.startswith('note_edit:'):
            await handle_note_edit_callback(update, context)
        elif callback_data.startswith('note_modify:'):
            await handle_note_modify_callback(update, context)
        elif callback_data.startswith('note_append:'):
            await handle_note_append_callback(update, context)
        elif callback_data.startswith('note_share:'):
            await handle_note_share_callback(update, context)
        elif callback_data.startswith('note_delete:'):
            await handle_note_delete_callback(update, context)
        elif callback_data == 'note_close':
            # 关闭笔记查看窗口
            await query.message.delete()
            await query.answer(lang_ctx.t('callback_closed'))
        elif callback_data.startswith('short_text:'):
            await handle_short_text_intent_callback(update, context)
        elif callback_data.startswith('refine_note:'):
            await handle_refine_note_callback(update, context)
        elif callback_data.startswith('fav:'):
            await handle_favorite_callback(update, context)
        elif callback_data.startswith('forward:'):
            await handle_forward_callback(update, context)
        elif callback_data == 'noop':
            # 不做任何操作（日期显示按钮）
            pass
        else:
            logger.warning(f"Unknown callback_data: {callback_data}")
    
    except Exception as e:
        logger.error(f"Error handling callback query: {e}", exc_info=True)


@with_language_context
async def handle_tag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理标签点击 - 显示该标签的内容列表
    
    Callback data format: tag:标签名:页码
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析: tag:tag_name:page
        parts = callback_data.split(':', 2)
        tag_name = parts[1]
        page = int(parts[2]) if len(parts) > 2 else 0
        
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        if not search_engine:
            await query.edit_message_text("Search engine not initialized")
            return
        
        # 搜索该标签的内容
        page_size = 10
        search_result = search_engine.search(
            f"#{tag_name}",
            limit=page_size,
            offset=page * page_size
        )
        
        if search_result.get('count', 0) == 0:
            await query.edit_message_text(lang_ctx.t('callback_tag_no_content', tag=tag_name))
            return
        
        # 使用MessageBuilder统一格式化列表
        from ..utils.message_builder import MessageBuilder
        
        # 获取数据库实例用于查询状态
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        
        archives = search_result.get('results', [])
        
        # 添加tags字段（如果没有）
        for archive in archives:
            if 'tags' not in archive:
                tag_manager = context.bot_data.get('tag_manager')
                if tag_manager:
                    archive['tags'] = tag_manager.get_archive_tags(archive.get('id'))
                else:
                    archive['tags'] = []
        
        results_text = MessageBuilder.format_archive_list(
            archives,
            lang_ctx,
            db_instance=db,
            with_links=True
        )
        
        # 获取总数
        total_count = search_result.get('total_count', search_result.get('count', 0))
        
        message = lang_ctx.t('callback_tag_header', tag=tag_name) + f"\n\n{results_text}"
        
        # 构建按钮布局：只包含分页和返回按钮
        keyboard = []
        
        # 构建分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        # 只有多于1页时才显示分页按钮
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"tag:{tag_name}:{page-1}"
                ))
            
            # 显示当前页码
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="tags_noop"
            ))
            
            if page + 1 < total_pages:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"tag:{tag_name}:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        # 返回按钮
        keyboard.append([InlineKeyboardButton(
            lang_ctx.t('button_back_to_tags'),
            callback_data="tags_page:0"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error handling tag callback: {e}", exc_info=True)


@with_language_context
async def handle_tags_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理标签列表分页
    
    Callback data format: tags_page:页码
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析页码
        page = int(callback_data.split(':')[1])
        
        tag_manager: TagManager = context.bot_data.get('tag_manager')
        if not tag_manager:
            await query.edit_message_text("Tag manager not initialized")
            return
        
        # 获取所有标签
        tags = tag_manager.get_all_tags(limit=100)
        
        if not tags:
            await query.edit_message_text("暂无标签")
            return
        
        # 构建按钮矩阵
        page_size = 30
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_tags = tags[start_idx:end_idx]
        
        keyboard = []
        row = []
        for i, tag in enumerate(page_tags):
            tag_name = tag.get('tag_name')
            count = tag.get('count', 0)
            
            button_text = f"#{tag_name} ({count})"
            callback_data = f"tag:{tag_name}:0"
            
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        # 分页按钮 - 只在多页时显示
        total_pages = (len(tags) + page_size - 1) // page_size
        
        # 只有多于1页时才显示分页按钮
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"tags_page:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="tags_noop"
            ))
            
            if end_idx < len(tags):
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"tags_page:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = lang_ctx.t('tags_button_list_header', count=len(tags))
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error handling tags page callback: {e}", exc_info=True)


async def handle_tag_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle tag list pagination
    
    Callback data format: tag_list:page
    """
    await handle_tags_page_callback(update, context)


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
            
            # Set language via config and update context
            config = get_config()
            if config.set('bot.language', language):
                config.save()
                # Update current language context
                lang_ctx.set_language(language)
                
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
                            BotCommand("note", "添加笔记"),
                            BotCommand("notes", "查看笔记"),
                            BotCommand("tags", "标签列表 (简写: /t)"),
                            BotCommand("stats", "统计信息 (简写: /st)"),
                            BotCommand("review", "存档回顾"),
                            BotCommand("trash", "垃圾箱"),
                            BotCommand("export", "导出数据"),
                            BotCommand("backup", "备份管理"),
                            BotCommand("ai", "AI状态"),
                            BotCommand("language", "切换语言 (简写: /lang)"),
                        ]
                        telegram_lang = "zh"  # Telegram 使用 zh 作为中文语言代码
                    else:
                        # 英文命令
                        commands = [
                            BotCommand("start", "Start bot"),
                            BotCommand("help", "Show help"),
                            BotCommand("search", "Search archives (/s)"),
                            BotCommand("note", "Add note"),
                            BotCommand("notes", "View notes"),
                            BotCommand("tags", "List tags (/t)"),
                            BotCommand("stats", "Show statistics (/st)"),
                            BotCommand("review", "Review archives"),
                            BotCommand("trash", "Trash bin"),
                            BotCommand("export", "Export data"),
                            BotCommand("backup", "Backup management"),
                            BotCommand("ai", "AI status"),
                            BotCommand("language", "Change language (/lang)"),
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
        except:
            pass


async def handle_tag_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle tag list pagination
    
    Callback data format: tag_list:page
    """
    await handle_tags_page_callback(update, context)


@with_language_context
async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理搜索结果分页
    
    Callback data format: search_page:encoded_query:page
    """
    from ..core.search_engine import SearchEngine
    from ..utils.helpers import truncate_text
    from urllib.parse import unquote, quote
    from telegram.constants import ParseMode
    
    query = update.callback_query
    
    try:
        # 解析 callback data: search_page:encoded_query:page
        parts = query.data.split(':', 2)
        if len(parts) != 3:
            await query.answer("Invalid callback data", show_alert=True)
            return
        
        encoded_query = parts[1]
        page = int(parts[2])
        search_query = unquote(encoded_query)
        
        # Get search engine
        search_engine: SearchEngine = context.bot_data.get('search_engine')
        if not search_engine:
            await query.answer("Search engine not initialized", show_alert=True)
            return
        
        # Perform search
        page_size = 10
        offset = page * page_size
        search_result = search_engine.search(search_query, limit=page_size, offset=offset)
        
        # Get total count
        total_count = search_result.get('total_count', 0)
        
        # 获取数据库实例
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        
        # Format results (第二个返回值现在是空列表)
        result_text, _ = search_engine.format_results(search_result, with_links=True, db_instance=db)
        
        # Build keyboard: 只包含分页按钮（状态信息已内联在文本中）
        keyboard = []
        
        # 分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"search_page:{encoded_query}:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="search_noop"
            ))
            
            if (page + 1) * page_size < total_count:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"search_page:{encoded_query}:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        # 更新消息
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        await query.answer()
        await query.edit_message_text(
            result_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        
        logger.info(f"Search page callback: query='{search_query}', page={page}")
        
    except Exception as e:
        logger.error(f"Error handling search page callback: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)}", show_alert=True)


@with_language_context
async def handle_ai_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle AI analysis view callback
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # Parse callback data: ai_view:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # Get database storage
        from ..storage.database import DatabaseStorage
        db_storage: DatabaseStorage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await query.answer("Database not available", show_alert=True)
            return
        
        # Get archive
        archive = db_storage.get_archive(archive_id)
        
        if not archive:
            await query.answer("Archive not found", show_alert=True)
            return
        
        # Get AI data
        ai_summary = archive.get('ai_summary', '')
        ai_key_points_json = archive.get('ai_key_points', '')
        ai_category = archive.get('ai_category', '')
        
        # Parse key points JSON
        ai_key_points = []
        if ai_key_points_json:
            try:
                import json
                ai_key_points = json.loads(ai_key_points_json)
            except:
                pass
        
        # Build AI analysis message
        title = archive.get('title', 'Untitled')
        ai_msg = f"📚 <b>{title}</b>\n\n🤖 <b>AI智能分析：</b>\n"
        
        if ai_category:
            ai_msg += f"\n📁 <b>分类：</b>{ai_category}"
        
        if ai_summary:
            ai_msg += f"\n\n📝 <b>摘要：</b>{ai_summary}"
        
        if ai_key_points:
            ai_msg += "\n\n🔑 <b>关键点：</b>"
            for i, point in enumerate(ai_key_points[:3], 1):
                ai_msg += f"\n  {i}. {point}"
        
        if not (ai_summary or ai_key_points or ai_category):
            ai_msg = "该归档暂无AI分析数据"
        
        # Send as new message
        await query.answer()
        await query.message.reply_text(ai_msg, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in AI view callback: {e}", exc_info=True)
        await query.answer("Error showing AI analysis", show_alert=True)


@with_language_context
async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理删除归档（移动到垃圾箱）
    
    Callback data format: delete:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 移动到垃圾箱
        if trash_manager.move_to_trash(archive_id):
            await query.edit_message_text(lang_ctx.t('archive_moved_to_trash', archive_id=archive_id))
        else:
            await query.edit_message_text(lang_ctx.t('archive_delete_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} moved to trash via callback")
        
    except Exception as e:
        logger.error(f"Error handling delete callback: {e}", exc_info=True)


@with_language_context
async def handle_trash_restore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理恢复归档
    
    Callback data format: trash_restore:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 恢复归档
        if trash_manager.restore_archive(archive_id):
            await query.edit_message_text(lang_ctx.t('trash_restore_success', archive_id=archive_id))
        else:
            await query.edit_message_text(lang_ctx.t('trash_restore_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} restored from trash via callback")
        
    except Exception as e:
        logger.error(f"Error handling restore callback: {e}", exc_info=True)


@with_language_context
async def handle_trash_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理永久删除归档
    
    Callback data format: trash_delete:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 永久删除
        if trash_manager.delete_permanently(archive_id):
            await query.edit_message_text(lang_ctx.t('trash_delete_success', archive_id=archive_id))
        else:
            await query.edit_message_text(lang_ctx.t('trash_delete_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} permanently deleted via callback")
        
    except Exception as e:
        logger.error(f"Error handling permanent delete callback: {e}", exc_info=True)


@with_language_context
async def handle_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理回顾统计按钮点击
    
    Callback data format: review:period (week/month/year) or review:back
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析: review:period
        parts = callback_data.split(':', 1)
        period = parts[1] if len(parts) > 1 else 'month'
        
        # 返回选择菜单
        if period == 'back':
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"📅 {lang_ctx.t('review_period_week')}",
                        callback_data='review:week'
                    ),
                    InlineKeyboardButton(
                        f"📅 {lang_ctx.t('review_period_month')}",
                        callback_data='review:month'
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"📅 {lang_ctx.t('review_period_year')}",
                        callback_data='review:year'
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                lang_ctx.t('review_usage'),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        if period not in ['week', 'month', 'year']:
            await query.edit_message_text(lang_ctx.t('review_invalid_period'))
            return
        
        review_manager = context.bot_data.get('review_manager')
        if not review_manager:
            await query.edit_message_text(lang_ctx.t('review_manager_not_initialized'))
            return
        
        # 显示处理中
        await query.edit_message_text(lang_ctx.t('processing'))
        
        # 生成报告
        report = review_manager.build_report(period=period, include_random=True)
        
        if not report or report['totals']['archives'] == 0:
            await query.edit_message_text(lang_ctx.t('review_no_data'))
            return
        
        # 构建消息
        period_name = lang_ctx.t(f'review_period_{period}')
        lines = [lang_ctx.t('review_header', period=period_name)]
        
        # 统计概览
        totals = report['totals']
        lines.append(lang_ctx.t(
            'review_totals',
            archives=totals['archives'],
            deleted=totals['deleted'],
            notes=totals['notes'],
            active_days=report.get('active_days', 0),
            days=report.get('days', 30)
        ))
        
        # 每日趋势（显示前10天）
        trend_data = report.get('trend', [])
        if trend_data:
            trend_lines = []
            for item in trend_data[:10]:
                date = item.get('date', '')
                count = item.get('count', 0)
                bar = '█' * min(count, 20)  # 简单条形图
                trend_lines.append(f"{date}: {bar} {count}")
            if trend_lines:
                lines.append(lang_ctx.t('review_trend', trend='\n'.join(trend_lines)))
        
        # 热门标签（Top 10）
        top_tags = report.get('top_tags', [])
        if top_tags:
            tag_lines = []
            for tag_item in top_tags[:10]:
                tag_name = tag_item.get('tag_name', '')
                tag_count = tag_item.get('count', 0)
                tag_lines.append(f"#{tag_name} ({tag_count})")
            if tag_lines:
                lines.append(lang_ctx.t('review_top_tags', tags='\n'.join(tag_lines)))
        
        # 随机回顾
        random_archive = report.get('random_archive')
        if random_archive:
            archive_id = random_archive.get('id')
            title = random_archive.get('title') or random_archive.get('content', '')[:50]
            tags = report.get('random_tags', [])
            tags_str = ' '.join(f'#{t}' for t in tags) if tags else lang_ctx.t('tags_empty')
            created_at = random_archive.get('created_at', 'N/A')
            
            # 构建标题链接（使用HTML格式，和搜索结果一致）
            storage_path = random_archive.get('storage_path')
            storage_type = random_archive.get('storage_type')
            title_display = title
            
            if storage_path and storage_type == 'telegram':
                # 解析 storage_path: 可能是 "message_id" 或 "channel_id:message_id" 或 "channel_id:message_id:file_id"
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    # 格式: channel_id:message_id[:file_id]
                    channel_id_str = parts[0].replace('-100', '')  # 移除-100前缀
                    message_id = parts[1]
                else:
                    # 格式: message_id（需要从配置获取channel_id）
                    from ...utils.config import get_config
                    config = get_config()
                    channel_id_str = str(config.telegram_channel_id).replace('-100', '')
                    message_id = storage_path
                
                file_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                # 使用HTML格式的链接（和搜索结果一致）
                title_display = f"<a href='{file_link}'>{title}</a>"
            
            # 获取数据库实例检查状态
            db_storage = context.bot_data.get('db_storage')
            db = db_storage.db if db_storage else None
            
            # 检查精选和笔记状态
            is_favorite = db.is_favorite(archive_id) if db and archive_id else False
            has_notes = db.has_notes(archive_id) if db and archive_id else False
            
            # 构建状态图标（按照统一格式）
            fav_icon = "❤️ 已精选" if is_favorite else "🤍 未精选"
            note_icon = "📝 √ 有笔记" if has_notes else "📝 无笔记"
            status_line = f"{fav_icon} | {note_icon} | 📅 {created_at}"
            
            lines.append(lang_ctx.t(
                'review_random',
                id=archive_id,
                title=title_display,
                tags=tags_str,
                created_at=created_at
            ))
            # 添加状态行
            lines.append(f"   {status_line}")
        
        # 添加返回按钮
        keyboard = [[
            InlineKeyboardButton(
                "← 返回选择",
                callback_data='review:back'
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            '\n'.join(lines),
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error handling review callback: {e}", exc_info=True)
        try:
            await query.edit_message_text(lang_ctx.t('error_occurred', error=str(e)))
        except:
            pass
        await query.answer(f"Error: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle note button click - 查看归档的关联笔记
    
    Callback data format: note:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: note:archive_id
        archive_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            logger.error("Note manager not initialized")
            return
        
        # 获取该归档的所有笔记
        notes = note_manager.get_notes(archive_id)
        
        if not notes:
            # 没有笔记时，直接设置等待状态并提示用户输入
            await query.answer("📝 请回复此消息输入笔记")
            
            # 设置等待状态
            context.user_data['waiting_note_for_archive'] = archive_id
            
            # 发送提示消息
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📝 归档 #{archive_id} 还没有笔记\n\n💬 请回复此消息输入笔记内容",
                reply_to_message_id=query.message.message_id
            )
            logger.info(f"User waiting to add note for archive {archive_id}")
            return
        
        # 构建笔记内容显示
        notes_text = f"📝 归档 #{archive_id} 的笔记\n\n"
        
        # 显示最新的笔记（或所有笔记）
        for idx, note in enumerate(notes, 1):
            content = note['content']
            notes_text += f"{content}\n"
            if len(notes) > 1:
                notes_text += f"\n📅 {note['created_at']}\n\n"
        
        if len(notes) == 1:
            notes_text += f"\n📅 {notes[0]['created_at']}"
        
        # 添加操作按钮：编辑笔记 | 删除笔记 | 分享笔记
        keyboard = [[
            InlineKeyboardButton("✏️ 编辑笔记", callback_data=f"note_edit:{archive_id}:{notes[-1]['id']}"),
            InlineKeyboardButton("🗑️ 删除笔记", callback_data=f"note_delete:{notes[-1]['id']}")
        ]]
        keyboard.append([InlineKeyboardButton("📤 分享笔记", callback_data=f"note_share:{archive_id}:{notes[-1]['id']}")])
        keyboard.append([InlineKeyboardButton("✖️ 关闭", callback_data=f"note_close")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 先answer，然后发送笔记内容
        await query.answer()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=notes_text,
            reply_markup=reply_markup
        )
        
        logger.info(f"Displayed {len(notes)} notes for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle add note button click - 提示用户输入笔记内容
    
    Callback data format: note_add:archive_id
    """
    query = update.callback_query
    
    try:
        archive_id = int(query.data.split(':')[1])
        
        # 设置用户状态，等待笔记输入
        context.user_data['waiting_note_for_archive'] = archive_id
        
        await query.answer("📝 请回复此消息输入笔记")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"💬 请回复此消息输入笔记内容\n\n将为归档 #{archive_id} 添加笔记",
            reply_to_message_id=query.message.message_id
        )
        
        logger.info(f"User waiting to add note for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note add callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle edit note button click - 显示修改和追加选项
    
    Callback data format: note_edit:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 显示修改和追加选项
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton("✏️ 修改笔记", callback_data=f"note_modify:{archive_id}:{note_id}")],
            [InlineKeyboardButton("➕ 追加笔记", callback_data=f"note_append:{archive_id}:{note_id}")],
            [InlineKeyboardButton("✖️ 取消", callback_data=f"note_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📝 编辑归档 #{archive_id} 的笔记\n\n请选择操作：",
            reply_markup=reply_markup
        )
        
        logger.info(f"Showing edit options for note {note_id}")
        
    except Exception as e:
        logger.error(f"Error handling note edit callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_modify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle modify note - 复制笔记内容供用户修改
    
    Callback data format: note_modify:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 获取笔记内容
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 获取笔记
        notes = note_manager.get_notes(archive_id)
        note_content = None
        for note in notes:
            if note['id'] == note_id:
                note_content = note['content']
                break
        
        if not note_content:
            await query.answer("笔记不存在", show_alert=True)
            return
        
        # 设置等待状态（修改模式）
        context.user_data['waiting_note_for_archive'] = archive_id
        context.user_data['note_modify_mode'] = True
        context.user_data['note_id_to_modify'] = note_id
        
        await query.answer("📋 笔记内容已发送")
        
        # 发送当前笔记内容供用户复制修改
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📝 当前笔记内容：\n\n{note_content}\n\n💡 请复制上方内容，修改后回复此消息发送",
            reply_to_message_id=query.message.message_id
        )
        
        logger.info(f"User modifying note {note_id} for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note modify callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_append_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle append note - 追加内容到现有笔记
    
    Callback data format: note_append:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 设置等待状态（追加模式）
        context.user_data['waiting_note_for_archive'] = archive_id
        context.user_data['note_append_mode'] = True
        context.user_data['note_id_to_append'] = note_id
        
        await query.answer("➕ 请输入要追加的内容")
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"➕ 追加笔记内容\n\n请回复此消息输入要追加的内容",
            reply_to_message_id=query.message.message_id
        )
        
        logger.info(f"User appending to note {note_id} for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note append callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle share note - 发送格式化的笔记供用户转发分享
    
    Callback data format: note_share:archive_id:note_id
    """
    query = update.callback_query
    
    try:
        parts = query.data.split(':')
        archive_id = int(parts[1])
        note_id = int(parts[2])
        
        # 获取笔记内容
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 获取笔记
        notes = note_manager.get_notes(archive_id)
        note_content = None
        note_created_at = None
        for note in notes:
            if note['id'] == note_id:
                note_content = note['content']
                note_created_at = note['created_at']
                break
        
        if not note_content:
            await query.answer("笔记不存在", show_alert=True)
            return
        
        # 获取存档信息（用于显示标题等）
        db_storage = context.bot_data.get('db_storage')
        archive_info = None
        if db_storage:
            archive_info = db_storage.get_archive(archive_id)
        
        # 构建分享消息
        share_text = "📝 笔记分享\n\n"
        
        # 如果有存档标题，添加标题
        if archive_info and archive_info.get('title'):
            share_text += f"📌 {archive_info['title']}\n\n"
        
        share_text += f"{note_content}\n\n"
        share_text += f"---\n"
        share_text += f"📅 {note_created_at}\n"
        share_text += f"🔖 来自归档 #{archive_id}"
        
        await query.answer("📤 笔记已发送，可直接转发")
        
        # 发送格式化的笔记消息
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=share_text
        )
        
        logger.info(f"Shared note {note_id} from archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note share callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_note_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle delete note button click
    
    Callback data format: note_delete:note_id
    """
    query = update.callback_query
    
    try:
        note_id = int(query.data.split(':')[1])
        
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        # 删除笔记
        success = note_manager.delete_note(note_id)
        
        if success:
            await query.answer("✅ 笔记已删除")
            # 删除显示笔记的消息
            try:
                await query.message.delete()
            except:
                pass
            logger.info(f"Deleted note {note_id}")
        else:
            await query.answer("❌ 删除失败", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling note delete callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_refine_note_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle refine note button click - prompts user for refinement instructions
    
    Callback data format: refine_note:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # Parse archive_id from callback data
        archive_id = int(query.data.split(':')[1])
        
        # Check if AI is available
        ai_summarizer = context.bot_data.get('ai_summarizer')
        if not ai_summarizer or not ai_summarizer.is_available():
            await query.answer("❌ AI功能未启用", show_alert=True)
            return
        
        # Get existing notes
        note_manager = context.bot_data.get('note_manager')
        if not note_manager:
            await query.answer("笔记管理器未初始化", show_alert=True)
            return
        
        notes = note_manager.get_notes_by_archive(archive_id)
        if not notes:
            await query.answer("❌ 该归档没有笔记", show_alert=True)
            return
        
        # Store context for next message
        context.user_data['refine_note_context'] = {
            'archive_id': archive_id,
            'notes': notes,
            'waiting_for_instruction': True
        }
        
        # Format existing notes
        notes_text = "\n\n".join([f"📝 {note['content']}" for note in notes])
        
        # Prompt user for refinement instructions
        await query.edit_message_text(
            f"✨ **精炼笔记**\n\n"
            f"当前笔记：\n{truncate_text(notes_text, 200)}\n\n"
            f"📨 请告诉我你想怎么改？\n\n"
            f"例如：\n"
            f"• 缩短\n"
            f"• 展开\n"
            f"• 改写成要点\n"
            f"• 翻译成英文\n"
            f"• 其他指令...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        await query.answer("💡 请发送你的指令")
        logger.info(f"User requested note refinement for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling refine note callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle favorite/unfavorite button click
    
    Callback data format: fav:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: fav:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # 获取数据库
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            await query.answer("Database not initialized", show_alert=True)
            logger.error("Database storage not initialized")
            return
        
        db = db_storage.db
        
        # 切换精选状态
        is_fav = db.is_favorite(archive_id)
        success = db.set_favorite(archive_id, not is_fav)
        
        if success:
            new_status = not is_fav
            
            # 更新按钮显示
            try:
                # 获取当前消息的按钮
                original_markup = query.message.reply_markup
                if original_markup and original_markup.inline_keyboard:
                    # 重建按钮，更新精选按钮的图标
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    new_keyboard = []
                    for row in original_markup.inline_keyboard:
                        new_row = []
                        for button in row:
                            callback_data = button.callback_data
                            if callback_data and callback_data.startswith(f'fav:{archive_id}'):
                                # 更新精选按钮图标
                                fav_icon = "❤️" if new_status else "🤍"
                                new_row.append(InlineKeyboardButton(fav_icon, callback_data=callback_data))
                            else:
                                new_row.append(button)
                        new_keyboard.append(new_row)
                    
                    # 更新消息的按钮
                    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
            except Exception as e:
                logger.debug(f"Failed to update button markup: {e}")
            
            # 给用户反馈
            if new_status:
                await query.answer("❤️ 已添加到精选")
            else:
                await query.answer("🤍 已取消精选")
            
            logger.info(f"Archive {archive_id} favorite toggled to {new_status}")
        else:
            await query.answer("操作失败", show_alert=True)
            logger.error(f"Failed to toggle favorite for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling favorite callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_forward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle forward button click - 转发归档消息到频道
    
    Callback data format: forward:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: forward:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # 获取归档信息
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            await query.answer("Database not initialized", show_alert=True)
            return
        
        # 查询归档
        archive = db_storage.db.execute(
            "SELECT storage_path, storage_type FROM archives WHERE id = ? AND deleted = 0",
            (archive_id,)
        ).fetchone()
        
        if not archive:
            await query.answer("归档不存在", show_alert=True)
            return
        
        storage_path = archive['storage_path']
        storage_type = archive['storage_type']
        
        if storage_type != 'telegram' or not storage_path:
            await query.answer("此归档无法转发", show_alert=True)
            return
        
        # 解析storage_path获取消息ID
        parts = storage_path.split(':')
        if len(parts) >= 2:
            channel_id = int(parts[0]) if parts[0].startswith('-') else int(f"-100{parts[0]}")
            message_id = int(parts[1])
        else:
            from ..utils.config import get_config
            config = get_config()
            channel_id = config.telegram_channel_id
            message_id = int(storage_path)
        
        # 转发消息到用户
        try:
            await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id=channel_id,
                message_id=message_id
            )
            await query.answer("✅ 已转发")
            logger.info(f"Forwarded archive {archive_id} to user {update.effective_user.id}")
        except Exception as fwd_error:
            logger.error(f"Forward error: {fwd_error}")
            await query.answer("转发失败，可能是权限问题", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling forward callback: {e}", exc_info=True)


@with_language_context
async def handle_short_text_intent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理短文本意图选择回调
    
    Callback data format: short_text:note|ai|archive
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析: short_text:action
        action = callback_data.split(':', 1)[1]
        
        # 获取待处理文本
        text = context.user_data.get('pending_short_text')
        if not text:
            await query.edit_message_text("⚠️ 会话已过期，请重新发送文本")
            return
        
        if action == 'note':
            # 保存为笔记
            note_manager = context.bot_data.get('note_manager')
            if note_manager:
                note_id = note_manager.add_note(None, text)
                if note_id:
                    await query.edit_message_text(f"✅ 已保存为笔记 (ID: #{note_id})")
                    logger.info(f"User chose to save as note: {note_id}")
                else:
                    await query.edit_message_text("❌ 笔记保存失败")
            else:
                await query.edit_message_text("❌ 笔记管理器未初始化")
        
        elif action == 'ai':
            # AI互动模式
            ai_summarizer = context.bot_data.get('ai_summarizer')
            if ai_summarizer and ai_summarizer.is_available():
                # 创建AI会话
                from ..core.ai_session import get_session_manager
                from ..ai.chat_router import handle_chat_message
                
                session_manager = get_session_manager()
                user_id = query.from_user.id
                
                # 创建新会话
                session_manager.create_session(user_id)
                
                await query.edit_message_text(
                    "🤖 **AI互动模式已激活**\n\n"
                    "我可以帮你：\n"
                    "• 搜索归档内容\n"
                    "• 回答相关问题\n"
                    "• 分析和总结信息\n\n"
                    "💬 直接发送消息开始对话\n"
                    "📝 发送 \"退出\" 或 \"exit\" 结束会话",
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info(f"User activated AI mode with text: {text[:50]}")
                
                # 如果有待处理文本，处理它
                if text:
                    # 获取会话数据
                    session = session_manager.get_session(user_id)
                    
                    # 调用AI处理（使用'auto'让AI自动判断语言）
                    ai_response = await handle_chat_message(text, session, context, 'auto')
                    
                    # 发送AI回复
                    await query.message.reply_text(f"🤖 {ai_response}")
                    
                    # 更新会话
                    session_manager.update_session(user_id, session.get('context', {}))
            else:
                await query.edit_message_text(
                    "❌ AI功能未启用\n\n"
                    "请在配置文件中启用AI功能后重试。"
                )
        
        elif action == 'archive':
            # 归档为内容
            await query.edit_message_text("📦 正在归档...")
            
            # 创建归档
            storage_manager = context.bot_data.get('storage_manager')
            if storage_manager:
                from ..utils.helpers import format_datetime
                
                result = storage_manager.create_archive(
                    content_type='text',
                    title=text[:50] + ('...' if len(text) > 50 else ''),
                    content=text,
                    file_id=None,
                    tags=[],
                    source='telegram',
                    ai_analysis=None
                )
                
                if result:
                    archive_id = result.get('id')
                    await query.edit_message_text(
                        f"✅ 已归档 (ID: #{archive_id})\n\n"
                        f"内容：{truncate_text(text, 100)}"
                    )
                    logger.info(f"User chose to archive text: {archive_id}")
                else:
                    await query.edit_message_text("❌ 归档失败")
            else:
                await query.edit_message_text("❌ 存储管理器未初始化")
        
        # 清除待处理文本
        context.user_data.pop('pending_short_text', None)
        
    except Exception as e:
        logger.error(f"Error handling short text intent callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ 处理失败: {str(e)}")
        await query.answer(f"Error: {str(e)}", show_alert=True)
