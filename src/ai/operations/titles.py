"""
Title generation operations
"""
import logging

logger = logging.getLogger(__name__)


async def generate_title_from_text_operation(
    provider,
    content: str,
    max_length: int = 32,
    language: str = 'zh-CN'
) -> str:
    """
    从文本内容生成标题
    """
    if not content or not content.strip():
        return "无标题"
    
    if not provider or not hasattr(provider, 'client'):
        fallback = content[:max_length].strip()
        if len(content) > max_length:
            fallback = fallback[:max_length-3] + "..."
        return fallback
    
    try:
        from ..providers.utils import detect_content_language, is_formal_content
        detected_lang = detect_content_language(content)
        is_formal = is_formal_content(content[:1000])
        
        if language.startswith('zh') or detected_lang == 'zh':
            if is_formal:
                prompt = f"请为这段文本拟一个标题（{max_length}字以内）。\n\n"
                prompt += "要求：\n• 准确概括核心内容\n• 简洁规范\n• 不加引号\n• 直接输出标题\n\n"
            else:
                prompt = f"帮我给这段内容想个标题（{max_length}字以内）。\n\n"
                prompt += "希望：\n• 能说清楚主要内容\n• 简单明了\n• 不要加引号\n• 直接给我标题就好\n\n"
            prompt += f"内容：\n{content[:1000]}"
        else:
            if is_formal:
                prompt = f"Please create a title for this text (within {max_length} characters).\n\n"
                prompt += "Requirements:\n• Accurately summarize core content\n• Concise and formal\n"
                prompt += "• No quotation marks\n• Output title directly\n\n"
            else:
                prompt = f"Help me come up with a title for this content (around {max_length} characters).\n\n"
                prompt += "Please:\n• Capture the main content\n• Keep it simple and clear\n"
                prompt += "• No quotes\n• Just give me the title\n\n"
            prompt += f"Content:\n{content[:1000]}"
        
        # 调用 API
        r = await provider.client.post(
            provider.api_url,
            json={
                "model": provider.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": provider.temperature
            }
        )
        title = r.json()['choices'][0]['message']['content'].strip()
        
        # 移除可能的引号
        for quote_char in ['"', "'", '"', '"', ''', ''']:
            title = title.strip(quote_char)
        
        # 确保标题不超过最大长度
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        logger.info(f"Generated title from text: {title}")
        return title
        
    except Exception as e:
        logger.error(f"Generate title from text error: {e}", exc_info=True)
        fallback = content[:max_length].strip()
        if len(content) > max_length:
            fallback = fallback[:max_length-3] + "..."
        return fallback
