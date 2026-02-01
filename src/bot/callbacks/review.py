"""
Review callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.review_manager import ReviewManager
from ...utils.helpers import format_datetime

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
        except Exception as edit_err:
            logger.debug(f"Failed to edit message with error: {edit_err}")
        await query.answer(f"Error: {str(e)}", show_alert=True)
