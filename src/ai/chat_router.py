"""
AI Chat Router

Handles AI interactive chat mode with 3-stage processing:
1. Understand user intent and plan response
2. Gather required data
3. Generate final response

Uses language context for multi-language support.
"""
import logging
import re
import json
import httpx
from typing import Optional, Dict, Any

from .prompts.chat import ChatPrompts

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
        from ..utils.config import get_config
        
        config = get_config()
        api_key = config.ai.get('api', {}).get('api_key')
        api_url = config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        reasoning_model = config.ai.get('api', {}).get('reasoning_model', 'grok-4-1-fast-reasoning')
        
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
                    "temperature": 0.4
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                ai_response = re.sub(r'^```json\s*|\s*```$', '', ai_response, flags=re.MULTILINE).strip()
                
                plan = json.loads(ai_response)
                logger.info(f"🧠 AI Understanding: {plan.get('user_goal')}")
                logger.info(f"📋 Response Strategy: {plan.get('response_strategy')}")
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
    if '退出' in user_goal or '結束' in user_goal or 'exit' in user_goal.lower():
        return handle_exit(language)
    if '帮助' in user_goal or '幫助' in user_goal or 'help' in user_goal.lower():
        return handle_help(language)
    
    # Stage 2: 根据规划获取数据
    logger.info(f"📊 Stage 2: Gathering data...")
    if progress_callback:
        await progress_callback(i18n.t('ai_chat_gathering'))
    data_context = await gather_data(plan.get('need_data', {}), context)
    
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


async def gather_data(need_data: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    根据AI规划收集需要的数据（使用缓存优化性能）
    
    Args:
        need_data: AI规划中需要的数据类型
        context: Bot context
        
    Returns:
        收集到的数据
    """
    data = {}
    
    try:
        search_engine = context.bot_data.get('search_engine')
        ai_cache = context.bot_data.get('ai_data_cache')
        
        if not ai_cache:
            logger.warning("AI data cache not available")
            return data
        
        # 搜索具体内容（不缓存，走FTS索引）
        if need_data.get('search_keywords'):
            if search_engine:
                keywords = need_data['search_keywords']
                results = search_engine.search(keywords, limit=5)
                if results and results.get('results'):
                    data['search_results'] = results['results']
                    logger.info(f"✓ Found {len(results['results'])} search results")
        
        # 统计数据（缓存5分钟）
        if need_data.get('need_statistics'):
            stats = ai_cache.get_statistics()
            data['statistics'] = stats
            logger.info(f"✓ Statistics: {stats['total']} archives, {stats['tags']} tags")
        
        # 示例归档（缓存5分钟）
        if need_data.get('need_sample_archives'):
            samples = ai_cache.get_recent_samples(limit=10)
            data['sample_archives'] = samples
            logger.info(f"✓ Sampled {len(samples)} archives")
        
        # 标签分析（缓存5分钟）
        if need_data.get('need_tags_analysis'):
            tag_analysis = ai_cache.get_tag_analysis(limit=15)
            data['tag_analysis'] = tag_analysis
            logger.info(f"✓ Analyzed {len(tag_analysis)} tags")
        
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
        最终回复
    """
    try:
        from ..utils.config import get_config
        
        config = get_config()
        api_key = config.ai.get('api', {}).get('api_key')
        api_url = config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        fast_model = 'grok-4-1-fast-non-reasoning'
        
        # 构建上下文
        context_parts = []
        
        if data_context.get('statistics'):
            stats = data_context['statistics']
            if language == 'en':
                context_parts.append(f"Statistics: {stats['total']} archives, {stats['tags']} tags, {stats['recent_week']} in last 7 days")
            elif language == 'zh-TW':
                context_parts.append(f"統計：共{stats['total']}條歸檔，{stats['tags']}個標籤，最近7天{stats['recent_week']}條")
            else:
                context_parts.append(f"统计：共{stats['total']}条归档，{stats['tags']}个标签，最近7天{stats['recent_week']}条")
        
        if data_context.get('search_results'):
            results = data_context['search_results']
            header = "Search results" if language == 'en' else ("搜尋結果" if language == 'zh-TW' else "搜索结果")
            context_parts.append(f"\n{header}（{len(results)}）：")
            for i, item in enumerate(results[:3], 1):
                title = item.get('title', 'No title' if language == 'en' else '無標題' if language == 'zh-TW' else '无标题')[:40]
                context_parts.append(f"{i}. {title}")
        
        if data_context.get('tag_analysis'):
            tags = data_context['tag_analysis'][:10]
            top_tags = ', '.join([f"#{t['tag']}({t['count']})" for t in tags[:5]])
            header = "Popular tags" if language == 'en' else ("熱門標籤" if language == 'zh-TW' else "热门标签")
            context_parts.append(f"\n{header}：{top_tags}")
        
        if data_context.get('sample_archives'):
            samples = data_context['sample_archives'][:5]
            header = "Recent archives" if language == 'en' else ("最近歸檔" if language == 'zh-TW' else "最近归档")
            context_parts.append(f"\n{header}：")
            for s in samples:
                context_parts.append(f"• {s['title']}")
        
        no_data_text = "No relevant data" if language == 'en' else ("暫無相關數據" if language == 'zh-TW' else "暂无相关数据")
        data_summary = '\n'.join(context_parts) if context_parts else no_data_text
        
        # 获取对话历史
        conversation_history = session_data.get('context', {}).get('history', [])
        
        # 使用提示词模板生成消息
        messages = ChatPrompts.get_response_prompt(
            user_message, plan, data_summary, language, conversation_history
        )
        
        logger.info(f"📤 Generating with {len(messages)} messages")
        
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
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content'].strip()
                
                # 更新历史
                if 'context' not in session_data:
                    session_data['context'] = {}
                if 'history' not in session_data['context']:
                    session_data['context']['history'] = []
                
                user_prefix = "User: " if language == 'en' else ("用戶: " if language == 'zh-TW' else "用户: ")
                session_data['context']['history'].append(f"{user_prefix}{user_message}")
                session_data['context']['history'].append(f"AI: {reply}")
                
                if len(session_data['context']['history']) > 6:
                    session_data['context']['history'] = session_data['context']['history'][-6:]
                
                logger.info(f"✓ Response generated: {reply[:50]}...")
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
