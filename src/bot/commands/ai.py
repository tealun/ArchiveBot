"""
Ai commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...ai.summarizer import get_ai_summarizer

@with_language_context
async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /ai command - 显示AI功能状态
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        config = get_config()
        ai_config = config.ai
        
        status_text = "🤖 **AI 功能状态**\n\n"
        
        # 检查是否启用
        if ai_config.get('enabled', False):
            status_text += "✅ **状态：** 已启用\n\n"
            
            # 获取AI总结器
            summarizer = get_ai_summarizer(ai_config)
            
            if summarizer and summarizer.is_available():
                status_text += "🟢 **服务：** 可用\n\n"
                
                # API配置信息
                api_config = ai_config.get('api', {})
                provider = api_config.get('provider', 'unknown')
                model = api_config.get('model', 'unknown')
                base_url = api_config.get('base_url', 'default')
                
                # 脱敏处理API Key
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
                
                # 功能开关
                status_text += "🔧 **功能开关：**\n"
                auto_summarize = ai_config.get('auto_summarize', False)
                auto_tags = ai_config.get('auto_generate_tags', False)
                auto_category = ai_config.get('auto_category', False)
                chat_enabled = ai_config.get('chat', {}).get('enabled', False)
                
                status_text += f"  • 自动摘要：{'✅ 开启' if auto_summarize else '❌ 关闭'}\n"
                status_text += f"  • 自动标签：{'✅ 开启' if auto_tags else '❌ 关闭'}\n"
                status_text += f"  • 自动分类：{'✅ 开启' if auto_category else '❌ 关闭'}\n"
                status_text += f"  • 智能对话：{'✅ 开启' if chat_enabled else '❌ 关闭'}\n\n"
                
                # 使用统计（从数据库获取）
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
                
                # 对话会话信息
                if chat_enabled:
                    session_manager = context.bot_data.get('session_manager')
                    if session_manager:
                        user_id = update.effective_user.id
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
                
                # 缓存信息
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
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"AI status command executed")
        
    except Exception as e:
        logger.error(f"Error in ai_status_command: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 获取AI状态失败: {str(e)}")
