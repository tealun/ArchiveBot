"""
Callback query handlers
Handles button clicks and inline keyboard callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.i18n import get_i18n
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


async def handle_tag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            await query.edit_message_text(f"标签 #{tag_name} 下暂无内容")
            return
        
        # 格式化结果列表
        formatted_results = []
        action_buttons = []  # 每条记录的操作按钮行
        
        # 获取数据库实例用于查询状态
        db_storage = context.bot_data.get('db_storage')
        db = db_storage.db if db_storage else None
        i18n = get_i18n()
        
        for idx, archive in enumerate(search_result.get('results', []), page * page_size + 1):
            emoji = get_content_type_emoji(archive.get('content_type', ''))
            title = archive.get('title', 'Untitled')
            title_truncated = truncate_text(title, 40)
            archive_id = archive.get('id')
            
            # 构建跳转链接
            storage_path = archive.get('storage_path')
            if storage_path:
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    channel_id = parts[0].replace('-100', '')
                    message_id = parts[1]
                    link = f"https://t.me/c/{channel_id}/{message_id}"
                    title_truncated = f"<a href='{link}'>{title_truncated}</a>"
            
            archived_at = format_datetime(archive.get('archived_at', ''))
            
            # 检查状态
            has_notes = db.has_notes(archive_id) if db and archive_id else False
            is_favorite = db.is_favorite(archive_id) if db and archive_id else False
            
            # 构建操作按钮（内联在文本中）
            note_icon = "📝✓" if has_notes else "📝"
            fav_icon = "❤️" if is_favorite else "🤍"
            forward_icon = "↗️"
            
            # 结果文本：序号、emoji、标题换行后显示按钮和日期
            result_text = f"{idx}. {emoji} {title_truncated}"
            formatted_results.append(result_text)
            
            # 为每条记录创建一行操作按钮
            if archive_id:
                action_row = [
                    InlineKeyboardButton(note_icon, callback_data=f"note:{archive_id}"),
                    InlineKeyboardButton(fav_icon, callback_data=f"fav:{archive_id}"),
                    InlineKeyboardButton(forward_icon, callback_data=f"forward:{archive_id}"),
                    InlineKeyboardButton(f"📅 {archived_at}", callback_data="noop")
                ]
                action_buttons.append(action_row)
        
        results_text = '\n\n'.join(formatted_results)
        
        # 获取总数
        has_more = search_result.get('count', 0) == page_size
        total_count = search_result.get('total_count', search_result.get('count', 0))
        
        message = f"🏷️ 标签: #{tag_name}\n\n{results_text}"
        
        # 构建按钮布局
        keyboard = []
        
        # 添加每条记录的操作按钮
        keyboard.extend(action_buttons)
        
        # 构建分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        # 只有多于1页时才显示分页按钮
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    i18n.t('button_previous_page'),
                    callback_data=f"tag:{tag_name}:{page-1}"
                ))
            
            # 显示当前页码
            nav_row.append(InlineKeyboardButton(
                i18n.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="tags_noop"
            ))
            
            if page + 1 < total_pages:
                nav_row.append(InlineKeyboardButton(
                    i18n.t('button_next_page'),
                    callback_data=f"tag:{tag_name}:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        # 返回按钮
        keyboard.append([InlineKeyboardButton(
            i18n.t('button_back_to_tags'),
            callback_data="tags_page:0"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error handling tag callback: {e}", exc_info=True)


async def handle_tags_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        
        i18n = get_i18n()
        
        # 分页按钮 - 只在多页时显示
        total_pages = (len(tags) + page_size - 1) // page_size
        
        # 只有多于1页时才显示分页按钮
        if total_pages > 1:
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    i18n.t('button_previous_page'),
                    callback_data=f"tags_page:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                i18n.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="tags_noop"
            ))
            
            if end_idx < len(tags):
                nav_row.append(InlineKeyboardButton(
                    i18n.t('button_next_page'),
                    callback_data=f"tags_page:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = i18n.t('tags_button_list_header', count=len(tags))
        
        await query.edit_message_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error handling tags page callback: {e}", exc_info=True)


async def handle_tag_list_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle tag list pagination
    
    Callback data format: tag_list:page
    """
    await handle_tags_page_callback(update, context)


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            
            # Set language
            i18n = get_i18n()
            if i18n.set_language(language):
                # Save to config
                config = get_config()
                config.set('bot.language', language)
                config.save()
                
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
                await query.edit_message_text(i18n.t('language_changed'))
                
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


async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        
        # Format results
        result_text, results_with_ai = search_engine.format_results(search_result, with_links=True)
        
        # Build keyboard
        keyboard = []
        
        # AI解析按钮
        if results_with_ai:
            for item in results_with_ai:
                # 计算全局索引（考虑分页偏移）
                global_index = offset + item['index']
                title_preview = truncate_text(item['title'], 12)
                button_text = f"🤖 #{global_index}《{title_preview}》"
                callback_data = f"ai_view:{item['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # 分页按钮 - 只在多页时显示
        total_pages = (total_count + page_size - 1) // page_size
        
        if total_pages > 1:
            i18n = get_i18n()
            nav_row = []
            
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


async def handle_ai_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理删除归档（移动到垃圾箱）
    
    Callback data format: delete:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        i18n = get_i18n()
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(i18n.t('trash_manager_not_initialized'))
            return
        
        # 移动到垃圾箱
        if trash_manager.move_to_trash(archive_id):
            await query.edit_message_text(i18n.t('archive_moved_to_trash', archive_id=archive_id))
        else:
            await query.edit_message_text(i18n.t('archive_delete_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} moved to trash via callback")
        
    except Exception as e:
        logger.error(f"Error handling delete callback: {e}", exc_info=True)


async def handle_trash_restore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理恢复归档
    
    Callback data format: trash_restore:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        i18n = get_i18n()
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(i18n.t('trash_manager_not_initialized'))
            return
        
        # 恢复归档
        if trash_manager.restore_archive(archive_id):
            await query.edit_message_text(i18n.t('trash_restore_success', archive_id=archive_id))
        else:
            await query.edit_message_text(i18n.t('trash_restore_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} restored from trash via callback")
        
    except Exception as e:
        logger.error(f"Error handling restore callback: {e}", exc_info=True)


async def handle_trash_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理永久删除归档
    
    Callback data format: trash_delete:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        i18n = get_i18n()
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(i18n.t('trash_manager_not_initialized'))
            return
        
        # 永久删除
        if trash_manager.delete_permanently(archive_id):
            await query.edit_message_text(i18n.t('trash_delete_success', archive_id=archive_id))
        else:
            await query.edit_message_text(i18n.t('trash_delete_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} permanently deleted via callback")
        
    except Exception as e:
        logger.error(f"Error handling permanent delete callback: {e}", exc_info=True)


async def handle_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理回顾统计按钮点击
    
    Callback data format: review:period (week/month/year) or review:back
    """
    try:
        query = update.callback_query
        callback_data = query.data
        i18n = get_i18n()
        
        # 解析: review:period
        parts = callback_data.split(':', 1)
        period = parts[1] if len(parts) > 1 else 'month'
        
        # 返回选择菜单
        if period == 'back':
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
            await query.edit_message_text(
                i18n.t('review_usage'),
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        if period not in ['week', 'month', 'year']:
            await query.edit_message_text(i18n.t('review_invalid_period'))
            return
        
        review_manager = context.bot_data.get('review_manager')
        if not review_manager:
            await query.edit_message_text(i18n.t('review_manager_not_initialized'))
            return
        
        # 显示处理中
        await query.edit_message_text(i18n.t('processing'))
        
        # 生成报告
        report = review_manager.build_report(period=period, include_random=True)
        
        if not report or report['totals']['archives'] == 0:
            await query.edit_message_text(i18n.t('review_no_data'))
            return
        
        # 构建消息
        period_name = i18n.t(f'review_period_{period}')
        lines = [i18n.t('review_header', period=period_name)]
        
        # 统计概览
        totals = report['totals']
        lines.append(i18n.t(
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
                lines.append(i18n.t('review_trend', trend='\n'.join(trend_lines)))
        
        # 热门标签（Top 10）
        top_tags = report.get('top_tags', [])
        if top_tags:
            tag_lines = []
            for tag_item in top_tags[:10]:
                tag_name = tag_item.get('tag_name', '')
                tag_count = tag_item.get('count', 0)
                tag_lines.append(f"#{tag_name} ({tag_count})")
            if tag_lines:
                lines.append(i18n.t('review_top_tags', tags='\n'.join(tag_lines)))
        
        # 随机回顾
        random_archive = report.get('random_archive')
        if random_archive:
            archive_id = random_archive.get('id')
            title = random_archive.get('title') or random_archive.get('content', '')[:50]
            tags = report.get('random_tags', [])
            tags_str = ' '.join(f'#{t}' for t in tags) if tags else i18n.t('tags_empty')
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
            
            lines.append(i18n.t(
                'review_random',
                id=archive_id,
                title=title_display,
                tags=tags_str,
                created_at=created_at
            ))
        
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
        i18n = get_i18n()
        try:
            await query.edit_message_text(i18n.t('error_occurred', error=str(e)))
        except:
            pass
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def handle_note_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle note button click - 进入笔记模式并关联到指定归档
    
    Callback data format: note:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: note:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # 设置用户状态为笔记模式
        context.user_data['note_mode'] = True
        context.user_data['note_archive_id'] = archive_id
        
        # 发送提示消息
        i18n = get_i18n()
        await query.answer(i18n.t('note_mode_archive_linked', archive_id=archive_id)[:200], show_alert=True)
        
        # 发送详细提示到聊天
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=i18n.t('note_mode_archive_linked', archive_id=archive_id),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"User {update.effective_user.id} entered note mode for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling note callback: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def handle_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            return
        
        db = db_storage.db
        
        # 切换精选状态
        is_fav = db.is_favorite(archive_id)
        success = db.set_favorite(archive_id, not is_fav)
        
        if success:
            i18n = get_i18n()
            if is_fav:
                await query.answer("❌ 已取消精选")
            else:
                await query.answer("❤️ 已添加到精选")
            
            # 刷新当前消息（更新按钮状态）
            # 重新构建按钮...这需要知道当前是在什么页面
            # 简化处理：只回答不刷新
            logger.info(f"Archive {archive_id} favorite toggled to {not is_fav}")
        else:
            await query.answer("操作失败", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling favorite callback: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)}", show_alert=True)


async def handle_forward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        await query.answer(f"Error: {str(e)}", show_alert=True)
