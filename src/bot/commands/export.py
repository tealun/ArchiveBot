"""
Export commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.export_manager import ExportManager
from ...utils.helpers import format_file_size

@with_language_context
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
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
        lang_ctx: Language context
    """
    try:
        # 获取export_manager
        export_manager = context.bot_data.get('export_manager')
        if not export_manager:
            await update.message.reply_text(lang_ctx.t('export_manager_not_initialized'))
            return
        
        # 发送处理中提示
        processing_msg = await update.message.reply_text(lang_ctx.t('export_processing'))
        
        # 解析命令参数
        format_type = 'markdown'  # 默认格式
        tag_name = None
        
        if context.args:
            if context.args[0] == 'tag':
                # 按标签导出
                if len(context.args) < 2:
                    await processing_msg.edit_text(lang_ctx.t('export_tag_usage'))
                    return
                tag_name = context.args[1]
                format_type = context.args[2] if len(context.args) > 2 else 'markdown'
            else:
                # 指定格式
                format_type = context.args[0].lower()
        
        # 验证格式
        if format_type not in ['markdown', 'json', 'csv', 'md']:
            await processing_msg.edit_text(lang_ctx.t('export_invalid_format'))
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
            await processing_msg.edit_text(lang_ctx.t('export_failed'))
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
            caption=lang_ctx.t('export_success', filename=full_filename, size=len(data))
        )
        
        # 删除处理中提示
        await processing_msg.delete()
        
        logger.info(f"Export command executed: format={format_type}, tag={tag_name}, size={len(data)}")
        
    except Exception as e:
        logger.error(f"Error in export_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
        except:
            pass
