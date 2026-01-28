"""
Random review command - 随机回顾存档
"""

import logging
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from .note_mode_interceptor import intercept_in_note_mode
from ...utils.config import get_config
from ...utils.message_builder import MessageBuilder
from ...utils.helpers import send_or_update_reply

logger = logging.getLogger(__name__)


@intercept_in_note_mode
@with_language_context
async def rand_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /rand or /r command - 随机返回存档
    
    Usage:
        /rand [count] - 随机返回指定数量的存档（默认从配置读取，范围1-10）
        /r [count] - 同上
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        db_storage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await send_or_update_reply(update, context, lang_ctx.t('error_database_not_initialized'), 'rand')
            return
        
        # 获取配置的随机回顾数量
        config = get_config()
        default_count = config.get('review.random_count', 3)
        
        # 解析参数
        count = default_count
        if context.args:
            try:
                count = int(context.args[0])
                # 限制范围1-10
                count = max(1, min(10, count))
            except ValueError:
                await send_or_update_reply(
                    update,
                    context,
                    f"❌ 无效的数量参数\n\n使用方法：/rand [1-10]\n默认数量：{default_count}",
                    'rand'
                )
                return
        
        # 获取所有非删除的存档ID
        with db_storage.db._lock:
            cursor = db_storage.db.execute(
                "SELECT id FROM archives WHERE deleted = 0 ORDER BY id"
            )
            all_ids = [row[0] for row in cursor.fetchall()]
        
        if not all_ids:
            await send_or_update_reply(update, context, "📭 暂无存档可供回顾", 'rand')
            return
        
        # 随机选择
        selected_count = min(count, len(all_ids))
        selected_ids = random.sample(all_ids, selected_count)
        
        # 获取存档详情
        archives = []
        for archive_id in selected_ids:
            archive = db_storage.get_archive(archive_id)
            if archive:
                archives.append(archive)
        
        if not archives:
            await send_or_update_reply(update, context, "❌ 获取存档失败", 'rand')
            return
        
        # 根据数量决定回复方式
        if len(archives) <= 3:
            # 3条以内：直接发送详细信息
            header = f"🎲 随机回顾（{len(archives)}/{len(all_ids)} 条）\n\n"
            await send_or_update_reply(update, context, header, 'rand')
            
            for archive in archives:
                # 尝试发送资源
                result = await MessageBuilder.send_archive_resource(
                    context.bot,
                    update.effective_chat.id,
                    archive
                )
                
                # 如果无法发送资源（database/reference类型或发送失败），发送文本详情
                if not result:
                    note_manager = context.bot_data.get('note_manager')
                    notes = note_manager.get_notes(archive['id']) if note_manager else []
                    text, reply_markup = MessageBuilder.format_text_archive_reply(
                        archive,
                        notes,
                        db_instance=db_storage.db
                    )
                    await update.message.reply_text(
                        text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
        else:
            # 3条以上：发送列表
            header = f"🎲 随机回顾（{len(archives)}/{len(all_ids)} 条）\n\n"
            list_text = MessageBuilder.format_archive_list(
                archives,
                lang_ctx,
                db_instance=db_storage.db,
                with_links=True
            )
            
            full_text = header + list_text
            
            await send_or_update_reply(
                update,
                context,
                full_text,
                'rand',
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        
        logger.info(f"Random review: returned {len(archives)} archives")
        
    except Exception as e:
        logger.error(f"Error in rand_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, f"❌ 随机回顾失败：{str(e)}", 'rand')
