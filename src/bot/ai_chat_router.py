"""
AI Chat Router

Handles AI interactive chat mode with 3-stage processing:
1. Understand user intent and plan response
2. Gather required data
3. Generate final response
"""
import logging
import re
import json
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def understand_and_plan(user_message: str, context: Any) -> Dict[str, Any]:
    """
    让AI理解用户真实需求并规划如何回答
    
    核心思想：不预设意图类型，让AI自由理解用户想要什么
    
    Returns:
        {
            'user_goal': str,  # 用户真正想要什么
            'need_data': {  # 需要什么数据来回答
                'search_keywords': str or None,
                'need_statistics': bool,
                'need_sample_archives': bool,
                'need_tags_analysis': bool
            },
            'response_strategy': str,  # 如何组织回复
            'reasoning': str  # 思考过程
        }
    """
    try:
        from ..utils.config import get_config
        import httpx
        import json
        
        config = get_config()
        api_key = config.ai.get('api', {}).get('api_key')
        api_url = config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        reasoning_model = config.ai.get('api', {}).get('reasoning_model', 'grok-4-1-fast-reasoning')
        
        understanding_prompt = f"""你是智能助手规划器。用户有一个归档管理系统（44条归档，125个标签）。

用户说："{user_message}"

请理解用户需求并规划回答方式。返回JSON（无markdown）：

{{
    "user_goal": "用户的真实需求（一句话）",
    "question_type": "precise|open",  # precise=具体精准问题, open=开放式问题
    "need_data": {{
        "search_keywords": "如果需要搜索，提取关键词；否则null",
        "need_statistics": true/false,
        "need_sample_archives": true/false,
        "need_tags_analysis": true/false
    }},
    "response_strategy": "回复方式（30字内）：直接回答/数据分析/搜索结果/澄清引导",
    "reasoning": "分析理由（50字内）"
}}

规划要点：
1. 判断问题类型
   - 精准问题：有明确目标、具体范围、特定需求（如"有多少条归档"、"找关于python的内容"）→ 直接专注回答
   - 开放问题：探索性、无明确范围、启发性（如"我归档了什么"、"分析下我的兴趣"）→ 可适度发散
2. 精准问题只返回所需数据，不过度引申
3. 开放问题可以分析趋势、提供洞察
4. 专业友好，不过度热情

只返回JSON。"""
        
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
        progress_callback: Optional callback for progress updates
        
    Returns:
        AI response text
    """
    # 简单命令直接处理
    text_lower = user_message.lower().strip()
    if text_lower in ['退出', '结束', 'exit', 'quit', 'bye', '再见']:
        return handle_exit()
    if text_lower in ['帮助', 'help', '?', '？']:
        return handle_help()
    
    # Stage 1: AI理解需求并规划
    logger.info(f"🧠 Stage 1: Understanding user need...")
    if progress_callback:
        await progress_callback("🧠 分析需求...")
    plan = await understand_and_plan(user_message, context)
    
    user_goal = plan.get('user_goal', '')
    if '退出' in user_goal or 'exit' in user_goal.lower():
        return handle_exit()
    if '帮助' in user_goal or 'help' in user_goal.lower():
        return handle_help()
    
    # Stage 2: 根据规划获取数据
    logger.info(f"📊 Stage 2: Gathering data...")
    if progress_callback:
        from ..utils.i18n import get_i18n
        i18n = get_i18n()
        await progress_callback(i18n.t('ai_chat_gathering'))
    data_context = await gather_data(plan.get('need_data', {}), context)
    
    # Stage 3: AI生成最终回复
    logger.info(f"💬 Stage 3: Generating response...")
    if progress_callback:
        from ..utils.i18n import get_i18n
        i18n = get_i18n()
        await progress_callback(i18n.t('ai_chat_generating'))
    return await generate_response(user_message, plan, data_context, session_data, context)


def handle_exit() -> str:
    """Handle exit intent"""
    from ..utils.i18n import get_i18n
    i18n = get_i18n()
    return i18n.t('ai_chat_exit')


def handle_help() -> str:
    """Handle help intent"""
    from ..utils.i18n import get_i18n
    i18n = get_i18n()
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
    context: Any
) -> str:
    """
    基于理解和数据生成最终回复
    
    Args:
        user_message: 用户原始消息
        plan: AI的理解和规划
        data_context: 收集到的数据
        session_data: 会话数据
        context: Bot context
        
    Returns:
        最终回复
    """
    try:
        from ..utils.config import get_config
        import httpx
        
        config = get_config()
        api_key = config.ai.get('api', {}).get('api_key')
        api_url = config.ai.get('api', {}).get('api_url', 'https://api.x.ai/v1/chat/completions')
        fast_model = 'grok-4-1-fast-non-reasoning'
        
        # 构建上下文
        context_parts = []
        
        if data_context.get('statistics'):
            stats = data_context['statistics']
            context_parts.append(f"统计：共{stats['total']}条归档，{stats['tags']}个标签，最近7天{stats['recent_week']}条")
        
        if data_context.get('search_results'):
            results = data_context['search_results']
            context_parts.append(f"\n搜索结果（{len(results)}条）：")
            for i, item in enumerate(results[:3], 1):
                title = item.get('title', '无标题')[:40]
                context_parts.append(f"{i}. {title}")
        
        if data_context.get('tag_analysis'):
            tags = data_context['tag_analysis'][:10]
            top_tags = ', '.join([f"#{t['tag']}({t['count']})" for t in tags[:5]])
            context_parts.append(f"\n热门标签：{top_tags}")
        
        if data_context.get('sample_archives'):
            samples = data_context['sample_archives'][:5]
            context_parts.append(f"\n最近归档：")
            for s in samples:
                context_parts.append(f"• {s['title']}")
        
        data_summary = '\n'.join(context_parts) if context_parts else "暂无相关数据"
        
        # 获取对话历史
        conversation_history = session_data.get('context', {}).get('history', [])
        
        # 根据问题类型调整系统提示
        question_type = plan.get('question_type', 'open')
        if question_type == 'precise':
            # 精准问题：专注、简洁、直接
            style_guide = """风格要求（精准问题模式）：
- 直接回答用户的具体问题，不发散
- 只提供所需数据，不额外延伸
- 简洁明了，控制在50-80字
- 如果数据充分，直接给结论；如果不足，明确说明
- 适度使用emoji（1个）"""
        else:
            # 开放问题：可以分析、洞察、适度发散
            style_guide = """风格要求（开放探索模式）：
- 可以从数据中发现趋势和规律
- 适度发散，提供洞察和建议
- 字数60-100字，分3-4个小段
- 善于总结和归纳
- 适度使用emoji（1-2个）"""
        
        messages = [
            {
                "role": "system",
                "content": f"""你是归档助手，帮用户管理和分析归档内容。

用户需求：{plan.get('user_goal', '未知')}
问题类型：{question_type}
回复策略：{plan.get('response_strategy', '友好回复')}

{style_guide}

通用要求：
- 专业但不刻板，友好但有分寸
- 不用"嘿"、"哥们儿"等过分随意的称呼

回复格式（重要）：
1. 分段表达，不要大段文字堆砌
2. 关键数据用列表：
   • 统计数据
   • 标签TOP3
   • 主要发现
3. 用空行分隔不同部分
4. 总字数60-100字，但要分3-4个小段
5. 不用markdown标题（###）和加粗（**）

示例格式：
📊 共44条归档，125个标签

热门标签：
• #技术 (12条)
• #学习 (8条) 
• #工具 (6条)

最近一周很活跃，归档了不少技术相关内容。要不要看看具体都是什么？"""
            }
        ]
        
        # 添加历史（最近3轮）
        for msg in conversation_history[-6:]:
            if msg.startswith("用户: "):
                messages.append({"role": "user", "content": msg[4:]})
            elif msg.startswith("AI: "):
                messages.append({"role": "assistant", "content": msg[4:]})
        
        # 当前问题+数据
        current_content = f"{user_message}\n\n【数据】\n{data_summary}"
        messages.append({"role": "user", "content": current_content})
        
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
                
                session_data['context']['history'].append(f"用户: {user_message}")
                session_data['context']['history'].append(f"AI: {reply}")
                
                if len(session_data['context']['history']) > 6:
                    session_data['context']['history'] = session_data['context']['history'][-6:]
                
                logger.info(f"✓ Response generated: {reply[:50]}...")
                return reply
            else:
                logger.error(f"Response generation error: {response.status_code}")
                return "抱歉，暂时无法回复，请稍后再试"
                
    except Exception as e:
        logger.error(f"Response generation error: {e}", exc_info=True)
        return "处理时出错了，请稍后再试"
