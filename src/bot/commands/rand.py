"""
Random review command - 随机回顾存档
"""

import logging
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config
from ...utils.message_builder import MessageBuilder

logger = logging.getLogger(__name__)


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
            await update.message.reply_text(lang_ctx.t('error_database_not_initialized'))
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
                await update.message.reply_text(
                    f"❌ 无效的数量参数\n\n使用方法：/rand [1-10]\n默认数量：{default_count}"
                )
                return
        
        # 获取所有非删除的存档ID
        with db_storage.db._lock:
            cursor = db_storage.db.execute(
                "SELECT id FROM archives WHERE deleted = 0 ORDER BY id"
            )
            all_ids = [row[0] for row in cursor.fetchall()]
        
        if not all_ids:
            await update.message.reply_text("📭 暂无存档可供回顾")
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
            await update.message.reply_text("❌ 获取存档失败")
            return
        
        # 根据数量决定回复方式
        if len(archives) <= 3:
            # 3条以内：直接发送详细信息
            header = f"🎲 随机回顾（{len(archives)}/{len(all_ids)} 条）\n\n"
            await update.message.reply_text(header)
            
            for archive in archives:
                # 发送资源或详情
                await MessageBuilder.send_archive_resource(
                    context.bot,
                    update.effective_chat.id,
                    archive
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
            
            await update.message.reply_text(
                full_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        
        logger.info(f"Random review: returned {len(archives)} archives")
        
    except Exception as e:
        logger.error(f"Error in rand_command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 随机回顾失败：{str(e)}")
