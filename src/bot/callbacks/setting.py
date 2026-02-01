"""
Setting callbacks - 配置管理回调处理
"""

from __future__ import annotations

import logging
import yaml
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..commands.setting import CONFIG_CATEGORIES, get_config_item_info, get_current_value, validate_config_value
from ...utils.config import get_config

logger = logging.getLogger(__name__)


async def handle_setting_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理配置分类选择
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析callback_data: setting_cat:category_key
        # 检查是否有临时回调数据（从设置保存后返回）
        callback_data = context.user_data.pop('_temp_callback', None) or query.data
        category_key = callback_data.split(':')[1]
        
        if category_key not in CONFIG_CATEGORIES:
            await query.edit_message_text("❌ 无效的分类")
            return
        
        category_info = CONFIG_CATEGORIES[category_key]
        
        # 使用MessageBuilder格式化分类菜单
        from ...utils.message_builder import MessageBuilder
        text, reply_markup = MessageBuilder.format_setting_category_menu(
            category_key, category_info, get_current_value
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in handle_setting_category_callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ 发生错误：{str(e)}")


async def handle_setting_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理配置项选择
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析callback_data: setting_item:config_key
        callback_data = query.data
        config_key = callback_data.split(':', 1)[1]
        
        item_info = get_config_item_info(config_key)
        if not item_info:
            await query.edit_message_text("❌ 无效的配置项")
            return
        
        current_value = get_current_value(config_key)
        category_key = _get_category_key(config_key)
        
        # 使用MessageBuilder格式化配置项提示
        from ...utils.message_builder import MessageBuilder
        text, reply_markup = MessageBuilder.format_setting_item_prompt(
            item_info, config_key, current_value, category_key
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        # 只对需要文本输入的类型设置等待状态（布尔类型通过按钮切换，不需要等待输入）
        if item_info['type'] in ('int', 'string'):
            context.user_data['waiting_setting_input'] = config_key
        
    except Exception as e:
        logger.error(f"Error in handle_setting_item_callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ 发生错误：{str(e)}")


async def handle_setting_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理配置值设置（通过按钮）
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 解析callback_data: setting_set:config_key:value
        parts = query.data.split(':', 2)
        config_key = parts[1]
        value_str = parts[2]
        
        # 验证并设置配置
        success, message = await _set_config_value(config_key, value_str)
        
        if success:
            # 返回到分类视图并显示成功消息
            category_key = _get_category_key(config_key)
            item_info = get_config_item_info(config_key)
            item_name = item_info['name']
            
            await query.edit_message_text(
                f"✅ 配置已更新\n\n"
                f"<b>{item_name}</b>\n"
                f"新值：<code>{value_str}</code>\n\n"
                f"{message}",
                parse_mode=ParseMode.HTML
            )
            
            # 2秒后自动返回分类视图
            import asyncio
            await asyncio.sleep(2)
            
            # 重新显示分类视图
            callback_data = f"setting_cat:{category_key}"
            context.user_data['_temp_callback'] = callback_data
            
            # 调用分类回调来显示更新后的分类页面
            await handle_setting_category_callback(update, context)
        else:
            await query.edit_message_text(
                f"❌ 配置更新失败\n\n{message}",
                parse_mode=ParseMode.HTML
            )
        
    except Exception as e:
        logger.error(f"Error in handle_setting_set_callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ 发生错误：{str(e)}")


async def handle_setting_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    处理用户输入的配置值（文本消息）
    
    Args:
        update: Telegram update
        context: Bot context
        
    Returns:
        bool: 如果处理了设置输入返回True，否则返回False
    """
    if not context.user_data.get('waiting_setting_input'):
        return False
    
    try:
        config_key = context.user_data['waiting_setting_input']
        value_str = update.message.text.strip()
        
        # 验证并设置配置
        success, message = await _set_config_value(config_key, value_str)
        
        item_info = get_config_item_info(config_key)
        item_name = item_info['name']
        category_key = _get_category_key(config_key)
        
        # 创建返回按钮
        keyboard = [[
            InlineKeyboardButton("⬅️ 返回配置分类", callback_data=f"setting_cat:{category_key}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if success:
            await update.message.reply_text(
                f"✅ 配置已更新\n\n"
                f"<b>{item_name}</b>\n"
                f"新值：<code>{value_str}</code>\n\n"
                f"{message}",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"❌ 配置更新失败\n\n{message}",
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        
        # 清除等待状态
        context.user_data.pop('waiting_setting_input', None)
        
        return True
    
    except Exception as e:
        logger.error(f"Error in handle_setting_input: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 发生错误：{str(e)}")
        context.user_data.pop('waiting_setting_input', None)
        return True


async def handle_setting_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    处理返回主菜单
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 重新显示分类菜单
        keyboard = []
        for category_key, category_info in CONFIG_CATEGORIES.items():
            icon = category_info['icon']
            name = category_info['name']
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} {name}",
                    callback_data=f"setting_cat:{category_key}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ <b>系统配置</b>\n\n"
            "请选择要配置的分类：",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error in handle_setting_back_callback: {e}", exc_info=True)
        await query.edit_message_text(f"❌ 发生错误：{str(e)}")


def _get_category_key(config_key: str) -> str:
    """
    根据配置键获取所属分类
    
    Args:
        config_key: 配置键（如 'ai.enabled'）
        
    Returns:
        分类键（如 'ai'）
    """
    for category_key, category_info in CONFIG_CATEGORIES.items():
        if config_key in category_info['items']:
            return category_key
    return 'basic'


async def _set_config_value(config_key: str, value_str: str) -> tuple[bool, str]:
    """
    设置配置值并写入文件
    
    Args:
        config_key: 配置键
        value_str: 值字符串
        
    Returns:
        (是否成功, 消息)
    """
    try:
        # 验证值
        is_valid, converted_value, error_msg = validate_config_value(config_key, value_str)
        if not is_valid:
            return False, error_msg
        
        # 读取配置文件
        import os
        config_path = os.path.join(os.path.dirname(__file__), '../../../config/config.yaml')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 更新配置值（支持嵌套键）
        keys = config_key.split('.')
        current = config_data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 设置最终值
        current[keys[-1]] = converted_value
        
        # 写回配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration updated: {config_key} = {converted_value}")
        
        return True, "⚠️ 注意：部分配置需要重启Bot才能生效"
    
    except Exception as e:
        logger.error(f"Error setting config value: {e}", exc_info=True)
        return False, f"写入配置文件失败：{str(e)}"
