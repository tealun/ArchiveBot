"""
Note generation operations
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


async def generate_note_from_content_operation(
    provider,
    content: str,
    content_type: str,
    max_length: int = 250,
    language: str = 'zh-CN'
) -> str:
    """
    根据内容生成笔记
    
    Args:
        provider: AI provider实例
        content: 原始内容
        content_type: 内容类型 (text/link/document)
        max_length: 笔记最大长度
        language: 语言
        
    Returns:
        生成的笔记内容
    """
    if not provider or not hasattr(provider, 'client'):
        return ""
    
    try:
        from ..providers.utils import is_formal_content
        is_formal = is_formal_content(content[:1000], content_type)
        
        # 构建prompt
        if language.startswith('zh'):
            if is_formal:
                prompt = f"请为这份{content_type}内容生成简明笔记（不超过{max_length}字）。\n\n"
                prompt += "要求：\n• 准确提炼核心内容和关键信息\n• 保持专业性和准确性\n"
                prompt += "• 便于检索和复习\n• 直接输出笔记内容，不要附加其他信息\n\n"
            else:
                prompt = f"帮我记一下这个{content_type}的要点（{max_length}字以内就好）。\n\n"
                prompt += "希望你能：\n• 说清楚核心内容和重要信息\n• 语言自然一些，别太正式\n"
                prompt += "• 方便以后快速回顾\n• 直接输出笔记，不需要其他说明\n\n"
            prompt += f"内容：\n{content[:3000]}"
        else:
            if is_formal:
                prompt = f"Please generate a concise note (within {max_length} words) for this {content_type} content.\n\n"
                prompt += "Requirements:\n• Accurately extract core content and key information\n"
                prompt += "• Maintain professionalism and accuracy\n• Suitable for retrieval and review\n"
                prompt += "• Output note content directly, no metadata\n\n"
            else:
                prompt = f"Help me jot down the key points of this {content_type} (around {max_length} words).\n\n"
                prompt += "Please:\n• Explain the core content and important info clearly\n"
                prompt += "• Keep it natural, not too formal\n• Make it easy to review later\n"
                prompt += "• Just the note, no extra explanations\n\n"
            prompt += f"Content:\n{content[:3000]}"
        
        # 调用 API
        r = await provider.client.post(
            provider.api_url,
            json={
                "model": provider.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": provider.temperature
            }
        )
        note_content = r.json()['choices'][0]['message']['content'].strip()
        
        logger.info(f"Generated note from content: {len(note_content)} chars")
        return note_content
        
    except Exception as e:
        logger.error(f"Generate note from content error: {e}", exc_info=True)
        return ""


async def generate_note_from_ai_analysis_operation(
    provider,
    ai_summary: str,
    ai_key_points: List[str],
    ai_category: str,
    title: str,
    language: str = 'zh-CN'
) -> str:
    """
    根据AI分析结果整理文档笔记
    """
    if not provider or not hasattr(provider, 'client'):
        return ""
    
    try:
        from ..providers.utils import is_formal_content
        is_formal = is_formal_content("", "", ai_category)
        
        key_points_text = '\n'.join([f"- {point}" for point in ai_key_points]) if ai_key_points else "无"
        
        if language.startswith('zh'):
            if is_formal:
                prompt = f"请根据以下AI分析整理一份完整的文档笔记。\n\n"
                prompt += f"文档：{title}\n分类：{ai_category}\n\n"
                prompt += f"摘要：\n{ai_summary}\n\n关键点：\n{key_points_text}\n\n"
                prompt += "要求：\n• 准确整合摘要和关键点信息\n• 保持专业性和逻辑性\n"
                prompt += "• 结构清晰便于理解\n• 直接输出笔记内容\n"
            else:
                prompt = f"帮我把这些AI分析的内容整理成一份笔记。\n\n"
                prompt += f"标题是《{title}》\n类型是{ai_category}\n\n"
                prompt += f"AI的总结：\n{ai_summary}\n\n主要要点：\n{key_points_text}\n\n"
                prompt += "希望你能：\n• 把摘要和要点融合在一起\n• 组织得清楚易懂\n"
                prompt += "• 语言自然流畅\n• 直接给我笔记内容就好\n"
        else:
            if is_formal:
                prompt = "Please organize a complete document note based on the following AI analysis.\n\n"
                prompt += f"Document: {title}\nCategory: {ai_category}\n\n"
                prompt += f"Summary:\n{ai_summary}\n\nKey Points:\n{key_points_text}\n\n"
                prompt += "Requirements:\n• Accurately integrate summary and key points\n"
                prompt += "• Maintain professionalism and logical flow\n• Clear structure, easy to understand\n"
                prompt += "• Output note content directly\n"
            else:
                prompt = "Help me organize these AI analysis results into a note.\n\n"
                prompt += f"Title: {title}\nType: {ai_category}\n\n"
                prompt += f"AI Summary:\n{ai_summary}\n\nMain Points:\n{key_points_text}\n\n"
                prompt += "Please:\n• Combine the summary and points naturally\n"
                prompt += "• Keep it clear and easy to understand\n• Use natural, flowing language\n"
                prompt += "• Just give me the note content\n"
        
        # 调用 API
        r = await provider.client.post(
            provider.api_url,
            json={
                "model": provider.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": provider.temperature
            }
        )
        note_content = r.json()['choices'][0]['message']['content'].strip()
        
        logger.info(f"Generated note from AI analysis: {len(note_content)} chars")
        return note_content
        
    except Exception as e:
        logger.error(f"Generate note from AI analysis error: {e}", exc_info=True)
        return ""
