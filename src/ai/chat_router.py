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
    
    # Stage 2: 根据规划和意图获取数据
    logger.info(f"📊 Stage 2: Gathering data (intent: {user_intent})...")
    if progress_callback and user_intent != 'pure_chat':
        await progress_callback(i18n.t('ai_chat_gathering'))
    data_context = await gather_data(plan.get('need_data', {}), context, user_intent)
    
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
        
        # 构建上下文
        context_parts = []
        
        # 获取用户意图，判断是否需要显示统计数据
        user_intent = plan.get('user_intent', 'general_query')
        # 只在这些意图下显示统计数据
        show_stats = user_intent in ['specific_search', 'stats_analysis', 'resource_request']
        
        logger.info(f"🎯 Response generation: intent={user_intent}, show_stats={show_stats}, has_stats={bool(data_context.get('statistics'))}")
        
        if data_context.get('statistics') and show_stats:
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
        
        # 最近24小时记录上下文（限制数量避免token消耗）
        if data_context.get('recent_context'):
            recent = data_context['recent_context'][:5]  # 最多5条，避免prompt过大
            header = "Archives in last 24 hours" if language == 'en' else ("過去24小時歸檔" if language == 'zh-TW' else "过去24小时归档")
            context_parts.append(f"\n{header}（{len(recent)}）：")
            for r in recent:
                title = r.get('title', '')[:40]  # 缩短标题长度
                tags = ', '.join([f"#{t}" for t in r.get('tags', [])[:2]])  # 最多2个标签
                context_parts.append(f"• {title} {tags}")
        
        no_data_text = "No relevant data" if language == 'en' else ("暫無相關數據" if language == 'zh-TW' else "暂无相关数据")
        data_summary = '\n'.join(context_parts) if context_parts else no_data_text
        
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
