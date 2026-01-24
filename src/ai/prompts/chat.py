"""
AI Chat Prompt Templates
Handles prompts for AI interactive chat mode
Supports Simplified Chinese, Traditional Chinese, and English
"""


class ChatPrompts:
    """AI Chat related prompt templates"""
    
    @staticmethod
    def get_understanding_prompt(user_message: str, language: str, stats: dict = None) -> str:
        """
        Get prompt for understanding user intent and planning response
        
        Args:
            user_message: User's message
            language: Language code (zh-CN, zh-TW, en)
            stats: Statistics about archive system (total, tags, etc.)
            
        Returns:
            Complete prompt string
        """
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            return ChatPrompts._get_understanding_prompt_zh(
                user_message, stats, is_traditional
            )
        else:
            return ChatPrompts._get_understanding_prompt_en(user_message, stats)
    
    @staticmethod
    def _get_understanding_prompt_zh(
        user_message: str,
        stats: dict = None,
        is_traditional: bool = False
    ) -> str:
        """Chinese understanding prompt"""
        total = stats.get('total', 44) if stats else 44
        tags = stats.get('tags', 125) if stats else 125
        
        if is_traditional:
            return f"""你是智慧助手規劃器。用戶有一個歸檔管理系統（{total}條歸檔，{tags}個標籤）。

用戶說："{user_message}"

請理解用戶需求並規劃回答方式。返回JSON（無markdown）：

{{
    "user_goal": "用戶的真實需求（一句話）",
    "question_type": "precise|open",  # precise=具體精準問題, open=開放式問題
    "need_data": {{
        "search_keywords": "如果需要搜尋，提取關鍵詞；否則null",
        "need_statistics": true/false,
        "need_sample_archives": true/false,
        "need_tags_analysis": true/false
    }},
    "response_strategy": "回覆方式（30字內）：直接回答/數據分析/搜尋結果/澄清引導",
    "reasoning": "分析理由（50字內）"
}}

規劃要點：
1. 判斷問題類型
   - 精準問題：有明確目標、具體範圍、特定需求（如「有多少條歸檔」、「找關於python的內容」）→ 直接專注回答
   - 開放問題：探索性、無明確範圍、啟發性（如「我歸檔了什麼」、「分析下我的興趣」）→ 可適度發散
2. 精準問題只返回所需數據，不過度引申
3. 開放問題可以分析趨勢、提供洞察
4. 專業友好，不過度熱情

只返回JSON。"""
        else:
            return f"""你是智能助手规划器。用户有一个归档管理系统（{total}条归档，{tags}个标签）。

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
   - 精准问题：有明确目标、具体范围、特定需求（如「有多少条归档」、「找关于python的内容」）→ 直接专注回答
   - 开放问题：探索性、无明确范围、启发性（如「我归档了什么」、「分析下我的兴趣」）→ 可适度发散
2. 精准问题只返回所需数据，不过度引申
3. 开放问题可以分析趋势、提供洞察
4. 专业友好，不过度热情

只返回JSON。"""
    
    @staticmethod
    def _get_understanding_prompt_en(user_message: str, stats: dict = None) -> str:
        """English understanding prompt"""
        total = stats.get('total', 44) if stats else 44
        tags = stats.get('tags', 125) if stats else 125
        
        return f"""You are an intelligent assistant planner. User has an archive management system ({total} archives, {tags} tags).

User said: "{user_message}"

Please understand the user's need and plan the response. Return JSON (no markdown):

{{
    "user_goal": "User's actual need (one sentence)",
    "question_type": "precise|open",  # precise=specific targeted question, open=exploratory question
    "need_data": {{
        "search_keywords": "If search needed, extract keywords; otherwise null",
        "need_statistics": true/false,
        "need_sample_archives": true/false,
        "need_tags_analysis": true/false
    }},
    "response_strategy": "Response approach (30 chars): direct answer/data analysis/search results/clarification",
    "reasoning": "Analysis rationale (50 chars)"
}}

Planning guidelines:
1. Determine question type
   - Precise: Clear goal, specific scope (e.g., "how many archives", "find Python content") → Focus on direct answer
   - Open: Exploratory, no clear scope (e.g., "what did I archive", "analyze my interests") → Can expand moderately
2. Precise questions return only required data, don't over-extend
3. Open questions can analyze trends and provide insights
4. Professional and friendly, not overly enthusiastic

Return JSON only."""
    
    @staticmethod
    def get_response_prompt(
        user_message: str,
        plan: dict,
        data_summary: str,
        language: str,
        conversation_history: list = None
    ) -> dict:
        """
        Get prompt for generating final response
        
        Args:
            user_message: User's original message
            plan: Understanding plan from Stage 1
            data_summary: Gathered data summary
            language: Language code
            conversation_history: Previous conversation messages
            
        Returns:
            Message list for API call
        """
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            return ChatPrompts._get_response_prompt_zh(
                user_message, plan, data_summary, conversation_history, is_traditional
            )
        else:
            return ChatPrompts._get_response_prompt_en(
                user_message, plan, data_summary, conversation_history
            )
    
    @staticmethod
    def _get_response_prompt_zh(
        user_message: str,
        plan: dict,
        data_summary: str,
        conversation_history: list = None,
        is_traditional: bool = False
    ) -> dict:
        """Chinese response prompt"""
        question_type = plan.get('question_type', 'open')
        
        if is_traditional:
            if question_type == 'precise':
                style_guide = """風格要求（精準問題模式）：
- 直接回答用戶的具體問題，不發散
- 只提供所需數據，不額外延伸
- 簡潔明了，控制在50-80字
- 如果數據充分，直接給結論；如果不足，明確說明
- 適度使用emoji（1個）"""
            else:
                style_guide = """風格要求（開放探索模式）：
- 可以從數據中發現趨勢和規律
- 適度發散，提供洞察和建議
- 字數60-100字，分3-4個小段
- 善於總結和歸納
- 適度使用emoji（1-2個）"""
            
            system_content = f"""你是歸檔助手，幫用戶管理和分析歸檔內容。

用戶需求：{plan.get('user_goal', '未知')}
問題類型：{question_type}
回覆策略：{plan.get('response_strategy', '友好回覆')}

{style_guide}

通用要求：
- 專業但不刻板，友好但有分寸
- 不用「嘿」、「哥們兒」等過分隨意的稱呼

回覆格式（重要）：
1. 分段表達，不要大段文字堆砌
2. 關鍵數據用列表：
   • 統計數據
   • 標籤TOP3
   • 主要發現
3. 用空行分隔不同部分
4. 總字數60-100字，但要分3-4個小段
5. 不用markdown標題（###）和加粗（**）

示例格式：
📊 共44條歸檔，125個標籤

熱門標籤：
• #技術 (12條)
• #學習 (8條) 
• #工具 (6條)

最近一週很活躍，歸檔了不少技術相關內容。要不要看看具體都是什麼？"""
        else:
            if question_type == 'precise':
                style_guide = """风格要求（精准问题模式）：
- 直接回答用户的具体问题，不发散
- 只提供所需数据，不额外延伸
- 简洁明了，控制在50-80字
- 如果数据充分，直接给结论；如果不足，明确说明
- 适度使用emoji（1个）"""
            else:
                style_guide = """风格要求（开放探索模式）：
- 可以从数据中发现趋势和规律
- 适度发散，提供洞察和建议
- 字数60-100字，分3-4个小段
- 善于总结和归纳
- 适度使用emoji（1-2个）"""
            
            system_content = f"""你是归档助手，帮用户管理和分析归档内容。

用户需求：{plan.get('user_goal', '未知')}
问题类型：{question_type}
回复策略：{plan.get('response_strategy', '友好回复')}

{style_guide}

通用要求：
- 专业但不刻板，友好但有分寸
- 不用「嘿」、「哥们儿」等过分随意的称呼

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
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 rounds
                if msg.startswith("用户: ") or msg.startswith("用戶: "):
                    messages.append({"role": "user", "content": msg[4:]})
                elif msg.startswith("AI: "):
                    messages.append({"role": "assistant", "content": msg[4:]})
        
        # Current question + data
        current_content = f"{user_message}\n\n【数据】\n{data_summary}" if not is_traditional else f"{user_message}\n\n【數據】\n{data_summary}"
        messages.append({"role": "user", "content": current_content})
        
        return messages
    
    @staticmethod
    def _get_response_prompt_en(
        user_message: str,
        plan: dict,
        data_summary: str,
        conversation_history: list = None
    ) -> dict:
        """English response prompt"""
        question_type = plan.get('question_type', 'open')
        
        if question_type == 'precise':
            style_guide = """Style requirements (Precise mode):
- Answer user's specific question directly, don't diverge
- Provide only required data, no extra extensions
- Concise and clear, 50-80 words
- Give conclusion if data sufficient; state clearly if insufficient
- Moderate emoji use (1)"""
        else:
            style_guide = """Style requirements (Exploratory mode):
- Discover trends and patterns from data
- Moderate expansion, provide insights and suggestions
- 60-100 words, 3-4 short paragraphs
- Good at summarizing and concluding
- Moderate emoji use (1-2)"""
        
        system_content = f"""You are an archive assistant helping users manage and analyze archived content.

User need: {plan.get('user_goal', 'Unknown')}
Question type: {question_type}
Response strategy: {plan.get('response_strategy', 'Friendly reply')}

{style_guide}

General requirements:
- Professional but not rigid, friendly but measured
- Don't use overly casual terms

Reply format (important):
1. Express in paragraphs, don't pile up text
2. Key data in lists:
   • Statistics
   • Top 3 tags
   • Main findings
3. Use blank lines to separate sections
4. Total 60-100 words, but split into 3-4 paragraphs
5. No markdown headers (###) or bold (**)

Example format:
📊 44 archives total, 125 tags

Popular tags:
• #tech (12 items)
• #learning (8 items)
• #tools (6 items)

Very active recently, archived lots of tech content. Want to see specifics?"""
        
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 rounds
                if msg.startswith("User: ") or msg.startswith("用户: ") or msg.startswith("用戶: "):
                    messages.append({"role": "user", "content": msg.split(": ", 1)[1]})
                elif msg.startswith("AI: "):
                    messages.append({"role": "assistant", "content": msg[4:]})
        
        # Current question + data
        current_content = f"{user_message}\n\n【Data】\n{data_summary}"
        messages.append({"role": "user", "content": current_content})
        
        return messages
