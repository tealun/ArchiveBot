"""
系统功能相关的消息格式化器
处理垃圾箱、AI状态、配置菜单、统计信息等格式化
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
                
                # 优先从环境变量读取，否则从配置文件读取
                import os
                provider = os.getenv('AI_API_PROVIDER') or api_config.get('provider', '') or 'unknown'
                model = os.getenv('AI_MODEL') or api_config.get('model', '') or 'unknown'
                base_url = os.getenv('AI_API_URL') or api_config.get('api_url', '') or api_config.get('base_url', 'default')
                
                # API Key处理
                api_key = os.getenv('AI_API_KEY') or api_config.get('api_key', '')
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
                chat_enabled = ai_config.get('chat_enabled', False)  # 修正：直接从ai_config读取
                
                status_text += f"  • 自动摘要：{'✅ 开启' if auto_summarize else '❌ 关闭'}\n"
                status_text += f"  • 自动标签：{'✅ 开启' if auto_tags else '❌ 关闭'}\n"
                status_text += f"  • 自动分类：{'✅ 开启' if auto_category else '❌ 关闭'}\n"
                status_text += f"  • 智能对话：{'✅ 开启' if chat_enabled else '❌ 关闭'}\n\n"
                
                db_storage = context.bot_data.get('db_storage')
                if db_storage:
                    try:
                        # 查询基本统计
                        cursor = db_storage.db.execute("""
                            SELECT 
                                COUNT(*) as total,
                                COUNT(CASE WHEN ai_summary IS NOT NULL AND ai_summary != '' THEN 1 END) as with_summary,
                                COUNT(CASE WHEN ai_key_points IS NOT NULL AND ai_key_points != '' THEN 1 END) as with_key_points,
                                COUNT(CASE WHEN ai_category IS NOT NULL AND ai_category != '' THEN 1 END) as with_category
                            FROM archives
                            WHERE deleted = 0
                        """)
                        stats = cursor.fetchone()
                        
                        total = stats[0]
                        with_summary = stats[1]
                        with_key_points = stats[2]
                        with_category = stats[3]
                        
                        # 查询AI生成的标签数量（标签类型为'ai'）
                        cursor = db_storage.db.execute("""
                            SELECT COUNT(DISTINCT at.archive_id)
                            FROM archive_tags at
                            INNER JOIN tags t ON at.tag_id = t.id
                            INNER JOIN archives a ON at.archive_id = a.id
                            WHERE t.tag_type = 'ai' AND a.deleted = 0
                        """)
                        with_ai_tags = cursor.fetchone()[0]
                        
                        status_text += "📊 **使用统计：**\n"
                        status_text += f"  • 总归档数：`{total}`\n"
                        status_text += f"  • AI摘要：`{with_summary}` ({int(with_summary/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI标签：`{with_ai_tags}` ({int(with_ai_tags/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI关键点：`{with_key_points}` ({int(with_key_points/total*100) if total > 0 else 0}%)\n"
                        status_text += f"  • AI分类：`{with_category}` ({int(with_category/total*100) if total > 0 else 0}%)\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to get AI usage stats: {e}", exc_info=True)
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
        
        keyboard = []
        
        if item_type == 'bool':
            # 布尔类型：显示状态和切换按钮
            status_text = "✅ 已启用" if current_value else "❌ 已禁用"
            text += f"当前状态：{status_text}\n"
            
            # 根据当前状态显示相反的操作按钮
            if current_value:
                keyboard = [
                    [InlineKeyboardButton("❌ 禁用", callback_data=f"setting_set:{config_key}:false")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data=f"setting_cat:{category_key}")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("✅ 启用", callback_data=f"setting_set:{config_key}:true")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data=f"setting_cat:{category_key}")]
                ]
        
        elif item_type == 'int':
            text += f"当前值：<code>{current_value}</code>\n\n"
            
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
            text += f"当前值：<code>{current_value}</code>\n\n"
            
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
    
    @staticmethod
    def format_stats(stats: Dict[str, Any], language: str = 'zh-CN', db_size: int = 0) -> str:
        """
        格式化统计信息文本
        
        Args:
            stats: 统计数据字典
            language: 语言代码
            db_size: 数据库文件大小（字节）
            
        Returns:
            格式化后的统计文本
        """
        from ..helpers import format_file_size
        from ..i18n import I18n
        
        i18n = I18n(language)
        
        total_archives = stats.get('total_archives', 0) or stats.get('total', 0)
        total_tags = stats.get('total_tags', 0) or stats.get('tags', 0)
        total_size = format_file_size(stats.get('total_size', 0))
        db_size_formatted = format_file_size(db_size) if db_size > 0 else None
        last_archive = stats.get('last_archive', 'N/A')
        
        # 获取类型统计
        type_stats = stats.get('type_stats', {})
        
        if db_size_formatted:
            # 完整版本（命令使用）
            message = i18n.t(
                'stats',
                total_archives=total_archives,
                total_tags=total_tags,
                storage_used=total_size,
                db_size=db_size_formatted,
                last_archive=last_archive
            )
            
            # 添加类型统计
            if type_stats:
                message += "\n\n📂 **类型统计：**\n"
                type_emoji = {
                    'text': '📝',
                    'link': '🔗',
                    'image': '🖼️',
                    'video': '🎬',
                    'audio': '🎵',
                    'voice': '🎤',
                    'document': '📄',
                    'ebook': '📚',
                    'animation': '🎞️',
                    'sticker': '🎭',
                    'contact': '👤',
                    'location': '📍'
                }
                
                # 按数量排序
                sorted_types = sorted(type_stats.items(), key=lambda x: x[1], reverse=True)
                for content_type, count in sorted_types:
                    emoji = type_emoji.get(content_type, '📦')
                    percentage = int(count / total_archives * 100) if total_archives > 0 else 0
                    message += f"  {emoji} {content_type}: `{count}` ({percentage}%)\n"
            
            # 添加笔记统计
            total_notes = stats.get('total_notes', 0)
            linked_notes = stats.get('linked_notes', 0)
            standalone_notes = stats.get('standalone_notes', 0)
            
            if total_notes > 0:
                message += "\n📝 **笔记统计：**\n"
                message += f"  • 总笔记数：`{total_notes}`\n"
                message += f"  • 关联笔记：`{linked_notes}` ({int(linked_notes/total_notes*100) if total_notes > 0 else 0}%)\n"
                message += f"  • 独立笔记：`{standalone_notes}` ({int(standalone_notes/total_notes*100) if total_notes > 0 else 0}%)\n"
        else:
            # 简化版本（AI对话使用）
            if language == 'en':
                message = f"📊 Statistics:\n"
                message += f"• Archives: {total_archives}\n"
                message += f"• Tags: {total_tags}\n"
                message += f"• Storage: {total_size}"
            elif language == 'zh-TW':
                message = f"📊 統計資訊：\n"
                message += f"• 歸檔數：{total_archives}\n"
                message += f"• 標籤數：{total_tags}\n"
                message += f"• 存儲：{total_size}"
            else:
                message = f"📊 统计信息：\n"
                message += f"• 归档数：{total_archives}\n"
                message += f"• 标签数：{total_tags}\n"
                message += f"• 存储：{total_size}"
        
        return message
    
    @staticmethod
    def format_search_results_summary(
        results: List[Dict], 
        total_count: int, 
        query: str,
        language: str = 'zh-CN',
        max_items: int = 5
    ) -> str:
        """
        格式化搜索结果摘要（AI对话用）
        
        Args:
            results: 搜索结果列表
            total_count: 总结果数
            query: 搜索关键词
            language: 语言代码
            max_items: 最多显示项数
            
        Returns:
            格式化后的搜索结果摘要文本
        """
        if not results:
            if language == 'en':
                return f"🔍 No results found for '{query}'"
            elif language == 'zh-TW':
                return f"🔍 沒有找到關於「{query}」的結果"
            else:
                return f"🔍 没有找到关于「{query}」的结果"
        
        if language == 'en':
            text = f"🔍 Found {total_count} result(s) for '{query}':\n\n"
        elif language == 'zh-TW':
            text = f"🔍 找到 {total_count} 個關於「{query}」的結果：\n\n"
        else:
            text = f"🔍 找到 {total_count} 个关于「{query}」的结果：\n\n"
        
        for i, item in enumerate(results[:max_items], 1):
            title = item.get('title', 'No title' if language == 'en' else '無標題' if language == 'zh-TW' else '无标题')
            if len(title) > 50:
                title = title[:50] + '...'
            text += f"{i}. {title}\n"
        
        if total_count > max_items:
            if language == 'en':
                text += f"\n... and {total_count - max_items} more"
            elif language == 'zh-TW':
                text += f"\n...還有 {total_count - max_items} 個"
            else:
                text += f"\n...还有 {total_count - max_items} 个"
        
        return text
    
    @staticmethod
    def format_tag_analysis(
        tags: List[Dict], 
        language: str = 'zh-CN',
        max_tags: int = 10
    ) -> str:
        """
        格式化标签分析文本
        
        Args:
            tags: 标签列表
            language: 语言代码
            max_tags: 最多显示标签数
            
        Returns:
            格式化后的标签分析文本
        """
        if not tags:
            if language == 'en':
                return "No tags available"
            elif language == 'zh-TW':
                return "暫無標籤"
            else:
                return "暂无标签"
        
        tag_texts = []
        for tag in tags[:max_tags]:
            tag_name = tag.get('tag') or tag.get('tag_name')
            count = tag.get('count', 0)
            tag_texts.append(f"#{tag_name}({count})")
        
        if language == 'en':
            header = f"🏷️ Top {len(tag_texts)} Tags:\n"
        elif language == 'zh-TW':
            header = f"🏷️ 熱門標籤 TOP {len(tag_texts)}：\n"
        else:
            header = f"🏷️ 热门标签 TOP {len(tag_texts)}：\n"
        
        return header + ' '.join(tag_texts)
    
    @staticmethod
    def format_recent_archives(
        archives: List[Dict],
        language: str = 'zh-CN',
        max_items: int = 5
    ) -> str:
        """
        格式化最近归档列表
        
        Args:
            archives: 归档列表
            language: 语言代码
            max_items: 最多显示条数
            
        Returns:
            格式化后的最近归档文本
        """
        if not archives:
            if language == 'en':
                return "No recent archives"
            elif language == 'zh-TW':
                return "暫無最近歸檔"
            else:
                return "暂无最近归档"
        
        if language == 'en':
            header = f"📚 Recent {len(archives[:max_items])} Archives:\n"
        elif language == 'zh-TW':
            header = f"📚 最近 {len(archives[:max_items])} 條歸檔：\n"
        else:
            header = f"📚 最近 {len(archives[:max_items])} 条归档：\n"
        
        text = header
        for archive in archives[:max_items]:
            title = archive.get('title', '')
            if len(title) > 40:
                title = title[:40] + '...'
            text += f"• {title}\n"
        
        return text
    
    @staticmethod
    def format_ai_context_summary(
        data_context: Dict[str, Any],
        user_intent: str,
        language: str = 'zh-CN'
    ) -> str:
        """
        格式化AI上下文数据摘要
        
        Args:
            data_context: AI收集的数据上下文
            user_intent: 用户意图类型
            language: 语言代码
            
        Returns:
            格式化后的数据摘要文本
        """
        parts = []
        
        show_stats = user_intent in ['specific_search', 'stats_analysis', 'resource_request']
        
        if data_context.get('statistics') and show_stats:
            stats = data_context['statistics']
            parts.append(SystemFormatter.format_stats(stats, language, db_size=0))
            
            if data_context.get('onboarding_hint'):
                parts.append(data_context['onboarding_hint'])
            if data_context.get('tagging_hint'):
                parts.append(data_context['tagging_hint'])
        
        if data_context.get('search_results'):
            results = data_context['search_results']
            query = data_context.get('search_query', '')
            parts.append(SystemFormatter.format_search_results_summary(results, len(results), query, language))
            
            if data_context.get('filter_suggestions'):
                parts.append(data_context['filter_suggestions'])
            if data_context.get('expand_suggestions'):
                parts.append(data_context['expand_suggestions'])
            if data_context.get('empty_result_suggestions'):
                parts.append(data_context['empty_result_suggestions'])
        
        if data_context.get('tag_analysis'):
            tags = data_context['tag_analysis']
            parts.append(SystemFormatter.format_tag_analysis(tags, language))
        
        if data_context.get('sample_archives'):
            archives = data_context['sample_archives']
            parts.append(SystemFormatter.format_recent_archives(archives, language))
        
        if data_context.get('notes'):
            from .note_formatter import NoteFormatter
            notes = data_context['notes']
            parts.append(NoteFormatter.format_ai_summary(notes, language))
        
        if data_context.get('no_resource_hint'):
            parts.append(data_context['no_resource_hint'])
        if data_context.get('next_hint'):
            parts.append(data_context['next_hint'])
        
        if not parts:
            if language == 'en':
                return "No relevant data available"
            elif language == 'zh-TW':
                return "暫無相關數據"
            else:
                return "暂无相关数据"
        
        return '\n\n'.join(parts)
