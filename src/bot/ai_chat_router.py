"""
AI Chat Router

Handles AI interactive chat mode with lightweight intent recognition.
Routes user messages to appropriate handlers (search, refine, general chat).
"""
import logging
import re
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """Lightweight rule-based intent recognition"""
    
    # 搜索关键词
    SEARCH_KEYWORDS = [
        r'\b(搜索|查找|找|search|find|look\s*for)\b',
        r'^(找|查|search|find)',
        r'(哪里|什么时候|when|where|which)',
        r'(有没有|有关|关于|about)',
    ]
    
    # 退出关键词
    EXIT_KEYWORDS = [
        r'^(退出|结束|quit|exit|bye|再见)$',
    ]
    
    # 帮助关键词
    HELP_KEYWORDS = [
        r'^(帮助|help|\?|？)$',
    ]
    
    @staticmethod
    def recognize(text: str) -> Tuple[str, float]:
        """
        Recognize intent from user message
        
        Args:
            text: User message text
            
        Returns:
            (intent, confidence) where intent in ['search', 'exit', 'help', 'chat']
            confidence is 0.0-1.0
        """
        text_lower = text.lower().strip()
        
        # Exit intent (highest priority)
        for pattern in IntentRecognizer.EXIT_KEYWORDS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return 'exit', 1.0
        
        # Help intent
        for pattern in IntentRecognizer.HELP_KEYWORDS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return 'help', 1.0
        
        # Search intent
        for pattern in IntentRecognizer.SEARCH_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                return 'search', 0.8
        
        # Default to general chat
        return 'chat', 0.3


async def handle_chat_message(
    user_message: str,
    session_data: Dict[str, Any],
    context: Any
) -> str:
    """
    Handle message in AI chat mode
    
    Args:
        user_message: User's message text
        session_data: Current session context
        context: Bot context (has bot_data with managers)
        
    Returns:
        AI response text
    """
    intent, confidence = IntentRecognizer.recognize(user_message)
    
    logger.info(f"AI chat intent: {intent} (confidence={confidence:.2f})")
    
    # Route to appropriate handler
    if intent == 'exit':
        return handle_exit()
    elif intent == 'help':
        return handle_help()
    elif intent == 'search':
        return await handle_search(user_message, session_data, context)
    else:
        return await handle_general_chat(user_message, session_data, context)


def handle_exit() -> str:
    """Handle exit intent"""
    return "👋 已退出AI助手模式"


def handle_help() -> str:
    """Handle help intent"""
    return """🤖 AI助手功能：

• 搜索归档：直接描述你要找的内容
• 精炼笔记：在归档后的消息中点击"精炼笔记"按钮
• 退出：发送"退出"结束会话

提示：会话10分钟无活动自动结束"""


async def handle_search(
    user_message: str,
    session_data: Dict[str, Any],
    context: Any
) -> str:
    """
    Handle search intent - search archives and return results
    
    Args:
        user_message: User's search query
        session_data: Session context
        context: Bot context
        
    Returns:
        Search results formatted as text
    """
    try:
        search_engine = context.bot_data.get('search_engine')
        if not search_engine:
            return "❌ 搜索功能暂不可用"
        
        # Extract search query (remove search keywords)
        query = re.sub(r'^(搜索|查找|找|search|find)\s*', '', user_message, flags=re.IGNORECASE).strip()
        if not query:
            return "🔍 请告诉我你要搜索什么内容"
        
        # Perform search (limit to 5 results)
        results = search_engine.search(query, limit=5)
        
        if not results:
            return f"🔍 没有找到关于「{query}」的归档"
        
        # Format results
        response = f"🔍 找到 {len(results)} 条相关归档：\n\n"
        for i, item in enumerate(results, 1):
            title = item.get('title', '无标题')[:50]
            archive_id = item.get('id', 0)
            tags = item.get('tags', [])
            tag_str = ' '.join([f"#{t}" for t in tags[:3]]) if tags else ''
            
            response += f"{i}. {title}\n"
            response += f"   ID: {archive_id}"
            if tag_str:
                response += f" | {tag_str}"
            response += "\n\n"
        
        return response.strip()
        
    except Exception as e:
        logger.error(f"Search error in chat mode: {e}", exc_info=True)
        return "❌ 搜索时出错，请稍后再试"


async def handle_general_chat(
    user_message: str,
    session_data: Dict[str, Any],
    context: Any
) -> str:
    """
    Handle general chat - use AI to respond
    
    Args:
        user_message: User's message
        session_data: Session context
        context: Bot context
        
    Returns:
        AI-generated response
    """
    try:
        ai_summarizer = context.bot_data.get('ai_summarizer')
        if not ai_summarizer or not ai_summarizer.is_available():
            return "💬 很抱歉，AI服务暂不可用"
        
        # Build context-aware prompt
        conversation_history = session_data.get('context', {}).get('history', [])
        
        # Prepare prompt with conversation context
        if conversation_history:
            history_text = "\n".join([f"- {msg}" for msg in conversation_history[-3:]])  # last 3 messages
            prompt = f"""你是ArchiveBot的AI助手，帮助用户管理归档。

最近对话：
{history_text}

用户：{user_message}

请简短回复（50字以内），友好自然。如果用户想归档内容，提示他直接发送或转发消息即可。"""
        else:
            prompt = f"""你是ArchiveBot的AI助手，帮助用户管理归档。

用户：{user_message}

请简短回复（50字以内），友好自然。如果用户想归档内容，提示他直接发送或转发消息即可。"""
        
        # Call AI (use provider directly for simple chat)
        try:
            if hasattr(ai_summarizer, 'provider') and ai_summarizer.provider:
                response = await ai_summarizer.provider.client.post(
                    ai_summarizer.provider.api_url,
                    json={
                        "model": ai_summarizer.provider.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 150
                    },
                    timeout=10
                )
                reply = response.json()['choices'][0]['message']['content'].strip()
                
                # Update conversation history
                if 'history' not in session_data.get('context', {}):
                    if 'context' not in session_data:
                        session_data['context'] = {}
                    session_data['context']['history'] = []
                
                session_data['context']['history'].append(f"用户: {user_message}")
                session_data['context']['history'].append(f"AI: {reply}")
                
                # Keep only last 6 messages (3 rounds)
                if len(session_data['context']['history']) > 6:
                    session_data['context']['history'] = session_data['context']['history'][-6:]
                
                return reply
            else:
                return "💬 AI服务暂不可用"
                
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return "💬 很抱歉，暂时无法回复"
            
    except Exception as e:
        logger.error(f"General chat error: {e}", exc_info=True)
        return "💬 处理消息时出错"
