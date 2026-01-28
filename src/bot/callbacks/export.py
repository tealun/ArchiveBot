"""
Export callbacks
"""

import logging
from io import BytesIO
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)


@with_language_context
async def handle_export_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle export format selection button click - 处理导出格式选择
    
    Callback data format: export_format:format_type:tag_name_or_all
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data
        parts = query.data.split(':')
        format_type = parts[1]  # markdown, json, csv
        tag_name = parts[2] if len(parts) > 2 and parts[2] != 'all' else None
        
        export_manager = context.bot_data.get('export_manager')
        
        if not export_manager:
            await query.answer(lang_ctx.t('export_manager_not_initialized'), show_alert=True)
            return
        
        # 显示处理中提示（编辑消息而不是 answer，因为 router 已经 answer 过了）
        try:
            await query.edit_message_text("⏳ 正在导出数据，请稍候...")
        except:
            pass
        
        # 导出数据
        data = None
        filename = None
        
        if tag_name:
            # 按标签导出
            data = export_manager.export_archives_by_tag(tag_name, format_type)
            filename = f"archives_tag_{tag_name}"
        else:
            # 全量导出
            if format_type == 'markdown':
                data = export_manager.export_to_markdown()
            elif format_type == 'json':
                data = export_manager.export_to_json()
            elif format_type == 'csv':
                data = export_manager.export_to_csv()
            
            filename = "archives_export"
        
        if not data:
            await query.edit_message_text(lang_ctx.t('export_failed'))
            return
        
        # 确定文件扩展名
        ext_map = {
            'markdown': 'md',
            'json': 'json',
            'csv': 'csv'
        }
        ext = ext_map.get(format_type, 'txt')
        
        # 生成文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        full_filename = f"{filename}_{timestamp}.{ext}"
        
        # 创建可下载的文件对象
        # CSV文件需要添加UTF-8 BOM，让Excel正确识别编码
        if format_type == 'csv':
            file_data = BytesIO(b'\xef\xbb\xbf' + data.encode('utf-8'))
        else:
            file_data = BytesIO(data.encode('utf-8'))
        
        file_data.name = full_filename
        file_data.seek(0)  # 确保指针在开始位置
        
        # 发送文件（使用bot而不是message以确保正确发送）
        from ...utils.helpers import format_file_size
        size_str = format_file_size(len(data))
        
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file_data,
            filename=full_filename,
            caption=f"✅ 导出成功\n\n📄 文件：{full_filename}\n📊 大小：{size_str}\n📋 格式：{format_type.upper()}"
        )
        
        # 删除选择菜单
        await query.edit_message_text(
            f"✅ 导出完成！\n\n格式：{format_type.upper()}\n文件：{full_filename}"
        )
        
        logger.info(f"Export completed: format={format_type}, tag={tag_name}, size={len(data)}")
        
    except Exception as e:
        logger.error(f"Error in export format callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)
