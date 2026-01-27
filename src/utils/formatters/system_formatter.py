"""
系统功能相关的消息格式化器
处理垃圾箱、AI状态、配置菜单等格式化
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class SystemFormatter:
    """系统格式化器 - 处理系统功能相关的消息格式化"""
    
    @staticmethod
    def format_trash_list(
        items: List[Dict[str, Any]],
        lang_ctx,
        max_display: int = 20
    ) -> str:
        """
        格式化垃圾箱列表
        
        Args:
            items: 垃圾箱项目列表
            lang_ctx: 语言上下文
            max_display: 最大显示数量
            
        Returns:
            格式化的消息文本
        """
        count = len(items)
        
        if count == 0:
            return lang_ctx.t('trash_empty')
        
        result_text = lang_ctx.t('trash_list', count=count) + "\n\n"
        
        for item in items[:max_display]:
            result_text += f"🗑️ ID: #{item['id']}\n"
            result_text += f"📝 {item['title']}\n"
            result_text += f"🏷️ {', '.join(item['tags'][:3])}{'...' if len(item['tags']) > 3 else ''}\n"
            result_text += f"🕐 {lang_ctx.t('deleted_at')}: {item['deleted_at']}\n\n"
        
        if count > max_display:
            result_text += lang_ctx.t('trash_more', count=count - max_display)
        
        return result_text
    
    @staticmethod
    def format_ai_status(
        ai_config: Dict[str, Any],
        context,
        lang_ctx
    ) -> str:
        """
        格式化AI功能状态显示
        
        Args:
            ai_config: AI配置
            context: Bot context
            lang_ctx: 语言上下文
            
        Returns:
            格式化的状态文本（Markdown格式）
        """
        from ...ai.summarizer import get_ai_summarizer
        
        status_text = "🤖 **AI 功能状态**\n\n"
        
        if ai_config.get('enabled', False):
            status_text += "✅ **状态：** 已启用\n\n"
            
            summarizer = get_ai_summarizer(ai_config)
            
            if summarizer and summarizer.is_available():
                status_text += "🟢 **服务：** 可用\n\n"
                
                api_config = ai_config.get('api', {})
                provider = api_config.get('provider', 'unknown')
                model = api_config.get('model', 'unknown')
                base_url = api_config.get('base_url', 'default')
                
                api_key = api_config.get('api_key', '')
                if api_key:
                    if len(api_key) > 10:
                        masked_key = api_key[:4] + '****' + api_key[-4:]
                    else:
                        masked_key = '****'
                else:
                    masked_key = '未设置'
                
                status_text += "⚙️ **配置信息：**\n"
                status_text += f"  • 提供商：`{provider}`\n"
                status_text += f"  • 模型：`{model}`\n"
                status_text += f"  • API Key：`{masked_key}`\n"
                status_text += f"  • Base URL：`{base_url}`\n"
                status_text += f"  • 最大Token：`{api_config.get('max_tokens', 1000)}`\n"
                status_text += f"  • 超时时间：`{api_config.get('timeout', 30)}秒`\n"
                status_text += f"  • 温度参数：`{api_config.get('temperature', 0.7)}`\n\n"
                
                status_text += "🔧 **功能开关：**\n"
                auto_summarize = ai_config.get('auto_summarize', False)
                auto_tags = ai_config.get('auto_generate_tags', False)
                auto_category = ai_config.get('auto_category', False)
                chat_enabled = ai_config.get('chat', {}).get('enabled', False)
                
                status_text += f"  • 自动摘要：{'✅ 开启' if auto_summarize else '❌ 关闭'}\n"
                status_text += f"  • 自动标签：{'✅ 开启' if auto_tags else '❌ 关闭'}\n"
                status_text += f"  • 自动分类：{'✅ 开启' if auto_category else '❌ 关闭'}\n"
                status_text += f"  • 智能对话：{'✅ 开启' if chat_enabled else '❌ 关闭'}\n\n"
                
                db_storage = context.bot_data.get('db_storage')
                if db_storage:
                    try:
                        cursor = db_storage.db.execute("""
                            SELECT 
                                COUNT(*) as total,
                                COUNT(CASE WHEN ai_summary IS NOT NULL THEN 1 END) as with_summary,
                                COUNT(CASE WHEN ai_tags IS NOT NULL THEN 1 END) as with_tags,
                                COUNT(CASE WHEN ai_category IS NOT NULL THEN 1 END) as with_category
                            FROM archives
                            WHERE deleted = 0
                        """)
                        stats = cursor.fetchone()
                        
                        total = stats[0]
                        with_summary = stats[1]
                        with_tags = stats[2]
                        with_category = stats[3]
                        
                        status_text += "📊 **使用统计：**\n"
                        status_text += f"  • 总归档数：`{total}`\n"
                        status_text += f"  • AI摘要：`{with_summary}` ({int(with_summary/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI标签：`{with_tags}` ({int(with_tags/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI分类：`{with_category}` ({int(with_category/total*100) if total > 0 else 0}%)\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to get AI usage stats: {e}")
                        status_text += "📊 **使用统计：** 无法获取\n\n"
                
                if chat_enabled:
                    session_manager = context.bot_data.get('session_manager')
                    if session_manager:
                        user_id = context._user_id if hasattr(context, '_user_id') else None
                        if user_id:
                            session = session_manager.get_session(user_id)
                            if session:
                                status_text += "💬 **对话会话：**\n"
                                status_text += f"  • 状态：活跃\n"
                                status_text += f"  • 消息数：`{session.get('message_count', 0)}`\n"
                                last_time = session.get('last_interaction')
                                if last_time:
                                    status_text += f"  • 最后交互：`{last_time}`\n"
                            else:
                                status_text += "💬 **对话会话：** 无活跃会话\n"
                            status_text += "\n"
                
                ai_cache = context.bot_data.get('ai_cache')
                if ai_cache:
                    try:
                        cache_stats = ai_cache.get_stats()
                        status_text += "💾 **缓存统计：**\n"
                        status_text += f"  • 缓存条目：`{cache_stats.get('total_entries', 0)}`\n"
                        status_text += f"  • 命中率：`{cache_stats.get('hit_rate', 0):.1f}%`\n"
                        status_text += f"  • 缓存大小：`{cache_stats.get('size_mb', 0):.2f} MB`\n"
                    except Exception as e:
                        logger.warning(f"Failed to get cache stats: {e}")
                
            else:
                status_text += "🔴 **服务：** 不可用\n\n"
                status_text += "⚠️ AI服务连接失败，请检查配置\n"
        else:
            status_text += "❌ **状态：** 未启用\n\n"
            status_text += "💡 **启用指南：**\n"
            status_text += "1. 编辑 `config/config.yaml`\n"
            status_text += "2. 设置 `ai.enabled: true`\n"
            status_text += "3. 配置API密钥和提供商\n"
            status_text += "4. 重启Bot\n"
        
        return status_text
    
    @staticmethod
    def format_setting_category_menu(
        category_key: str,
        category_info: Dict[str, Any],
        config_getter
    ) -> tuple[str, Any]:
        """
        格式化配置分类菜单
        
        Args:
            category_key: 分类键
            category_info: 分类信息
            config_getter: 获取配置值的函数
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup)
        """
        category_name = category_info['name']
        category_icon = category_info['icon']
        items = category_info['items']
        
        text = f"{category_icon} <b>{category_name}</b>\n\n"
        text += "选择要配置的项目：\n\n"
        
        keyboard = []
        for config_key, item_info in items.items():
            item_name = item_info['name']
            current_value = config_getter(config_key)
            
            if item_info['type'] == 'bool':
                value_display = "✅" if current_value else "❌"
            else:
                value_display = str(current_value) if current_value is not None else "未设置"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{item_name} [{value_display}]",
                    callback_data=f"setting_item:{config_key}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("⬅️ 返回", callback_data="setting_back")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return text, reply_markup
    
    @staticmethod
    def format_setting_item_prompt(
        item_info: Dict[str, Any],
        config_key: str,
        current_value: Any,
        category_key: str
    ) -> tuple[str, Any]:
        """
        格式化配置项输入提示
        
        Args:
            item_info: 配置项信息
            config_key: 配置键
            current_value: 当前值
            category_key: 所属分类键
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup或None)
        """
        item_name = item_info['name']
        item_type = item_info['type']
        description = item_info.get('description', '')
        
        text = f"⚙️ <b>{item_name}</b>\n\n"
        text += f"📝 {description}\n\n"
        text += f"当前值：<code>{current_value}</code>\n\n"
        
        keyboard = []
        
        if item_type == 'bool':
            text += "请输入新值：\n"
            text += "• true/false\n"
            text += "• yes/no\n"
            text += "• 1/0\n"
            text += "• 开/关"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ 启用", callback_data=f"setting_set:{config_key}:true"),
                    InlineKeyboardButton("❌ 禁用", callback_data=f"setting_set:{config_key}:false")
                ],
                [
                    InlineKeyboardButton("⬅️ 返回", callback_data=f"setting_cat:{category_key}")
                ]
            ]
        
        elif item_type == 'int':
            min_val = item_info.get('min')
            max_val = item_info.get('max')
            default_val = item_info.get('default')
            
            text += "请输入新值（整数）：\n"
            if min_val is not None:
                text += f"• 最小值：{min_val}\n"
            if max_val is not None:
                text += f"• 最大值：{max_val}\n"
            if default_val is not None:
                text += f"• 默认值：{default_val}\n"
            
            text += f"\n💡 直接回复数字即可"
            
            keyboard = [[
                InlineKeyboardButton("⬅️ 返回", callback_data=f"setting_cat:{category_key}")
            ]]
        
        elif item_type == 'string':
            example = item_info.get('example', '')
            
            text += "请输入新值（文本）：\n"
            if example:
                text += f"• 示例：<code>{example}</code>\n"
            
            text += f"\n💡 直接回复文本即可"
            
            keyboard = [[
                InlineKeyboardButton("⬅️ 返回", callback_data=f"setting_cat:{category_key}")
            ]]
        
        elif item_type == 'choice':
            choices = item_info.get('choices', [])
            default_val = item_info.get('default')
            
            text += "请选择新值：\n"
            for choice in choices:
                text += f"• {choice}\n"
            if default_val:
                text += f"\n默认值：{default_val}\n"
            
            keyboard = []
            for choice in choices:
                keyboard.append([
                    InlineKeyboardButton(
                        choice,
                        callback_data=f"setting_set:{config_key}:{choice}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("⬅️ 返回", callback_data=f"setting_cat:{category_key}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        return text, reply_markup
