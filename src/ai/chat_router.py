"""
AI Chat Router

Handles AI interactive chat mode with 3-stage processing:
1. Understand user intent and plan response
2. Gather required data
3. Generate final response

Uses language context for multi-language support.
"""
from __future__ import annotations

import logging
import re
import json
import httpx
from typing import Optional, Dict, Any

from .prompts.chat import ChatPrompts
from ..utils.config import get_config

logger = logging.getLogger(__name__)


async def understand_and_plan(user_message: str, language: str, context: Any, stats: dict = None) -> Dict[str, Any]:
    """
    让AI理解用户真实需求并规划如何回答
    
    Args:
        user_message: 用户消息
        language: 用户语言 (zh-CN, zh-TW, en)
        context: Bot context
        stats: 归档系统统计数据
    
    Returns:
        AI规划结果
    """
    try:
        config = get_config()
        
        # 检查是否启用推理模型（默认启用）
        use_reasoning = config.ai.get('chat_use_reasoning', True)
        if not use_reasoning:
            # 不使用推理模型，返回简单响应策略
            logger.info("🧠 AI reasoning disabled, using simple reply strategy")
            return {
                'user_goal': 'general_chat',
                'need_data': {},
                'response_strategy': 'simple_reply',
                'reasoning': 'reasoning disabled'
            }
        
        # 使用 config.get() 方法以支持环境变量（AI_API_KEY）
        api_key = config.get('ai.api.api_key') or config.ai.get('api', {}).get('api_key')
        api_url = config.get('ai.api.api_url') or config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        reasoning_model = config.get('ai.api.reasoning_model') or config.ai.get('api', {}).get('reasoning_model', 'grok-4-1-fast-reasoning')
        temperature = config.get('ai.api.temperature', 0.7)  # 从配置读取，默认0.7
        
        # 使用提示词模板
        understanding_prompt = ChatPrompts.get_understanding_prompt(user_message, language, stats)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": reasoning_model,
                    "messages": [{"role": "user", "content": understanding_prompt}],
                    "max_tokens": 300,
                    "temperature": temperature * 0.57  # 意图分析需要更低的温度（0.7 * 0.57 ≈ 0.4）
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                ai_response = re.sub(r'^```json\s*|\s*```$', '', ai_response, flags=re.MULTILINE).strip()
                
                # 调试：输出原始AI响应
                logger.debug(f"AI raw response: {ai_response[:500]}")
                
                try:
                    plan = json.loads(ai_response)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {e}")
                    logger.error(f"Raw response: {ai_response}")
                    return {
                        'user_goal': 'general_chat',
                        'user_intent': 'pure_chat',
                        'need_data': {},
                        'response_strategy': 'simple_reply'
                    }
                
                user_intent = plan.get('user_intent', 'unknown')
                user_goal = plan.get('user_goal', 'unknown')
                response_strategy = plan.get('response_strategy', 'unknown')
                reasoning = plan.get('reasoning', '')
                
                # 如果没有user_intent字段，根据response_strategy降级推断
                if 'user_intent' not in plan:
                    logger.warning(f"⚠️ AI response missing 'user_intent' field! Inferring from strategy...")
                    logger.debug(f"Plan keys: {list(plan.keys())}")
                    
                    # 降级映射：strategy -> intent
                    strategy_to_intent = {
                        'clarify': 'pure_chat',           # 打招呼、澄清问题
                        'direct_answer': 'general_query',  # 简单直接回答
                        'search_results': 'specific_search', # 搜索结果
                        'data_analysis': 'stats_analysis',   # 数据分析
                        'resource_reply': 'resource_request' # 资源回复
                    }
                    
                    inferred_intent = strategy_to_intent.get(response_strategy, 'general_query')
                    plan['user_intent'] = inferred_intent
                    user_intent = inferred_intent
                    logger.info(f"✓ Inferred intent: {user_intent} (from strategy: {response_strategy})")
                
                logger.info(f"🧠 AI Understanding:")
                logger.info(f"  Intent: {user_intent}")
                logger.info(f"  Goal: {user_goal}")
                logger.info(f"  Strategy: {response_strategy}")
                if reasoning:
                    logger.info(f"  Reasoning: {reasoning}")
                
                return plan
            else:
                logger.warning(f"Understanding API error: {response.status_code}")
                return {
                    'user_goal': 'general_chat',
                    'need_data': {},
                    'response_strategy': 'simple_reply',
                    'reasoning': 'API error'
                }
                
    except json.JSONDecodeError as e:
        logger.error(f"Understanding JSON parse error: {e}")
        return {'user_goal': 'general_chat', 'need_data': {}, 'response_strategy': 'simple_reply'}
    except Exception as e:
        logger.error(f"Understanding error: {e}", exc_info=True)
        return {'user_goal': 'general_chat', 'need_data': {}, 'response_strategy': 'simple_reply'}


async def handle_chat_message(
    user_message: str,
    session_data: Dict[str, Any],
    context: Any,
    language: str = 'auto',
    progress_callback=None
) -> str:
    """
    Handle message in AI chat mode - 智能理解与响应流程
    
    Stage 1: AI理解用户真实需求并规划回答
    Stage 2: 获取需要的数据
    Stage 3: AI基于数据生成最终回复
    
    Args:
        user_message: User's message text
        session_data: Current session context
        context: Bot context (has bot_data with managers)
        language: User's language preference ('auto' = AI自动判断语言)
        progress_callback: Optional callback for progress updates
        
    Returns:
        AI response text
    """
    from ..utils.i18n import I18n
    # 对于AI聊天，使用'auto'允许AI自动判断回复语言
    # 只有在退出/帮助等固定消息时才需要i18n
    i18n = I18n(language if language != 'auto' else 'zh-CN')
    
    # 简单命令直接处理
    text_lower = user_message.lower().strip()
    if text_lower in ['退出', '結束', '结束', 'exit', 'quit', 'bye', '再见', '再見']:
        # 对于退出消息，使用用户实际的语言（如果是auto则用zh-CN）
        actual_lang = language if language != 'auto' else 'zh-CN'
        return handle_exit(actual_lang)
    if text_lower in ['帮助', '幫助', 'help', '?', '？']:
        actual_lang = language if language != 'auto' else 'zh-CN'
        return handle_help(actual_lang)
    
    # Stage 1: AI理解需求并规划
    logger.info(f"🧠 Stage 1: Understanding user need...")
    if progress_callback:
        await progress_callback(i18n.t('ai_chat_understanding'))
    
    # 获取统计数据
    stats = None
    try:
        ai_cache = context.bot_data.get('ai_data_cache')
        if ai_cache:
            stats = ai_cache.get_statistics()
    except Exception as e:
        logger.debug(f"Failed to get stats: {e}")
    
    plan = await understand_and_plan(user_message, language, context, stats)
    
    user_goal = plan.get('user_goal', '')
    user_intent = plan.get('user_intent', 'general_query')
    
    if '退出' in user_goal or '結束' in user_goal or 'exit' in user_goal.lower():
        return handle_exit(language)
    if '帮助' in user_goal or '幫助' in user_goal or 'help' in user_goal.lower():
        return handle_help(language)
    
    # 处理 command_request 意图（操作指令）
    if user_intent == 'command_request':
        logger.info(f"⚙️ Command request detected: {plan.get('command_type', 'unknown')}")
        return await handle_command_request(plan, context, language)
    
    # 处理 contextual_reference 意图（上下文引用）
    if user_intent == 'contextual_reference':
        logger.info(f"🔗 Contextual reference detected: {plan.get('context_reference', {})}")
        return await handle_contextual_reference(plan, session_data, context, language, user_message)
    
    # 处理 clarification 意图（确认对话）
    if user_intent == 'clarification':
        logger.info(f"✅ Clarification detected: {plan.get('clarification_type', 'confirm')}")
        return await handle_clarification(plan, session_data, context, language, user_message)
    
    # 处理 guided_inquiry 意图（引导式探询）
    if user_intent == 'guided_inquiry':
        logger.info(f"📚 Guided inquiry detected: {plan.get('inquiry_params', {})}")
        return await handle_guided_inquiry(plan, session_data, context, language, user_message)
    
    # Stage 2: 根据规划和意图获取数据
    logger.info(f"📊 Stage 2: Gathering data (intent: {user_intent})...")
    if progress_callback and user_intent != 'pure_chat':
        await progress_callback(i18n.t('ai_chat_gathering'))
    data_context = await gather_data(plan.get('need_data', {}), context, user_intent)
    
    # Stage 2.5: 智能优化数据上下文（添加建议和提示）
    from .response_optimizer import ResponseOptimizer
    data_context = ResponseOptimizer.optimize(user_intent, data_context, user_message, language)
    logger.info(f"✨ Data context optimized with intelligent suggestions")
    
    # Stage 3: AI生成最终回复
    logger.info(f"💬 Stage 3: Generating response...")
    if progress_callback:
        await progress_callback(i18n.t('ai_chat_generating'))
    return await generate_response(user_message, plan, data_context, session_data, context, language)


def handle_exit(language: str) -> str:
    """Handle exit intent"""
    from ..utils.i18n import I18n
    i18n = I18n(language)
    return i18n.t('ai_chat_exit')


def handle_help(language: str) -> str:
    """Handle help intent"""
    from ..utils.i18n import I18n
    i18n = I18n(language)
    return i18n.t('ai_chat_help')


async def handle_command_request(plan: Dict[str, Any], context: Any, language: str) -> str:
    """
    处理操作指令意图（command_request）
    
    Phase 1: Safe read-only operations (search, stats, tags, notes, review) - execute directly
    Phase 2: Write operations (create_note, add_tag, etc.) - require confirmation
    Phase 3: Dangerous operations (delete, trash, export, backup) - forbidden
    
    Args:
        plan: AI 理解规划结果
        context: Bot context
        language: 语言代码
        
    Returns:
        执行结果消息
    """
    from ..utils.i18n import I18n
    from .operations.safe_executor import execute_safe_operation
    
    i18n = I18n(language)
    
    command_type = plan.get('command_type', 'unknown')
    command_params = plan.get('command_params', {})
    
    # Phase 1: Safe operations - execute directly
    SAFE_OPERATIONS = ['search', 'stats', 'tags', 'notes', 'review']
    
    if command_type in SAFE_OPERATIONS:
        logger.info(f"🤖 AI executing safe operation: {command_type}")
        success, message, data = await execute_safe_operation(
            operation_type=command_type,
            operation_params=command_params,
            context=context,
            language=language
        )
        
        if success and data:
            # Format data for user-friendly display
            if command_type == 'search' and data.get('results'):
                # Format search results
                results_text = _format_search_results(data['results'], language)
                return f"{message}\n\n{results_text}"
            
            elif command_type == 'stats':
                # Format statistics
                stats_text = _format_stats(data, language)
                return f"{message}\n\n{stats_text}"
            
            elif command_type == 'tags' and data.get('tags'):
                # Format tags list
                tags_text = _format_tags(data['tags'], language)
                return f"{message}\n\n{tags_text}"
            
            elif command_type == 'notes' and data.get('notes'):
                # Format notes list
                notes_text = _format_notes(data['notes'], language)
                return f"{message}\n\n{notes_text}"
            
            elif command_type == 'review' and data.get('archive'):
                # Format review archive
                review_text = _format_review(data, language)
                return f"{message}\n\n{review_text}"
        
        return message
    
    # Phase 2: Write operations - require confirmation
    WRITE_OPERATIONS = ['create_note', 'add_tag', 'remove_tag', 'toggle_favorite']
    
    if command_type in WRITE_OPERATIONS:
        logger.info(f"🤖 AI requesting write operation with confirmation: {command_type}")
        
        # Generate confirmation using existing pending_action mechanism
        import uuid
        from datetime import datetime
        
        confirmation_id = str(uuid.uuid4())[:8]
        
        # Store pending action in context
        if 'pending_actions' not in context.user_data:
            context.user_data['pending_actions'] = {}
        
        context.user_data['pending_actions'][confirmation_id] = {
            'action_type': command_type,
            'params': command_params,
            'created_at': datetime.now().isoformat(),
            'language': language
        }
        
        # Generate confirmation message
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        action_descriptions = {
            'create_note': '创建笔记' if not language.startswith('zh-T') else '創建筆記',
            'add_tag': '添加标签' if not language.startswith('zh-T') else '添加標籤',
            'remove_tag': '移除标签' if not language.startswith('zh-T') else '移除標籤',
            'toggle_favorite': '切换收藏' if not language.startswith('zh-T') else '切換收藏'
        }
        
        action_desc = action_descriptions.get(command_type, command_type)
        params_str = ', '.join([f"{k}={v}" for k, v in command_params.items()])
        
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            message_text = (
                f"⚠️ 确认执行操作\n\n"
                f"🔧 操作：{action_desc}\n"
                f"📝 参数：{params_str}\n\n"
                f"请确认是否执行此操作？"
            ) if not is_traditional else (
                f"⚠️ 確認執行操作\n\n"
                f"🔧 操作：{action_desc}\n"
                f"📝 參數：{params_str}\n\n"
                f"請確認是否執行此操作？"
            )
        else:
            message_text = (
                f"⚠️ Confirm Action\n\n"
                f"🔧 Action: {action_desc}\n"
                f"📝 Parameters: {params_str}\n\n"
                f"Do you want to proceed?"
            )
        
        # Return message with confirmation callback data
        # The confirmation will be handled by executor via callback
        context.user_data['pending_confirmation_message'] = message_text
        context.user_data['pending_confirmation_id'] = confirmation_id
        
        return message_text
    
    # Phase 3: Forbidden operations - reject with explanation
    FORBIDDEN_OPERATIONS = ['delete', 'clear_trash', 'backup', 'restore_backup', 'export']
    
    if command_type in FORBIDDEN_OPERATIONS:
        logger.warning(f"🚫 AI attempted forbidden operation: {command_type}")
        
        # Log to audit trail
        _log_audit_event(
            event_type='forbidden_operation_attempt',
            operation=command_type,
            params=command_params,
            context=context,
            language=language
        )
        
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            return (
                f"🚫 出于安全考虑，此操作需要您手动执行\n\n"
                f"🔒 被拒绝的操作：{command_type}\n\n"
                f"💡 请使用对应的命令手动操作"
            ) if not is_traditional else (
                f"🚫 出於安全考慮，此操作需要您手動執行\n\n"
                f"🔒 被拒絕的操作：{command_type}\n\n"
                f"💡 請使用對應的命令手動操作"
            )
        else:
            return (
                f"🚫 For security reasons, this operation requires manual execution\n\n"
                f"🔒 Rejected operation: {command_type}\n\n"
                f"💡 Please use the corresponding command"
            )
    
    # Unknown operations - guide user to use commands
    
    command_guides = {
        'note': i18n.t('command_guide_note', language) if hasattr(i18n, 't') else "💡 使用 /note <归档ID> 添加笔记",
        'trash': i18n.t('command_guide_trash', language) if hasattr(i18n, 't') else "💡 使用 /trash 查看回收站并删除",
        'export': i18n.t('command_guide_export', language) if hasattr(i18n, 't') else "💡 使用 /export 导出数据",
        'backup': i18n.t('command_guide_backup', language) if hasattr(i18n, 't') else "💡 使用 /backup 备份或恢复数据库",
        'language': i18n.t('command_guide_language', language) if hasattr(i18n, 't') else "💡 使用 /language 切换语言",
        'tag_operation': i18n.t('command_guide_tags', language) if hasattr(i18n, 't') else "💡 使用 /tags 管理标签"
    }
    
    guide_message = command_guides.get(command_type, "")
    
    if language.startswith('zh'):
        is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
        if is_traditional:
            return f"⚙️ 收到您的操作請求！\n\n{guide_message}\n\n💬 寫入操作需要您確認後執行。"
        else:
            return f"⚙️ 收到您的操作请求！\n\n{guide_message}\n\n💬 写入操作需要您确认后执行。"
    else:
        return f"⚙️ Command request received!\n\n{guide_message}\n\n💬 Write operations require your confirmation."


def _format_search_results(results: list, language: str) -> str:
    """Format search results for display"""
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    
    if not results:
        return ""
    
    formatted = []
    for i, result in enumerate(results[:5], 1):  # Show top 5
        title = result.get('title', '无标题' if not is_traditional else '無標題')
        archive_id = result.get('id', '?')
        content_type = result.get('content_type', '未知')
        formatted.append(f"{i}. #{archive_id} - {title} ({content_type})")
    
    if len(results) > 5:
        more = len(results) - 5
        if language.startswith('zh'):
            formatted.append(f"\n...还有 {more} 个结果" if not is_traditional else f"\n...還有 {more} 個結果")
        else:
            formatted.append(f"\n...{more} more results")
    
    return "\n".join(formatted)


def _format_stats(data: dict, language: str) -> str:
    """Format statistics for display"""
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    
    if language.startswith('zh'):
        return f"📦 总归档：{data.get('total_archives', 0)}\n🏷️ 总标签：{data.get('total_tags', 0)}" if not is_traditional else f"📦 總歸檔：{data.get('total_archives', 0)}\n🏷️ 總標籤：{data.get('total_tags', 0)}"
    else:
        return f"📦 Total Archives: {data.get('total_archives', 0)}\n🏷️ Total Tags: {data.get('total_tags', 0)}"


def _format_tags(tags: list, language: str) -> str:
    """Format tags list for display"""
    if not tags:
        return ""
    
    formatted = []
    for tag in tags[:10]:  # Show top 10
        tag_name = tag.get('tag_name', '?')
        count = tag.get('count', 0)
        formatted.append(f"#{tag_name} ({count})")
    
    if len(tags) > 10:
        more = len(tags) - 10
        is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
        if language.startswith('zh'):
            formatted.append(f"...还有 {more} 个标签" if not is_traditional else f"...還有 {more} 個標籤")
        else:
            formatted.append(f"...{more} more tags")
    
    return "\n".join(formatted)


def _format_notes(notes: list, language: str) -> str:
    """Format notes list for display"""
    if not notes:
        return ""
    
    formatted = []
    for i, note in enumerate(notes[:5], 1):  # Show top 5
        content = note.get('content', '')
        note_id = note.get('id', '?')
        # Truncate long content
        if len(content) > 50:
            content = content[:50] + "..."
        formatted.append(f"{i}. #{note_id} - {content}")
    
    if len(notes) > 5:
        more = len(notes) - 5
        is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
        if language.startswith('zh'):
            formatted.append(f"\n...还有 {more} 条笔记" if not is_traditional else f"\n...還有 {more} 條筆記")
        else:
            formatted.append(f"\n...{more} more notes")
    
    return "\n".join(formatted)


def _format_review(data: dict, language: str) -> str:
    """Format review archive for display"""
    archive = data.get('archive', {})
    if not archive:
        return ""
    
    is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
    title = archive.get('title', '无标题' if not is_traditional else '無標題')
    archive_id = archive.get('id', '?')
    content_type = archive.get('content_type', '未知')
    
    if language.startswith('zh'):
        return f"📌 随机回顾\n#{archive_id} - {title}\n类型：{content_type}" if not is_traditional else f"📌 隨機回顧\n#{archive_id} - {title}\n類型：{content_type}"
    else:
        return f"📌 Random Review\n#{archive_id} - {title}\nType: {content_type}"


async def handle_contextual_reference(
    plan: Dict[str, Any], 
    session_data: Dict[str, Any],
    context: Any,
    language: str,
    user_message: str
) -> str:
    """
    处理上下文引用意图（contextual_reference）
    
    Args:
        plan: AI 理解规划结果
        session_data: 会话数据
        context: Bot context
        language: 语言代码
        user_message: 用户消息
        
    Returns:
        基于上下文的回复
    """
    from ..utils.i18n import I18n
    from ..core.ai_session import get_session_manager
    
    i18n = I18n(language)
    session_manager = get_session_manager()
    
    # 获取对话历史
    session_id = session_data.get('session_id')
    history = session_manager.get_conversation_history(session_id, limit=3) if session_id else []
    
    context_ref = plan.get('context_reference', {})
    ref_type = context_ref.get('type', 'previous_result')
    action = context_ref.get('action', 'get_more')
    
    # 如果没有历史记录
    if not history:
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_traditional:
                return "🤔 抱歉，我沒有找到之前的對話記錄。\n\n💡 您可以直接告訴我您想查找什麼內容。"
            else:
                return "🤔 抱歉，我没有找到之前的对话记录。\n\n💡 您可以直接告诉我您想查找什么内容。"
        else:
            return "🤔 Sorry, I couldn't find previous conversation history.\n\n💡 You can directly tell me what you want to find."
    
    # 获取最近一轮的上下文
    last_turn = history[-1]
    last_intent = last_turn.get('intent')
    last_result = last_turn.get('result_summary', {})
    
    # 根据引用类型和动作处理
    if action == 'get_more' and last_intent == 'resource_request':
        # "再来一个" - 重复上次的资源请求
        logger.info(f"🔄 Repeating last resource request")
        # 重新执行资源请求
        need_data = plan.get('need_data', {})
        if not need_data.get('resource_query', {}).get('enabled'):
            # 从历史中恢复资源查询参数
            need_data['resource_query'] = {
                'enabled': True,
                'type': 'random',
                'limit': 1
            }
        data_context = await gather_data(need_data, context, 'resource_request')
        from .response_optimizer import ResponseOptimizer
        data_context = ResponseOptimizer.optimize('resource_request', data_context, user_message, language)
        return await generate_response(user_message, plan, data_context, session_data, context, language)
    
    # 其他上下文引用 - 当前版本返回友好提示
    if language.startswith('zh'):
        is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
        if is_traditional:
            return f"🔗 我理解您在引用之前的內容。\n\n上一輪對話：「{last_turn.get('user_message', '')}」\n\n💡 當前版本的上下文引用功能正在完善中，請直接描述您的需求。"
        else:
            return f"🔗 我理解您在引用之前的内容。\n\n上一轮对话：「{last_turn.get('user_message', '')}」\n\n💡 当前版本的上下文引用功能正在完善中，请直接描述您的需求。"
    else:
        return f"🔗 I understand you're referring to previous content.\n\nLast conversation: \"{last_turn.get('user_message', '')}\"\n\n💡 Contextual reference features are being enhanced. Please describe your needs directly."


async def handle_clarification(
    plan: Dict[str, Any],
    session_data: Dict[str, Any],
    context: Any,
    language: str,
    user_message: str
) -> str:
    """
    处理确认对话意图（clarification）
    
    Args:
        plan: AI 理解规划结果
        session_data: 会话数据
        context: Bot context
        language: 语言代码
        user_message: 用户消息
        
    Returns:
        确认回应
    """
    from ..utils.i18n import I18n
    from ..core.ai_session import get_session_manager
    
    i18n = I18n(language)
    session_manager = get_session_manager()
    
    # 获取待确认操作
    session_id = session_data.get('session_id')
    pending_action = session_manager.get_pending_action(session_id) if session_id else None
    
    # 提取确认类型
    clarification_type = plan.get('clarification_type', 'confirm')
    
    # 如果没有待确认操作
    if not pending_action:
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_traditional:
                return "🤔 我好像沒有需要您確認的操作。\n\n💡 您可以直接告訴我您想做什麼。"
            else:
                return "🤔 我好像没有需要您确认的操作。\n\n💡 您可以直接告诉我您想做什么。"
        else:
            return "🤔 I don't have any pending action that needs your confirmation.\n\n💡 You can directly tell me what you want to do."
    
    # 提取待确认操作信息
    action_type = pending_action.get('type')
    action_params = pending_action.get('params', {})
    action_description = pending_action.get('description', '')
    
    # 根据确认类型处理
    if clarification_type == 'cancel':
        # 用户取消操作
        session_manager.clear_pending_action(session_id)
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_traditional:
                return f"✅ 已取消操作：{action_description}\n\n如有其他需要，請隨時告訴我。"
            else:
                return f"✅ 已取消操作：{action_description}\n\n如有其他需要，请随时告诉我。"
        else:
            return f"✅ Operation cancelled: {action_description}\n\nLet me know if you need anything else."
    
    elif clarification_type == 'reject':
        # 用户拒绝操作
        session_manager.clear_pending_action(session_id)
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_traditional:
                return f"✅ 好的，我不會執行這個操作。\n\n如有其他需要，請隨時告訴我。"
            else:
                return f"✅ 好的，我不会执行这个操作。\n\n如有其他需要，请随时告诉我。"
        else:
            return f"✅ Okay, I won't proceed with this operation.\n\nLet me know if you need anything else."
    
    else:  # confirm
        # 用户确认操作 - 执行实际操作
        from .operations.executor import execute_confirmed_action
        
        # 执行操作
        success, result_message = await execute_confirmed_action(
            action_type=action_type,
            action_params=action_params,
            context=context,
            language=language
        )
        
        # 清除pending action
        session_manager.clear_pending_action(session_id)
        
        # 返回执行结果
        return result_message


async def handle_guided_inquiry(
    plan: Dict[str, Any],
    session_data: Dict[str, Any],
    context: Any,
    language: str,
    user_message: str
) -> str:
    """
    处理引导式探询意图（guided_inquiry）
    
    Args:
        plan: AI 理解规划结果
        session_data: 会话数据
        context: Bot context
        language: 语言代码
        user_message: 用户消息
        
    Returns:
        引导式回复
    """
    from ..utils.i18n import I18n
    from .knowledge_base import get_knowledge_base
    
    i18n = I18n(language)
    
    # 提取探询参数
    inquiry_params = plan.get('inquiry_params', {})
    topic = inquiry_params.get('topic', 'general')
    stage = inquiry_params.get('stage', 'initial')
    
    # 获取知识库内容
    kb = get_knowledge_base()
    knowledge = kb.get_knowledge() if kb else ""
    
    # 根据主题提供引导
    if 'how_to_use' in topic or 'tutorial' in topic or '如何使用' in user_message or '怎么' in user_message:
        # 提供系统使用指南
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_traditional:
                return f"""📚 **ArchiveBot 使用指南**

**核心功能：**
1️⃣ **轉發收藏** - 將消息轉發給 bot 自動歸檔
2️⃣ **智能搜索** - 使用關鍵詞或 AI 對話快速查找
3️⃣ **標籤管理** - 用 #標籤 組織內容
4️⃣ **筆記生成** - AI 自動為歸檔生成摘要筆記

**快速開始：**
• 轉發任何消息給我即可收藏
• 使用 /search 關鍵詞搜索內容
• 使用 /ai 進入智能對話模式
• 使用 /stats 查看統計數據

**進階功能：**
• /note - 生成歸檔筆記
• /export - 導出數據
• /backup - 備份數據庫
• /tags - 管理標籤

💡 **提示：** 您可以直接用自然語言問我任何問題，例如：「最近收藏了什麼？」「幫我找關於 Python 的歸檔」

{knowledge}

需要更詳細的某個功能說明嗎？"""
            else:
                return f"""📚 **ArchiveBot 使用指南**

**核心功能：**
1️⃣ **转发收藏** - 将消息转发给 bot 自动归档
2️⃣ **智能搜索** - 使用关键词或 AI 对话快速查找
3️⃣ **标签管理** - 用 #标签 组织内容
4️⃣ **笔记生成** - AI 自动为归档生成摘要笔记

**快速开始：**
• 转发任何消息给我即可收藏
• 使用 /search 关键词搜索内容
• 使用 /ai 进入智能对话模式
• 使用 /stats 查看统计数据

**进阶功能：**
• /note - 生成归档笔记
• /export - 导出数据
• /backup - 备份数据库
• /tags - 管理标签

💡 **提示：** 您可以直接用自然语言问我任何问题，例如：「最近收藏了什么？」「帮我找关于 Python 的归档」

{knowledge}

需要更详细的某个功能说明吗？"""
        else:
            return f"""📚 **ArchiveBot User Guide**

**Core Features:**
1️⃣ **Forward to Save** - Forward any message to bot for archiving
2️⃣ **Smart Search** - Find content using keywords or AI chat
3️⃣ **Tag Management** - Organize with #tags
4️⃣ **Note Generation** - AI generates summary notes for archives

**Quick Start:**
• Forward any message to me to save
• Use /search keyword to find content
• Use /ai to enter smart chat mode
• Use /stats to view statistics

**Advanced Features:**
• /note - Generate archive notes
• /export - Export data
• /backup - Backup database
• /tags - Manage tags

💡 **Tip:** You can ask me anything in natural language, e.g., "What did I save recently?" "Find archives about Python"

{knowledge}

Need more details about any specific feature?"""
    
    elif 'command' in topic or 'feature' in topic or '功能' in user_message:
        # 提供命令列表
        return handle_help(language)
    
    else:
        # 通用引导
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_traditional:
                return f"""📖 我可以幫您了解：

1. **如何使用系統** - 基本操作和快速開始
2. **功能介紹** - 詳細的功能說明
3. **命令列表** - 所有可用命令
4. **常見問題** - 使用技巧和解答

{knowledge}

您想了解哪方面呢？直接告訴我即可。"""
            else:
                return f"""📖 我可以帮您了解：

1. **如何使用系统** - 基本操作和快速开始
2. **功能介绍** - 详细的功能说明
3. **命令列表** - 所有可用命令
4. **常见问题** - 使用技巧和解答

{knowledge}

您想了解哪方面呢？直接告诉我即可。"""
        else:
            return f"""📖 I can help you learn about:

1. **How to use the system** - Basic operations and quick start
2. **Feature introduction** - Detailed feature explanations
3. **Command list** - All available commands
4. **FAQ** - Tips and troubleshooting

{knowledge}

What would you like to know? Just tell me directly."""


async def gather_data(need_data: Dict[str, Any], context: Any, user_intent: str = None) -> Dict[str, Any]:
    """
    根据AI规划收集需要的数据（使用缓存优化性能）
    
    Args:
        need_data: AI规划中需要的数据类型
        context: Bot context
        user_intent: 用户意图类型（pure_chat/general_query/specific_search/stats_analysis/resource_request）
        
    Returns:
        收集到的数据
    """
    data = {}
    
    # 纯聊天模式，直接返回空数据，不做任何查询
    if user_intent == 'pure_chat':
        logger.info("🎯 Intent: pure_chat - Skip all data queries")
        return data
    
    try:
        search_engine = context.bot_data.get('search_engine')
        ai_cache = context.bot_data.get('ai_data_cache')
        db_storage = context.bot_data.get('db_storage')
        
        if not ai_cache:
            logger.warning("AI data cache not available")
            return data
        
        # 获取排除配置（统一处理）
        from ..utils.config import get_config
        config = get_config()
        excluded_channels = config.get('ai.exclude_from_context.channel_ids', [])
        excluded_tags = config.get('ai.exclude_from_context.tags', [])
        
        if excluded_channels or excluded_tags:
            logger.info(f"⚠️ Exclusion active: channels={excluded_channels}, tags={excluded_tags}")
        else:
            logger.debug("✅ No exclusion filters configured")
        
        logger.info(f"🎯 Intent: {user_intent or 'unknown'} - Gathering data...")
        
        # 搜索具体内容（不缓存，走FTS索引）
        if need_data.get('search_keywords'):
            if search_engine:
                keywords = need_data['search_keywords']
                results = search_engine.search(keywords, limit=10)
                if results and results.get('results'):
                    candidates = results['results']
                    original_count = len(candidates)
                    
                    # 应用排除逻辑
                    if excluded_channels:
                        candidates = [
                            a for a in candidates 
                            if not any(
                                a.get('storage_path', '').startswith(f"telegram:{ch_id}:") 
                                for ch_id in excluded_channels
                            )
                        ]
                        logger.debug(f"Filtered by channels: {original_count} → {len(candidates)}")
                    
                    if excluded_tags:
                        # 需要检查每个归档的标签
                        tag_manager = context.bot_data.get('tag_manager')
                        if tag_manager:
                            filtered = []
                            for archive in candidates:
                                archive_tags = tag_manager.get_archive_tags(archive.get('id'))
                                if not any(tag in excluded_tags for tag in archive_tags):
                                    filtered.append(archive)
                            candidates = filtered
                            logger.debug(f"Filtered by tags: {original_count} → {len(candidates)}")
                    
                    data['search_results'] = candidates
                    logger.info(f"✅ Search: Found {len(candidates)} results for '{keywords}' (filtered from {original_count})")
                else:
                    logger.info(f"❌ Search: No results for '{keywords}'")  
        
        # 统计数据（缓存5分钟）
        if need_data.get('need_statistics'):
            stats = ai_cache.get_statistics()
            data['statistics'] = stats
            logger.info(f"✓ Stats: {stats['total']} archives, {stats['tags']} tags, {stats.get('recent_week', 0)} recent")
        
        # 示例归档（缓存5分钟）
        if need_data.get('need_sample_archives'):
            samples = ai_cache.get_recent_samples(limit=10)
            data['sample_archives'] = samples
            logger.info(f"✓ Samples: {len(samples)} recent archives")
        
        # 标签分析（缓存5分钟）
        if need_data.get('need_tags_analysis'):
            tag_analysis = ai_cache.get_tag_analysis(limit=15)
            data['tag_analysis'] = tag_analysis
            logger.info(f"✓ Tags: Analyzed {len(tag_analysis)} popular tags")
        
        # 最近记录上下文（24小时内，关键词触发）
        if need_data.get('need_recent_context') and db_storage:
            from datetime import datetime, timedelta
            from ..models.database import ArchiveDB
            
            # 获取24小时内的归档
            cutoff_time = datetime.now() - timedelta(hours=24)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            # 查询最近24小时的归档（限制数量避免内存消耗）
            recent_archives = db_storage.db.get_archives(
                limit=20,  # 最多20条，避免内存消耗过大
                order_by='created_at DESC'
            )
            
            # 筛选24小时内的
            recent_archives = [
                a for a in recent_archives 
                if a.get('created_at', 0) >= cutoff_timestamp
            ]
            
            if recent_archives:
                # 添加标签信息
                tag_manager = context.bot_data.get('tag_manager')
                if tag_manager:
                    for archive in recent_archives:
                        if 'tags' not in archive:
                            archive['tags'] = tag_manager.get_archive_tags(archive.get('id'))
                
                data['recent_context'] = recent_archives
                logger.info(f"✓ Loaded {len(recent_archives)} recent archives (24h)")
            else:
                logger.info("✗ No recent archives in last 24 hours")
        
        # 笔记查询（用户查询笔记）
        notes_query = need_data.get('notes_query', {})
        if notes_query and notes_query.get('enabled'):
            note_manager = context.bot_data.get('note_manager')
            if note_manager:
                limit = notes_query.get('limit', 10)
                sort_order = notes_query.get('sort', 'recent')  # recent 或 oldest
                has_link = notes_query.get('has_link')  # True/False/None
                
                logger.info(f"⏳ Notes query: limit={limit}, sort={sort_order}, has_link={has_link}")
                
                try:
                    # 获取所有笔记（包含title和storage_path）
                    all_notes = note_manager.get_all_notes(limit=100)
                    
                    if all_notes:
                        # 为每个笔记添加has_link字段
                        for note in all_notes:
                            note['has_link'] = bool(note.get('storage_path'))
                        
                        # 筛选条件：是否有链接
                        if has_link is not None:
                            if has_link:
                                # 仅有链接的笔记
                                all_notes = [n for n in all_notes if n.get('has_link')]
                            else:
                                # 仅无链接的笔记
                                all_notes = [n for n in all_notes if not n.get('has_link')]
                        
                        # 排序
                        if sort_order == 'oldest':
                            # 按创建时间升序（最早的在前）
                            all_notes.sort(key=lambda x: x.get('created_at', 0))
                        else:
                            # 按创建时间降序（最近的在前）- 默认
                            all_notes.sort(key=lambda x: x.get('created_at', 0), reverse=True)
                        
                        # 限制数量
                        notes_list = all_notes[:limit]
                        
                        data['notes'] = notes_list
                        logger.info(f"✅ Notes query: Found {len(notes_list)} notes (filtered from {len(all_notes)} total)")
                    else:
                        logger.info("❌ Notes query: No notes found")
                        data['notes'] = []
                        
                except Exception as e:
                    logger.error(f"Notes query error: {e}", exc_info=True)
                    data['notes'] = []
            else:
                logger.warning("⚠️ Note manager not available")
                data['notes'] = []
        
        # 资源查询（用于直接返回文件）
        resource_query = need_data.get('resource_query', {})
        if resource_query and resource_query.get('enabled') and db_storage:
            query_type = resource_query.get('type', 'random')
            content_types = resource_query.get('content_types')
            keywords = resource_query.get('keywords')
            tags = resource_query.get('tags')
            favorite_only = resource_query.get('favorite_only', False)
            limit = resource_query.get('limit', 1)
            
            logger.info(f"⏳ Resource query: type={query_type}, content_types={content_types}, keywords={keywords}, tags={tags}, favorite={favorite_only}, limit={limit}")
            
            # 应用排除逻辑的辅助函数
            def apply_exclusions(archives_list):
                """应用排除逻辑到归档列表"""
                if not archives_list:
                    return []
                
                original = len(archives_list)
                filtered = archives_list
                
                # 排除指定频道
                if excluded_channels:
                    filtered = [
                        a for a in filtered 
                        if not any(
                            a.get('storage_path', '').startswith(f"telegram:{ch_id}:") 
                            for ch_id in excluded_channels
                        )
                    ]
                    if len(filtered) < original:
                        logger.debug(f"Excluded {original - len(filtered)} from channels")
                
                # 排除指定标签
                if excluded_tags:
                    tag_manager = context.bot_data.get('tag_manager')
                    if tag_manager:
                        final = []
                        for archive in filtered:
                            archive_tags = archive.get('tags') or tag_manager.get_archive_tags(archive.get('id'))
                            if not any(tag in excluded_tags for tag in archive_tags):
                                final.append(archive)
                        filtered = final
                        if len(filtered) < original:
                            logger.debug(f"Excluded {original - len(filtered)} by tags")
                
                return filtered
            
            resources = []
            
            if query_type == 'random':
                # 随机获取
                import random
                filters = {}
                if content_types:
                    filters['content_types'] = content_types
                if favorite_only:
                    filters['favorite_only'] = True
                
                logger.debug(f"Random query filters: {filters}")
                
                # 从数据库获取符合条件的归档
                all_matches = db_storage.db.get_archives(
                    content_type=content_types[0] if content_types and len(content_types) == 1 else None,
                    favorite_only=favorite_only,
                    limit=100  # 先取100条，然后随机
                )
                
                logger.info(f"➡️ Random query: Retrieved {len(all_matches)} candidates from DB")
                
                if all_matches:
                    # 如果有多个类型筛选，进一步过滤
                    if content_types and len(content_types) > 1:
                        all_matches = [a for a in all_matches if a.get('content_type') in content_types]
                    
                    # 应用排除逻辑
                    all_matches = apply_exclusions(all_matches)
                    
                    # 随机选取
                    random.shuffle(all_matches)
                    resources = all_matches[:limit]
                    logger.info(f"✅ Random: Selected {len(resources)} from {len(all_matches)} after filtering")
                    
            elif query_type == 'search' and keywords:
                # 搜索模式
                if search_engine:
                    logger.debug(f"Search mode: keywords='{keywords}'")
                    search_results = search_engine.search(keywords, limit=limit * 2)
                    candidates = search_results.get('results', [])
                    logger.info(f"➡️ Search: FTS returned {len(candidates)} results")
                    
                    # 应用筛选
                    original_count = len(candidates)
                    if content_types:
                        candidates = [a for a in candidates if a.get('content_type') in content_types]
                        logger.debug(f"Filtered by content_types: {original_count} → {len(candidates)}")
                    if favorite_only and db_storage:
                        candidates = [a for a in candidates if db_storage.db.is_favorite(a.get('id'))]
                        logger.debug(f"Filtered by favorite: {original_count} → {len(candidates)}")
                    
                    # 应用排除逻辑
                    candidates = apply_exclusions(candidates)
                    
                    resources = candidates[:limit]
                    logger.info(f"✅ Search: Final {len(resources)} results after filtering")
                    
                    # 添加tags字段（如果没有）
                    tag_manager = context.bot_data.get('tag_manager')
                    if tag_manager:
                        for resource in resources:
                            if 'tags' not in resource:
                                resource['tags'] = tag_manager.get_archive_tags(resource.get('id'))
                    
            elif query_type == 'filter':
                # 筛选模式
                logger.debug(f"Filter mode: tags={tags}, content_types={content_types}, favorite={favorite_only}")
                filters = {}
                if favorite_only:
                    filters['favorite_only'] = True
                if tags:
                    # 标签筛选
                    tag_manager = context.bot_data.get('tag_manager')
                    if tag_manager:
                        # 去掉#前缀
                        clean_tags = [t.lstrip('#') for t in tags]
                        logger.debug(f"Searching by tags: {clean_tags}")
                        # 获取有这些标签的归档
                        tag_archives = set()
                        for tag in clean_tags:
                            archives = tag_manager.get_archives_by_tag(tag, limit=50)
                            tag_archives.update([a['id'] for a in archives])
                        
                        logger.info(f"➡️ Filter: Found {len(tag_archives)} archives with specified tags")
                        # 获取详细信息
                        resources = [db_storage.get_archive(aid) for aid in tag_archives]
                        resources = [r for r in resources if r]  # 过滤None
                else:
                    # 没有标签筛选，获取最近的
                    resources = db_storage.db.get_archives(
                        content_type=content_types[0] if content_types and len(content_types) == 1 else None,
                        favorite_only=favorite_only,
                        limit=limit * 2
                    )
                    logger.info(f"➡️ Filter: Retrieved {len(resources)} recent archives")
                
                # 应用排除逻辑
                resources = apply_exclusions(resources)
                
                # 应用类型筛选
                if content_types and len(content_types) > 1:
                    original_count = len(resources)
                    resources = [a for a in resources if a.get('content_type') in content_types]
                    logger.debug(f"Filtered by content_types: {original_count} → {len(resources)}")
                
                resources = resources[:limit]
                logger.info(f"✅ Filter: Final {len(resources)} results")
            
            # 确保资源有storage_path（只有telegram存储的才能发送）
            original_count = len(resources)
            resources = [r for r in resources if r.get('storage_type') == 'telegram' and r.get('storage_path')]
            if original_count > len(resources):
                logger.warning(f"⚠️ Filtered out {original_count - len(resources)} non-telegram resources")
            
            # 添加tags字段（如果没有）
            if resources:
                tag_manager = context.bot_data.get('tag_manager')
                if tag_manager:
                    for resource in resources:
                        if 'tags' not in resource:
                            resource['tags'] = tag_manager.get_archive_tags(resource.get('id'))
                        if not resource.get('tags'):
                            resource['tags'] = []
            
            if resources:
                data['resources'] = resources
                logger.info(f"✅ Resource query: {len(resources)} resources ready to send")
            else:
                logger.warning(f"❌ Resource query: No resources found (type={query_type}, filters applied)")
        
    except Exception as e:
        logger.error(f"Data gathering error: {e}", exc_info=True)
    
    return data


async def generate_response(
    user_message: str,
    plan: Dict[str, Any],
    data_context: Dict[str, Any],
    session_data: Dict[str, Any],
    context: Any,
    language: str
) -> str:
    """
    基于理解和数据生成最终回复
    
    Args:
        user_message: 用户原始消息
        plan: AI的理解和规划
        data_context: 收集到的数据
        session_data: 会话数据
        context: Bot context
        language: 用户语言
        
    Returns:
        最终回复（文本或JSON结构）
    """
    try:
        response_strategy = plan.get('response_strategy', '')
        
        # 检测是否为资源回复策略
        if 'resource_reply' in response_strategy.lower():
            resources = data_context.get('resources', [])
            
            if resources:
                # 返回JSON结构，由handlers处理
                import json
                return json.dumps({
                    'type': 'resources',
                    'strategy': 'single' if len(resources) == 1 else 'list',
                    'count': len(resources),
                    'items': resources
                }, ensure_ascii=False)
            else:
                # 没有找到资源，返回提示
                if language == 'en':
                    return "🔍 No matching resources found in your archives."
                elif language == 'zh-TW':
                    return "🔍 沒有在您的歸檔中找到符合條件的資源。"
                else:
                    return "🔍 没有在您的归档中找到符合条件的资源。"
        
        # 非resource_reply策略，正常生成文本回复
        from ..utils.config import get_config
        from .knowledge_base import get_knowledge_base
        from ..utils.message_builder import MessageBuilder
        
        config = get_config()
        # 使用 config.get() 方法以支持环境变量（AI_API_KEY）
        api_key = config.get('ai.api.api_key') or config.ai.get('api', {}).get('api_key')
        api_url = config.get('ai.api.api_url') or config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        fast_model = config.get('ai.api.model') or 'grok-4-1-fast-non-reasoning'
        
        # 判断是否需要引入知识库
        kb = get_knowledge_base()
        knowledge_content = None
        if kb.is_system_related_query(user_message):
            knowledge_content = kb.get_knowledge()
            logger.info("System-related query detected, knowledge base included")
        
        # 获取用户意图
        user_intent = plan.get('user_intent', 'general_query')
        
        # 使用统一的格式化工具构建数据摘要
        # 添加search_query到data_context（如果有搜索结果）
        if data_context.get('search_results') and plan.get('need_data', {}).get('search_keywords'):
            data_context['search_query'] = plan['need_data']['search_keywords']
        
        data_summary = MessageBuilder.format_ai_context_summary(data_context, user_intent, language)
        
        logger.info(f"🎯 Response generation: intent={user_intent}, data_summary_length={len(data_summary)}")
        
        # 获取对话历史
        conversation_history = session_data.get('context', {}).get('history', [])
        
        # 使用提示词模板生成消息（传递知识库）
        messages = ChatPrompts.get_response_prompt(
            user_message, plan, data_summary, language, conversation_history, knowledge_base=knowledge_content
        )
        
        logger.info(f"📤 Generating with {len(messages)} messages")
        
        # 从配置读取temperature
        from ..utils.config import get_config
        config = get_config()
        temperature = config.get('ai.api.temperature', 0.7)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": fast_model,
                    "messages": messages,
                    "max_tokens": 220,
                    "temperature": temperature  # 使用配置的温度
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content'].strip()
                
                # 更新历史（使用配置的长度限制）
                if 'context' not in session_data:
                    session_data['context'] = {}
                if 'history' not in session_data['context']:
                    session_data['context']['history'] = []
                
                user_prefix = "User: " if language == 'en' else ("用戶: " if language == 'zh-TW' else "用户: ")
                session_data['context']['history'].append(f"{user_prefix}{user_message}")
                session_data['context']['history'].append(f"AI: {reply}")
                
                # 获取配置的历史长度（默认10对，即20条消息）
                from ..utils.config import get_config
                config = get_config()
                max_history_pairs = config.get('ai.chat_history_length', 10)
                max_history_messages = max_history_pairs * 2  # 每对包含用户+AI两条消息
                
                # 保留最近的N对对话
                if len(session_data['context']['history']) > max_history_messages:
                    session_data['context']['history'] = session_data['context']['history'][-max_history_messages:]
                
                # 同时保存到 ai_session 的对话历史（用于上下文引用）
                session_id = session_data.get('session_id')
                if session_id:
                    from ..core.ai_session import get_session_manager
                    session_manager = get_session_manager()
                    
                    # 提取结果数据用于上下文引用
                    result_data = None
                    user_intent = plan.get('user_intent')
                    if user_intent == 'specific_search':
                        search_results = data_context.get('search_results', [])
                        result_data = {
                            'type': 'search',
                            'count': len(search_results),
                            'items': [{'id': r.get('id'), 'title': r.get('title')} for r in search_results[:3]]
                        }
                    elif user_intent == 'resource_request':
                        resources = data_context.get('resources', [])
                        result_data = {
                            'type': 'resource',
                            'count': len(resources),
                            'items': resources[:3]
                        }
                    
                    session_manager.add_conversation_turn(
                        session_id=session_id,
                        user_message=user_message,
                        bot_response=reply,
                        intent=user_intent,
                        result_data=result_data,
                        max_history=5
                    )
                
                logger.info(f"✓ Response generated: {reply[:50]}... (history: {len(session_data['context']['history'])} messages)")
                return reply
            else:
                logger.error(f"Response generation error: {response.status_code}")
                error_msg = "Sorry, temporarily unable to reply, please try again later"
                if language == 'zh-TW':
                    error_msg = "抱歉，暫時無法回覆，請稍後再試"
                elif language == 'zh-CN':
                    error_msg = "抱歉，暂时无法回复，请稍后再试"
                return error_msg
                
    except Exception as e:
        logger.error(f"Response generation error: {e}", exc_info=True)
        error_msg = "An error occurred during processing, please try again later"
        if language == 'zh-TW':
            error_msg = "處理時出錯了，請稍後再試"
        elif language == 'zh-CN':
            error_msg = "处理时出错了，请稍后再试"
        return error_msg


# ============================================================================
# AI Chat Mode Helper Functions (重构版)
# 提供消息路由判断和统一处理流程，复用现有工具函数
# ============================================================================

def should_trigger_ai_chat(message, context, config) -> tuple[bool, str]:
    """
    判断是否应触发AI对话模式
    复用helpers.py的工具函数
    
    Args:
        message: Telegram消息对象
        context: Bot context
        config: 配置对象
        
    Returns:
        (should_trigger, reason): 是否触发, 原因说明
    """
    from ..utils.helpers import is_url
    
    # AI功能未启用
    ai_config = config.ai
    chat_enabled = bool(ai_config.get('chat_enabled', False))
    if not chat_enabled:
        return False, 'chat_disabled'
    
    # 只处理文本消息且非转发
    if not message.text or message.forward_origin:
        return False, 'not_text_or_forwarded'
    
    # 如果消息属于媒体组（批量消息），不触发AI Chat
    if message.media_group_id:
        return False, 'belongs_to_media_group'
    
    text = message.text.strip()
    
    # 检查是否有其他特殊模式正在进行
    has_other_mode = (
        context.user_data.get('waiting_note_for_archive') or
        context.user_data.get('note_modify_mode') or
        context.user_data.get('note_append_mode') or
        (context.user_data.get('refine_note_context') and 
         context.user_data['refine_note_context'].get('waiting_for_instruction'))
    )
    
    if has_other_mode:
        return False, 'other_mode_active'
    
    # URL检测 - 不触发AI，让其归档
    if is_url(text):
        return False, 'url_detected'
    
    # 获取文本阈值
    text_thresholds = ai_config.get('text_thresholds', {})
    short_text_threshold = int(text_thresholds.get('short_text', 50))
    
    # 自动触发条件：短文本且无媒体
    if (len(text) < short_text_threshold and 
        not message.media_group_id and
        not message.photo and 
        not message.document and 
        not message.video and
        not message.audio):
        return True, 'short_text_auto_trigger'
    
    return False, 'does_not_match_criteria'


def detect_message_intent(text: str, language: str, config, has_active_session: bool) -> Dict[str, Any]:
    """
    检测消息意图（短文本/长文本/连贯性）
    复用helpers.should_create_note
    
    Args:
        text: 消息文本
        language: 用户语言
        config: 配置对象
        has_active_session: 是否有活跃会话
        
    Returns:
        intent字典: {type, threshold, ...}
    """
    from ..utils.helpers import should_create_note
    
    text_thresholds = config.ai.get('text_thresholds', {})
    
    # 如果在AI会话中，检测长文本意图
    if has_active_session:
        # 根据语言选择阈值
        if language in ['zh-CN', 'zh-TW', 'zh-HK', 'zh-MO']:
            threshold = int(text_thresholds.get('note_chinese', 150))
        else:
            threshold = int(text_thresholds.get('note_english', 250))
        
        if len(text) >= threshold:
            return {
                'type': 'long_text_in_session',
                'threshold': threshold,
                'length': len(text),
                'should_prompt': True
            }
    
    # 检查短文本
    is_short, note_type = should_create_note(text)
    
    if is_short:
        short_threshold = int(text_thresholds.get('short_text', 50))
        return {
            'type': 'short_text',
            'note_type': note_type,
            'length': len(text),
            'threshold': short_threshold,
            'should_prompt': len(text) < short_threshold
        }
    
    return {
        'type': 'normal',
        'length': len(text)
    }


async def process_ai_chat(
    message, 
    session_data: Dict[str, Any], 
    context, 
    lang_ctx,
    progress_callback=None
) -> tuple[bool, Optional[str]]:
    """
    统一的AI消息处理流程
    消除重复代码，提供可复用的AI调用
    
    Args:
        message: Telegram消息对象
        session_data: 会话数据
        context: Bot context
        lang_ctx: Language context
        progress_callback: 进度回调函数
        
    Returns:
        (success, response): 处理是否成功, AI响应内容或None
    """
    text = message.text.strip()
    
    try:
        # Stage 1: 理解需求
        if progress_callback:
            await progress_callback(lang_ctx.t('ai_chat_analyzing'))
        
        # 调用AI处理（使用'auto'让AI自动判断回复语言）
        ai_response = await handle_chat_message(
            text, 
            session_data, 
            context, 
            'auto', 
            progress_callback
        )
        
        logger.info(f"AI chat response generated for user")
        return True, ai_response
        
    except Exception as e:
        logger.error(f"AI chat processing error: {e}", exc_info=True)
        return False, None


def _log_audit_event(
    event_type: str,
    operation: str,
    params: dict,
    context: Any,
    language: str,
    result: str = None
) -> None:
    """
    Log AI operation audit trail (Phase 3)
    
    Args:
        event_type: Event type (forbidden_attempt, write_confirmed, write_cancelled, safe_executed)
        operation: Operation name
        params: Operation parameters
        context: Bot context
        language: Language code
        result: Operation result (success/failure message)
    """
    from datetime import datetime
    import json
    
    audit_log = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'operation': operation,
        'params': params,
        'language': language,
        'result': result
    }
    
    # Log to application logger with special prefix for audit trail
    logger.info(f"[AUDIT] {json.dumps(audit_log, ensure_ascii=False)}")
    
    # Optional: Store to database for persistent audit trail
    # TODO: Implement database audit table if needed
