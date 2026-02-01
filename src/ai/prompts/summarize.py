"""
内容摘要分析 Prompt 模板
负责生成内容分析、分类、标签提取等功能的 prompts
支持简体中文、繁体中文和英文
"""


class SummarizePrompts:
    """内容摘要分析相关的 prompt 模板"""
    
    @staticmethod
    def get_role_description(is_formal: bool, language: str = 'zh-CN') -> str:
        """
        获取角色描述（供其他模块复用）
        
        Args:
            is_formal: 是否使用正式风格
            language: 语言代码
            
        Returns:
            角色描述字符串
        """
        if language.startswith('zh'):
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if is_formal:
                return "你是一位專業的技術資訊分析師，擅長處理技術文件、學術資料和專業內容。" if is_traditional else "你是一位专业的技术信息分析师，擅长处理技术文档、学术资料和专业内容。"
            else:
                return "你是個很會整理資訊的助手，對各種內容都有獨到的理解。" if is_traditional else "你是个很会整理信息的助手，对各种内容都有独到的理解。"
        else:
            if is_formal:
                return "You are a professional technical information analyst specializing in technical documentation, academic materials, and professional content."
            else:
                return "You're a helpful assistant who's great at organizing information and understanding various types of content."
    
    @staticmethod
    def get_prompt(
        content: str,
        is_formal: bool,
        language: str,
        language_instruction: str,
        context_info: str,
        example_categories: str,
        example_tags: str = ""
    ) -> str:
        """
        获取内容摘要分析的 prompt
        
        Args:
            content: 要分析的内容
            is_formal: 是否使用正式风格
            language: 语言代码
            language_instruction: 语言指令
            context_info: 上下文信息
            example_categories: 示例分类
            example_tags: 示例标签（中文需要）
            
        Returns:
            完整的 prompt 字符串
        """
        if language.startswith('zh'):
            # 判断是否为繁体中文
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            return SummarizePrompts._get_prompt_zh(
                content, is_formal, language_instruction, context_info, 
                example_categories, example_tags, is_traditional
            )
        else:
            return SummarizePrompts._get_prompt_en(
                content, is_formal, context_info
            )
    
    @staticmethod
    def _get_prompt_zh(
        content: str,
        is_formal: bool,
        language_instruction: str,
        context_info: str,
        example_categories: str,
        example_tags: str,
        is_traditional: bool = False
    ) -> str:
        """中文摘要 prompt（支持简繁体用词差异）"""
        if is_formal:
            # 正式风格 - 技术/严肃/知识类
            if is_traditional:
                role_desc = "你是一位專業的技術資訊分析師，擅長處理技術文件、學術資料和專業內容。"
                task_desc = """請幫我分析這份內容，需要你做到：
• 準確提煉核心技術要點和關鍵資訊
• 建立清晰的知識分類體系
• 生成便於檢索的專業標籤"""
                
                example = """參考示例（技術類）：
輸入：《深入理解電腦系統》第三版.pdf
輸出：{{
  "summary": "經典電腦系統教材，系統講解電腦組成原理、作業系統和程式最佳化",
  "key_points": ["電腦體系結構基礎", "系統級程式設計技術", "效能最佳化方法論"],
  "category": "技術",
  "suggested_tags": ["電腦系統", "教材", "系統程式設計", "技術書籍", "PDF文件"]
}}"""
                
                quality_guide = """輸出規範：
• 摘要控制在30-100字，客觀準確地描述核心內容
• 關鍵點每個10-30字，聚焦於重要資訊而非細枝末節
• 分類選擇一個最合適的主類別
• 標籤5個，組合使用主題詞和屬性詞，要精準可搜尋
  正例：「Python教學」、「機器學習」、「技術文件」
  反例：「檔案」、「資料」（過於寬泛）"""
            else:
                role_desc = "你是一位专业的技术信息分析师，擅长处理技术文档、学术资料和专业内容。"
                task_desc = """请帮我分析这份内容，需要你做到：
• 准确提炼核心技术要点和关键信息
• 建立清晰的知识分类体系
• 生成便于检索的专业标签"""
                
                example = """参考示例（技术类）：
输入：《深入理解计算机系统》第三版.pdf
输出：{{
  "summary": "经典计算机系统教材，系统讲解计算机组成原理、操作系统和程序优化",
  "key_points": ["计算机体系结构基础", "系统级编程技术", "性能优化方法论"],
  "category": "技术",
  "suggested_tags": ["计算机系统", "教材", "系统编程", "技术书籍", "PDF文档"]
}}"""
                
                quality_guide = """输出规范：
• 摘要控制在30-100字，客观准确地描述核心内容
• 关键点每个10-30字，聚焦于重要信息而非细枝末节
• 分类选择一个最合适的主类别
• 标签5个，组合使用主题词和属性词，要精准可搜索
  正例："Python教程"、"机器学习"、"技术文档"
  反例："文件"、"资料"（过于宽泛）"""
        else:
            # 轻松风格 - 生活/娱乐/日常类
            if is_traditional:
                role_desc = "你是個很會整理資訊的助手，對各種內容都有獨到的理解。"
                task_desc = """幫我看看這個內容講了什麼，你需要：
• 用簡潔的話說清楚核心內容
• 給它找個合適的分類
• 打上幾個好用的標籤，方便以後找"""
                
                example = """給你看個例子：
輸入：華爾街之狼電影片段.mp4
輸出：{{
  "summary": "一段關於華爾街交易員生活的電影片段，奢華、瘋狂又充滿慾望",
  "key_points": ["講金融圈的故事", "華爾街背景", "根據真人真事改編"],
  "category": "娛樂",
  "suggested_tags": ["電影片段", "金融題材", "傳記電影", "影視收藏", "李奧納多"]
}}"""
                
                quality_guide = """輸出要求：
• 摘要30-100字左右，說清楚就行，別太刻板
• 關鍵點每個10-30字，抓住要點即可
• 分類選一個最貼切的
• 標籤給5個，既要準確又要實用
  可以參考：「美食教學」、「旅行相片」、「電影推薦」
  別用這種：「內容」、「檔案」（太模糊了）"""
            else:
                role_desc = "你是个很会整理信息的助手，对各种内容都有独到的理解。"
                task_desc = """帮我看看这个内容讲了什么，你需要：
• 用简洁的话说清楚核心内容
• 给它找个合适的分类
• 打上几个好用的标签，方便以后找"""
                
                example = """给你看个例子：
输入：华尔街之狼电影片段.mp4
输出：{{
  "summary": "一段关于华尔街交易员生活的电影片段，奢华、疯狂又充满欲望",
  "key_points": ["讲金融圈的故事", "华尔街背景", "根据真人真事改编"],
  "category": "娱乐",
  "suggested_tags": ["电影片段", "金融题材", "传记电影", "影视收藏", "小李子"]
}}"""
                
                quality_guide = """输出要求：
• 摘要30-100字左右，说清楚就行，别太刻板
• 关键点每个10-30字，抓住要点即可
• 分类选一个最贴切的
• 标签给5个，既要准确又要实用
  可以参考："美食教程"、"旅行照片"、"电影推荐"
  别用这种："内容"、"文件"（太模糊了）"""
        
        return f"""{role_desc}
{task_desc}

{context_info}

{example}

{quality_guide}

待分析的内容：
{content[:4000]}

请用JSON格式回复（{language_instruction}）：
{{
  "summary": "简短总结（1-2句话）",
  "key_points": ["关键点1", "关键点2", "关键点3"],
  "category": "内容分类（参考：{example_categories}）",
  "suggested_tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}}"""
    
    @staticmethod
    def _get_prompt_en(
        content: str,
        is_formal: bool,
        context_info: str
    ) -> str:
        """英文摘要 prompt"""
        if is_formal:
            # Formal style for technical/serious content
            role_desc = "You are a professional technical information analyst specializing in technical documentation, academic materials, and professional content."
            task_desc = """Please help me analyze this content by:
• Accurately extracting core technical points and key information
• Establishing a clear knowledge classification
• Generating professional tags for easy retrieval"""
            
            example = """Example (Technical):
Input: Deep_Learning_by_Ian_Goodfellow.pdf
Output: {{
  "summary": "Comprehensive textbook on deep learning covering neural networks, optimization, and modern architectures",
  "key_points": ["Neural network fundamentals", "Training optimization methods", "CNN and RNN architectures"],
  "category": "Technology",
  "suggested_tags": ["Deep Learning", "Textbook", "AI", "Technical Book", "PDF"]
}}"""
            
            quality_guide = """Output specifications:
• Summary: 30-100 words, objective and accurate description
• Key points: 10-30 words each, focus on important information
• Category: Select one most appropriate main category
• Tags: 5 tags combining topic and attribute words, precise and searchable
  Good examples: "Python Tutorial", "Machine Learning", "Technical Doc"
  Avoid: "File", "Content" (too vague)"""
        else:
            # Casual style for life/entertainment content
            role_desc = "You're a helpful assistant who's great at organizing information and understanding various types of content."
            task_desc = """Help me understand what this content is about by:
• Explaining the core content in simple terms
• Finding a suitable category for it
• Adding some useful tags for later searching"""
            
            example = """Here's an example:
Input: The-Wolf-of-Wall-Street-clip.mp4
Output: {{
  "summary": "A movie clip about Wall Street traders' lifestyle - luxurious, wild, and full of ambition",
  "key_points": ["Story about finance world", "Wall Street setting", "Based on true events"],
  "category": "Entertainment",
  "suggested_tags": ["Movie Clip", "Finance Theme", "Biographical", "Film Collection", "DiCaprio"]
}}"""
            
            quality_guide = """Output requirements:
• Summary: Around 30-100 words, clear and natural
• Key points: 10-30 words each, capture the essence
• Category: Pick one that fits best
• Tags: 5 tags that are both accurate and practical
  Like: "Food Tutorial", "Travel Photos", "Movie Recommendation"
  Not: "Content", "File" (too vague)"""
        
        return f"""{role_desc}
{task_desc}

{context_info}

{example}

{quality_guide}

Content to analyze:
{content[:4000]}

Please respond in JSON format:
{{
  "summary": "Brief summary (1-2 sentences)",
  "key_points": ["Key point 1", "Key point 2", "Key point 3"],
  "category": "Content category",
  "suggested_tags": ["Tag1", "Tag2", "Tag3", "Tag4", "Tag5"]
}}"""
