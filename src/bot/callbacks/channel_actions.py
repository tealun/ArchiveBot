"""
Channel Message Actions Callback Handler
处理频道消息按钮的回调（笔记/删除）
精选功能使用系统已有的handle_favorite_callback处理
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_channel_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理笔记按钮点击
    - 如果有笔记 → 跳转到笔记链接
    - 如果没有笔记 → 提示创建笔记
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析回调数据：ch_note:archive_id
        data = query.data.split(':')
        if len(data) < 2:
            await query.answer("数据格式错误", show_alert=True)
            return
        
        archive_id = int(data[1])
        logger.info(f"Handling channel note button for archive_id={archive_id}")
        
        # 查询是否有笔记
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            logger.error("db_storage not found in context.bot_data")
            await query.answer("数据库不可用", show_alert=True)
            return
        
        db = db_storage.db
        if not db:
            logger.error("db_storage.db is None")
            await query.answer("数据库连接错误", show_alert=True)
            return
        
        notes = db.execute(
            "SELECT id, storage_path FROM notes WHERE archive_id = ? AND deleted = 0",
            (archive_id,)
        ).fetchall()
        
        if notes:
            # 有笔记，生成跳转链接列表
            note_links = []
            for note in notes:
                note_id = note['id']
                storage_path = note['storage_path']
                if storage_path:
                    note_links.append(f"📝 <a href='{storage_path}'>笔记 #{note_id}</a>")
                else:
                    note_links.append(f"📝 笔记 #{note_id}（未存储）")
            
            text = "📝 <b>该存档的笔记</b>\n\n" + "\n".join(note_links)
            
            # 发送新消息而不是编辑原消息（保留原始存档消息）
            await query.message.reply_text(
                text=text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 返回", callback_data=f"ch_back:{archive_id}")
                ]])
            )
            logger.info(f"Sent notes list message for archive {archive_id}")
        else:
            # 没有笔记，提示创建
            await query.answer(
                "该存档还没有笔记\n请先在Bot中查看该存档，然后点击'📝 添加笔记'按钮创建",
                show_alert=True
            )
    
    except Exception as e:
        logger.error(f"Error handling channel note button: {e}", exc_info=True)
        await query.answer("处理失败", show_alert=True)


async def handle_channel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理删除按钮点击
    软删除（标记deleted=1）
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析回调数据：ch_del:archive_id 或 ch_del_note:note_id
        data = query.data.split(':')
        if len(data) < 2:
            await query.answer("数据格式错误", show_alert=True)
            return
        
        logger.info(f"Handling channel delete button: {query.data}")
        
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            logger.error("db_storage not found in context.bot_data")
            await query.answer("数据库不可用", show_alert=True)
            return
        
        db = db_storage.db
        if not db:
            logger.error("db_storage.db is None")
            await query.answer("数据库连接错误", show_alert=True)
            return
        
        if data[0] == 'ch_del':
            # 删除存档
            archive_id = int(data[1])
            db.execute(
                "UPDATE archives SET deleted = 1 WHERE id = ?",
                (archive_id,)
            )
            db.commit()
            item_type = "存档"
        elif data[0] == 'ch_del_note':
            # 删除笔记
            note_id = int(data[1])
            db.execute(
                "UPDATE notes SET deleted = 1 WHERE id = ?",
                (note_id,)
            )
            db.commit()
            item_type = "笔记"
        else:
            await query.answer("未知操作", show_alert=True)
            return
        
        # 触发AI缓存失效
        storage_manager = context.bot_data.get('storage_manager')
        if storage_manager:
            storage_manager._invalidate_ai_cache()
        
        # 直接删除频道消息
        try:
            await query.message.delete()
            logger.info(f"Deleted channel message for {item_type} (callback: {query.data})")
        except Exception as e:
            logger.warning(f"Failed to delete channel message: {e}")
            # 如果删除失败，降级为添加删除标记
            try:
                text = f"🗑️ <s>{query.message.text or query.message.caption}</s>\n\n<i>[已删除]</i>"
                if query.message.text:
                    await query.edit_message_text(
                        text=text[:4096],
                        parse_mode='HTML',
                        reply_markup=None
                    )
                else:
                    await query.edit_message_caption(
                        caption=text[:1024],
                        parse_mode='HTML',
                        reply_markup=None
                    )
                logger.info(f"Fallback: marked message as deleted instead")
            except Exception as e2:
                logger.error(f"Failed to mark message as deleted: {e2}")
        
        await query.answer(f"✅ {item_type}已删除", show_alert=False)
    
    except Exception as e:
        logger.error(f"Error handling channel delete button: {e}", exc_info=True)
        await query.answer("删除失败", show_alert=True)


async def handle_channel_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理返回按钮（从笔记列表或存档详情返回原始存档消息）
    ch_back:archive_id - 从笔记列表返回
    ch_back_note:archive_id - 从存档详情返回笔记
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析回调数据
        data = query.data.split(':')
        if len(data) < 2:
            await query.answer("数据格式错误", show_alert=True)
            return
        
        callback_type = data[0]  # ch_back 或 ch_back_note
        archive_id = int(data[1])
        logger.info(f"Handling {callback_type} button for archive_id={archive_id}")
        
        # 获取数据库实例
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            logger.error("db_storage not found in context.bot_data")
            await query.answer("数据库不可用", show_alert=True)
            return
        
        db = db_storage.db
        if not db:
            logger.error("db_storage.db is None")
            await query.answer("数据库连接错误", show_alert=True)
            return
        
        if callback_type == 'ch_back_note':
            # 从存档详情返回笔记列表
            logger.info(f"Returning from archive detail to notes list for archive {archive_id}")
            
            # 查询笔记列表
            notes = db.execute(
                "SELECT id, storage_path FROM notes WHERE archive_id = ? AND deleted = 0",
                (archive_id,)
            ).fetchall()
            
            if notes:
                # 重新显示笔记列表
                note_links = []
                for note in notes:
                    note_id = note['id']
                    storage_path = note['storage_path'] if 'storage_path' in note.keys() else None
                    if storage_path:
                        note_links.append(f"📝 <a href='{storage_path}'>笔记 #{note_id}</a>")
                    else:
                        note_links.append(f"📝 笔记 #{note_id}（未存储）")
                
                text = "📝 <b>该存档的笔记</b>\n\n" + "\n".join(note_links)
                await query.edit_message_text(
                    text=text,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 返回", callback_data=f"ch_back:{archive_id}")
                    ]])
                )
                logger.info(f"Successfully returned to notes list for archive {archive_id}")
            else:
                await query.answer("笔记已不存在", show_alert=True)
        else:
            # 从笔记列表返回原始存档消息（删除当前临时消息）
            logger.info(f"Returning from notes list to original archive message for archive {archive_id}")
            await query.message.delete()
            await query.answer("已返回原始消息", show_alert=False)
            logger.info(f"Successfully deleted temporary message, user returned to original archive")
    
    except Exception as e:
        logger.error(f"Error handling channel back button: {e}", exc_info=True)
        await query.answer("处理失败", show_alert=True)


async def handle_channel_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理查看存档按钮（从笔记跳转到存档）
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析回调数据：ch_archive:archive_id
        data = query.data.split(':')
        if len(data) < 2:
            await query.answer("数据格式错误", show_alert=True)
            return
        
        archive_id = int(data[1])
        logger.info(f"Handling channel archive button for archive_id={archive_id}")
        
        # 获取数据库存储实例
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            logger.error("db_storage not found in context.bot_data")
            await query.answer("数据库不可用", show_alert=True)
            return
        
        # 获取数据库实例
        db = db_storage.db
        if not db:
            logger.error("db_storage.db is None")
            await query.answer("数据库连接错误", show_alert=True)
            return
        
        # 查询存档信息
        logger.info(f"Querying archive {archive_id} from database")
        archive = db.execute(
            "SELECT storage_path, title FROM archives WHERE id = ? AND deleted = 0",
            (archive_id,)
        ).fetchone()
        
        if not archive:
            logger.warning(f"Archive {archive_id} not found in database")
            await query.answer("存档不存在", show_alert=True)
            return
        
        storage_path = archive['storage_path'] if 'storage_path' in archive.keys() else None
        if not storage_path:
            logger.warning(f"Archive {archive_id} has no storage_path")
            await query.answer("存档未存储", show_alert=True)
            return
        
        title = archive['title'] if 'title' in archive.keys() and archive['title'] else '无标题'
        logger.info(f"Found archive {archive_id}: title='{title}', storage_path='{storage_path}'")
        
        # 如果是Telegram链接格式（channel:message:file_id），转换为可点击链接
        if ':' in storage_path and not storage_path.startswith('http'):
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id = parts[0]
                message_id = parts[1]
                # 转换为t.me链接
                if channel_id.startswith('-100'):
                    channel_numeric = channel_id[4:]
                    storage_path = f"https://t.me/c/{channel_numeric}/{message_id}"
                    logger.info(f"Converted storage_path to: {storage_path}")
        
        text = f"📄 <b>存档</b>\n\n标题: {title}\n\n<a href='{storage_path}'>点击查看存档消息</a>"
        logger.info(f"Editing message with archive link for archive {archive_id}")
        
        await query.edit_message_text(
            text=text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 返回笔记", callback_data=f"ch_back_note:{archive_id}")
            ]])
        )
        
        logger.info(f"Successfully handled channel archive button for archive {archive_id}")
    
    except Exception as e:
        logger.error(f"Error handling channel archive button: {e}", exc_info=True)
        await query.answer("处理失败", show_alert=True)
