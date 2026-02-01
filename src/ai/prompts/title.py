"""
标题生成 Prompt 模板
负责生成标题相关功能的 prompts
"""


class TitlePrompts:
    """标题生成相关的 prompt 模板"""
    
    @staticmethod
    def get_prompt(
        content: str,
        max_length: int,
        is_formal: bool,
        language: str,
        detected_lang: str
    ) -> str:
        """
        获取标题生成的 prompt
        
        Args:
            content: 文本内容
            max_length: 最大长度
            is_formal: 是否正式风格
            language: 用户语言
            detected_lang: 检测到的内容语言
            
        Returns:
            完整的 prompt 字符串
        """
        if language.startswith('zh') or detected_lang == 'zh':
            if is_formal:
                prompt = f"请为这段文本拟一个标题（{max_length}字以内）。\n\n"
                prompt += "要求：\n"
                prompt += "• 准确概括核心内容\n"
                prompt += "• 简洁规范\n"
                prompt += "• 不加引号\n"
                prompt += "• 直接输出标题\n\n"
            else:
                prompt = f"帮我给这段内容想个标题（{max_length}字以内）。\n\n"
                prompt += "希望：\n"
                prompt += "• 能说清楚主要内容\n"
                prompt += "• 简单明了\n"
                prompt += "• 不要加引号\n"
                prompt += "• 直接给我标题就好\n\n"
            prompt += f"内容：\n{content[:1000]}"
        else:
            if is_formal:
                prompt = f"Please create a title for this text (within {max_length} characters).\n\n"
                prompt += "Requirements:\n"
                prompt += "• Accurately summarize core content\n"
                prompt += "• Concise and formal\n"
                prompt += "• No quotation marks\n"
                prompt += "• Output title directly\n\n"
            else:
                prompt = f"Help me come up with a title for this content (around {max_length} characters).\n\n"
                prompt += "Please:\n"
                prompt += "• Capture the main content\n"
                prompt += "• Keep it simple and clear\n"
                prompt += "• No quotes\n"
                prompt += "• Just give me the title\n\n"
            prompt += f"Content:\n{content[:1000]}"
        
        return prompt
