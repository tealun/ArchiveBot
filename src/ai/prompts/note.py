"""
笔记生成 Prompt 模板
负责生成各种笔记相关功能的 prompts
"""


class NotePrompts:
    """笔记生成相关的 prompt 模板"""
    
    @staticmethod
    def get_direct_prompt(
        content: str,
        content_type: str,
        max_length: int,
        is_formal: bool,
        language: str
    ) -> str:
        """
        获取直接从内容生成笔记的 prompt
        
        Args:
            content: 原始内容
            content_type: 内容类型
            max_length: 最大长度
            is_formal: 是否正式风格
            language: 语言代码
            
        Returns:
            完整的 prompt 字符串
        """
        if language.startswith('zh'):
            if is_formal:
                # 正式风格
                prompt = f"请为这份{content_type}内容生成简明笔记（不超过{max_length}字）。\n\n"
                prompt += "要求：\n"
                prompt += "• 准确提炼核心内容和关键信息\n"
                prompt += "• 保持专业性和准确性\n"
                prompt += "• 便于检索和复习\n"
                prompt += "• 直接输出笔记内容，不要附加其他信息\n\n"
            else:
                # 轻松风格
                prompt = f"帮我记一下这个{content_type}的要点（{max_length}字以内就好）。\n\n"
                prompt += "希望你能：\n"
                prompt += "• 说清楚核心内容和重要信息\n"
                prompt += "• 语言自然一些，别太正式\n"
                prompt += "• 方便以后快速回顾\n"
                prompt += "• 直接输出笔记，不需要其他说明\n\n"
            prompt += f"内容：\n{content[:3000]}"
        else:
            if is_formal:
                # Formal style
                prompt = f"Please generate a concise note (within {max_length} words) for this {content_type} content.\n\n"
                prompt += "Requirements:\n"
                prompt += "• Accurately extract core content and key information\n"
                prompt += "• Maintain professionalism and accuracy\n"
                prompt += "• Suitable for retrieval and review\n"
                prompt += "• Output note content directly, no metadata\n\n"
            else:
                # Casual style
                prompt = f"Help me jot down the key points of this {content_type} (around {max_length} words).\n\n"
                prompt += "Please:\n"
                prompt += "• Explain the core content and important info clearly\n"
                prompt += "• Keep it natural, not too formal\n"
                prompt += "• Make it easy to review later\n"
                prompt += "• Just the note, no extra explanations\n\n"
            prompt += f"Content:\n{content[:3000]}"
        
        return prompt
    
    @staticmethod
    def get_from_analysis_prompt(
        title: str,
        ai_category: str,
        ai_summary: str,
        key_points_text: str,
        is_formal: bool,
        language: str
    ) -> str:
        """
        获取从AI分析结果整理笔记的 prompt
        
        Args:
            title: 文档标题
            ai_category: AI分类
            ai_summary: AI摘要
            key_points_text: 关键点文本
            is_formal: 是否正式风格
            language: 语言代码
            
        Returns:
            完整的 prompt 字符串
        """
        if language.startswith('zh'):
            if is_formal:
                # 正式风格
                prompt = f"请根据以下AI分析整理一份完整的文档笔记。\n\n"
                prompt += f"文档：{title}\n"
                prompt += f"分类：{ai_category}\n\n"
                prompt += f"摘要：\n{ai_summary}\n\n"
                prompt += f"关键点：\n{key_points_text}\n\n"
                prompt += "要求：\n"
                prompt += "• 准确整合摘要和关键点信息\n"
                prompt += "• 保持专业性和逻辑性\n"
                prompt += "• 结构清晰便于理解\n"
                prompt += "• 直接输出笔记内容\n"
            else:
                # 轻松风格
                prompt = f"帮我把这些AI分析的内容整理成一份笔记。\n\n"
                prompt += f"标题是《{title}》\n"
                prompt += f"类型是{ai_category}\n\n"
                prompt += f"AI的总结：\n{ai_summary}\n\n"
                prompt += f"主要要点：\n{key_points_text}\n\n"
                prompt += "希望你能：\n"
                prompt += "• 把摘要和要点融合在一起\n"
                prompt += "• 组织得清楚易懂\n"
                prompt += "• 语言自然流畅\n"
                prompt += "• 直接给我笔记内容就好\n"
        else:
            if is_formal:
                # Formal style
                prompt = "Please organize a complete document note based on the following AI analysis.\n\n"
                prompt += f"Document: {title}\n"
                prompt += f"Category: {ai_category}\n\n"
                prompt += f"Summary:\n{ai_summary}\n\n"
                prompt += f"Key Points:\n{key_points_text}\n\n"
                prompt += "Requirements:\n"
                prompt += "• Accurately integrate summary and key points\n"
                prompt += "• Maintain professionalism and logical flow\n"
                prompt += "• Clear structure, easy to understand\n"
                prompt += "• Output note content directly\n"
            else:
                # Casual style
                prompt = "Help me organize these AI analysis results into a note.\n\n"
                prompt += f"Title: {title}\n"
                prompt += f"Type: {ai_category}\n\n"
                prompt += f"AI Summary:\n{ai_summary}\n\n"
                prompt += f"Main Points:\n{key_points_text}\n\n"
                prompt += "Please:\n"
                prompt += "• Combine the summary and points naturally\n"
                prompt += "• Keep it clear and easy to understand\n"
                prompt += "• Use natural, flowing language\n"
                prompt += "• Just give me the note content\n"
        
        return prompt
