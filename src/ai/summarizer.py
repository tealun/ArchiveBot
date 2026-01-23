"""
AI Summarizer - 云端API服务
"""
import logging, json, asyncio, re
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)

def detect_content_language(content: str) -> str:
    """检测内容语言"""
    if not content:
        return 'unknown'
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content[:500]))
    # 统计英文字符
    english_chars = len(re.findall(r'[a-zA-Z]', content[:500]))
    
    if chinese_chars > english_chars * 2:
        return 'zh'
    elif english_chars > chinese_chars * 2:
        return 'en'
    else:
        return 'mixed'

class AIProvider(ABC):
    @abstractmethod
    async def summarize(self, content: str, max_tokens: int = 500, language: str = 'zh-CN', 
                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: pass
    @abstractmethod
    async def generate_tags(self, content: str, max_tags: int = 5, language: str = 'zh-CN') -> List[str]: pass
    @abstractmethod
    async def categorize(self, content: str, language: str = 'zh-CN') -> str: pass

class OpenAIProvider(AIProvider):
    def __init__(self, api_key, model="gpt-3.5-turbo", api_url=None):
        self.api_key, self.model = api_key, model
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        try:
            import httpx
            # 增加超时时间，添加重试配置
            self.client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {api_key}"}, 
                timeout=httpx.Timeout(60.0, connect=10.0),  # 60秒总超时，10秒连接超时
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                transport=httpx.AsyncHTTPTransport(retries=2)  # 自动重试2次
            )
            self.available = True
        except: self.available = False
    
    async def summarize(self, content, max_tokens=500, language='zh-CN', 
                       context: Optional[Dict[str, Any]] = None):
        """
        智能分析内容
        
        Args:
            content: 要分析的内容
            max_tokens: 最大token数
            language: 用户界面语言
            context: 上下文信息 (content_type, file_size, existing_tags, title, file_extension)
        """
        context = context or {}
        content_type = context.get('content_type', 'unknown')
        file_size = context.get('file_size', 0)
        existing_tags = context.get('existing_tags', [])
        title = context.get('title', '')
        file_ext = context.get('file_extension', '')
        
        # 检测内容语言
        content_lang = detect_content_language(content[:500])
        
        # 智能降级策略
        content_length = len(content)
        if content_length < 50:
            analysis_depth = 'minimal'  # 仅基于文件名
        elif content_length < 200:
            analysis_depth = 'brief'  # 简要分析
        else:
            analysis_depth = 'full'  # 完整分析
        
        # 根据语言设置prompt
        if language.startswith('zh'):
            # 区分简体和繁体中文
            if language in ['zh-TW', 'zh-HK', 'zh-MO']:
                language_instruction = "用繁體中文回答，請使用符合台灣/香港地區的用詞習慣（如：文件而非文檔、教學而非教程、影片而非視頻、相片而非照片等）"
                example_categories = "技術、生活、學習、娛樂、新聞等"
                example_tags = "電子書、小說、技術文件、教學、電影、影片、照片、證件相片、漫畫等"
                depth_instruction = {
                    'minimal': '基於檔案名稱和類型推測',
                    'brief': '簡要分析，重點標籤',
                    'full': '完整分析，包含摘要和關鍵點'
                }
            else:
                language_instruction = "用简体中文回答，请使用大陆地区的标准用词（如：文档、教程、视频、照片等）"
                example_categories = "技术、生活、学习、娱乐、新闻等"
                example_tags = "电子书、小说、技术文档、教程、电影、电影片段、照片、证件照、漫画等"
                depth_instruction = {
                    'minimal': '基于文件名和类型推测',
                    'brief': '简要分析，重点标签',
                    'full': '完整分析，包含摘要和关键点'
                }
            
            # 构建上下文信息
            file_size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 0 else "文本内容"
            context_info = f"""【上下文信息】
- 文件类型：{content_type}{f' ({file_ext})' if file_ext else ''}
- 文件大小：{file_size_str}
- 已有标签：{', '.join(existing_tags) if existing_tags else '无'}（请避免重复）
- 标题：{title if title else '无'}
- 内容语言：{content_lang}
- 分析深度：{depth_instruction[analysis_depth]}"""
            
            # 构建示例
            example = """【示例参考】
输入：华尔街之狼电影片段.mp4
输出：{{
  "summary": "描述华尔街金融交易员生活的电影片段，展示了奢华与欲望",
  "key_points": ["金融欺诈主题", "华尔街背景", "传记电影"],
  "category": "娱乐",
  "suggested_tags": ["电影", "金融", "传记", "影片片段", "马丁·斯科塞萨"]
}}"""
            
            # 构建输出质量约束
            quality_constraints = """【输出要求】
1. 摘要：30-100字，客观描述，不要主观评价
2. 关键点：每个10-30字，提取核心信息而非细节
3. 分类：只返回一个主分类
4. 标签：5个精准标签，格式：主题词+属性词
   - ✓ 正确示例："Python教程"、"机器学习"、"PDF文件"
   - ✗ 错误示例："文件"、"内容"、"资料"（太宽泛）"""
            
            # 构建思维链
            thinking_process = """【分析步骤】
第一步：识别内容类型和主题
第二步：提取核心信息和关键观点
第三步：确定适合的分类
第四步：生成精准、可搜索的标签（避免宽泛标签）"""
            
            prompt = f"""你是一位专业的信息管理员和知识组织专家。
你的任务是分析各类文档、媒体文件，帮助用户：
1. 快速理解核心内容
2. 建立清晰的分类体系
3. 创建精准的搜索标签

请对以下内容进行智能分析（{language_instruction}）：

{context_info}

{example}

{quality_constraints}

{thinking_process}

【待分析内容】
{content[:4000]}

请按JSON格式返回最终结果：
{{
  "summary": "核心观点的简短总结（1-2句话）",
  "key_points": ["关键点1", "关键点2", "关键点3"],
  "category": "内容分类（如：{example_categories}）",
  "suggested_tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]  (注意：标签应包含内容主题标签和文件属性标签，如：{example_tags})
}}"""
        else:
            # English prompt with all optimizations
            file_size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 0 else "Text content"
            context_info = f"""【Context Information】
- File Type: {content_type}{f' ({file_ext})' if file_ext else ''}
- File Size: {file_size_str}
- Existing Tags: {', '.join(existing_tags) if existing_tags else 'None'} (avoid duplication)
- Title: {title if title else 'None'}
- Content Language: {content_lang}"""
            
            example = """【Example Reference】
Input: The-Wolf-of-Wall-Street-clip.mp4
Output: {{
  "summary": "Movie clip depicting the life of Wall Street traders, showcasing luxury and desire",
  "key_points": ["Financial fraud theme", "Wall Street setting", "Biographical film"],
  "category": "Entertainment",
  "suggested_tags": ["Movie", "Finance", "Biography", "Movie Clip", "Martin Scorsese"]
}}"""
            
            quality_constraints = """【Output Requirements】
1. Summary: 30-100 words, objective description, no subjective comments
2. Key Points: 10-30 words each, extract core info not details
3. Category: Return only one main category
4. Tags: 5 precise tags, format: topic + attribute
   - ✓ Correct: "Python Tutorial", "Machine Learning", "PDF Document"
   - ✗ Wrong: "File", "Content", "Material" (too broad)"""
            
            prompt = f"""You are a professional information manager and knowledge organization expert.
Your task is to analyze various documents and media files to help users:
1. Quickly understand core content
2. Establish clear classification systems
3. Create precise search tags

Please analyze the following content intelligently (respond in English):

{context_info}

{example}

{quality_constraints}

【Analysis Steps】
Step 1: Identify content type and theme
Step 2: Extract core information and key points
Step 3: Determine appropriate category
Step 4: Generate precise, searchable tags (avoid broad tags)

【Content to Analyze】
{content[:4000]}

Return in JSON format:
{{
  "summary": "Brief summary of core ideas (1-2 sentences)",
  "key_points": ["Key point 1", "Key point 2", "Key point 3"],
  "category": "Content category (e.g., Technology, Life, Learning, Entertainment, News, etc.)",
  "suggested_tags": ["Tag1", "Tag2", "Tag3", "Tag4", "Tag5"]  (Note: Tags should include content topic tags and file attribute tags)
}}"""
        
        r = await self.client.post(self.api_url,
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens})
        
        response_text = r.json()['choices'][0]['message']['content']
        
        # 尝试解析JSON
        try:
            # 提取JSON部分（有些模型会在前后加说明文字）
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'summary': result.get('summary', ''),
                    'key_points': result.get('key_points', []),
                    'category': result.get('category', '其他'),
                    'suggested_tags': result.get('suggested_tags', [])
                }
        except Exception as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
        
        # 降级：返回原始文本作为摘要
        return {'summary': response_text, 'key_points': [], 'category': '其他', 'suggested_tags': []}
    
    async def generate_tags(self, content, max_tags=5, language='zh-CN'):
        if language.startswith('zh'):
            # 区分简体和繁体中文
            if language in ['zh-TW', 'zh-HK', 'zh-MO']:
                prompt = f"為以下內容生成{max_tags}個繁體中文標籤（逗號分隔）。請使用符合台灣/香港地區的用詞習慣（如：文件、教學、影片、相片等）。標籤應包含內容主題標籤和文件屬性標籤（如：電子書、小說、技術文件、教學、電影、影片、照片、證件相片、漫畫等）：\n{content[:1000]}"
            else:
                prompt = f"为以下内容生成{max_tags}个简体中文标签（逗号分隔）。请使用大陆地区的标准用词（如：文档、教程、视频、照片等）。标签应包含内容主题标签和文件属性标签（如：电子书、小说、技术文档、教程、电影、电影片段、照片、证件照、漫画等）：\n{content[:1000]}"
        else:
            prompt = f"Generate {max_tags} tags in English (comma-separated) for the following content. Tags should include content topic tags and file attribute tags (e.g., eBook, Novel, Technical Documentation, Tutorial, Movie, Movie Clip, Photo, ID Photo, Comic, etc.):\n{content[:1000]}"
        
        r = await self.client.post(self.api_url,
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 50})
        tags_str = r.json()['choices'][0]['message']['content']
        return [t.strip().replace('#', '') for t in tags_str.split(',') if t.strip()][:max_tags]
    
    async def categorize(self, content, language='zh-CN'):
        if language.startswith('zh'):
            # 区分简体和繁体中文
            if language in ['zh-TW', 'zh-HK', 'zh-MO']:
                prompt = "請對以下內容進行分類只返回分類名稱\n"
                prompt += "請使用符合台灣香港地區的用詞習慣如技術學習娛樂等\n\n"
                prompt += f"{content[:500]}\n\n分類"
                default_category = "其他"
            else:
                prompt = "请对以下内容进行分类只返回分类名称\n"
                prompt += "如技术生活学习娱乐新闻工作健康等\n\n"
                prompt += f"{content[:500]}\n\n分类"
                default_category = "其他"
        else:
            prompt = "Please categorize the following content return only the category name\n"
            prompt += "e.g. Technology Life Learning Entertainment News Work Health etc\n\n"
            prompt += f"{content[:500]}\n\nCategory"
            default_category = "Other"
        
        try:
            r = await self.client.post(self.api_url,
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 20})
            category = r.json()['choices'][0]['message']['content'].strip()
            return category if category else default_category
        except:
            return default_category

class AISummarizer:
    def __init__(self, config):
        self.config, self.provider = config, None
        if not config.get('enabled'): return
        
        # 只使用云端API
        api = config.get('api', {})
        if not api.get('api_key'): 
            logger.warning("AI enabled but no API key provided")
            return
        
        provider_type = api.get('provider', 'openai')
        if provider_type in ['openai', 'grok']:
            try:
                self.provider = OpenAIProvider(
                    api['api_key'], 
                    api.get('model', 'gpt-3.5-turbo'),
                    api.get('api_url')  # 支持自定义API URL
                )
                logger.info(f"Using {provider_type.upper()} API: {api.get('model', 'gpt-3.5-turbo')}")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_type} provider: {e}")
    
    def is_available(self):
        """Check if AI provider is available"""
        return self.provider is not None and hasattr(self.provider, 'available') and self.provider.available
    
    async def summarize_content(self, content, url=None, language='zh-CN', context: Optional[Dict[str, Any]] = None):
        if not self.is_available(): return {'success': False, 'error': 'AI不可用'}
        try:
            result = await self.provider.summarize(content, 1000, language=language, context=context)
            result['success'] = True
            result['provider'] = 'CLOUD'
            
            # 如果summarize没有返回category，单独调用categorize
            default_category = '其他' if language.startswith('zh') else 'Other'
            if not result.get('category') or result.get('category') == default_category:
                result['category'] = await self.provider.categorize(content, language=language)
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def generate_tags(self, content, max_tags=5, language='zh-CN'):
        if not self.is_available(): return []
        try:
            return await self.provider.generate_tags(content, max_tags, language=language)
        except Exception as e:
            logger.error(f"Generate tags error: {e}")
            return []
    
    async def batch_generate_tags(self, contents: list, max_tags: int = 5):
        """
        批量生成标签（并发处理）
        
        Args:
            contents: 内容列表
            max_tags: 每个内容的最大标签数
        
        Returns:
            标签列表的列表
        """
        if not self.is_available():
            return [[] for _ in contents]
        
        tasks = [self.generate_tags(content, max_tags) for content in contents]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def is_ebook(self, file_name: str, language: str = 'zh-CN') -> bool:
        """
        判断文件是否为电子书（书籍、杂志、报刊、画报等）
        
        Args:
            file_name: 文件名
            language: 用户界面语言
            
        Returns:
            True表示是电子书，False表示不是
        """
        if not self.is_available():
            return False
        
        try:
            # 根据语言构建prompt
            if language.startswith('zh'):
                if language in ['zh-TW', 'zh-HK', 'zh-MO']:
                    prompt = "請判斷以下檔案名稱是否為電子書\n"
                    prompt += "包括書籍雜誌期刊畫報漫畫等\n"
                    prompt += "只需回答是或否\n\n"
                    prompt += f"檔案名稱{file_name}\n\n這是電子書嗎"
                else:
                    prompt = "请判断以下文件名是否为电子书\n"
                    prompt += "包括书籍杂志期刊画报漫画等\n"
                    prompt += "只需回答是或否\n\n"
                    prompt += f"文件名{file_name}\n\n这是电子书吗"
            else:
                prompt = "Please determine if the following file name is an eBook\n"
                prompt += "including books magazines journals pictorials comics etc\n"
                prompt += "Just answer Yes or No\n\n"
                prompt += f"File name {file_name}\n\nIs this an eBook"
            
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10
                }
            )
            
            response = r.json()['choices'][0]['message']['content'].strip().lower()
            
            # 判断回答
            positive_answers = ['yes', '是', 'true', 'y']
            return any(ans in response for ans in positive_answers)
            
        except Exception as e:
            logger.error(f"AI判断电子书失败: {e}")
            return False
    
    async def generate_tags_batch(self, contents: list, max_tags: int = 5) -> list:
        """
        批量生成标签
        
        Args:
            contents: 内容列表
            max_tags: 每个内容的最大标签数
            
        Returns:
            标签列表的列表 [[tags1], [tags2], ...]
        """
        if not self.is_available():
            return [[] for _ in contents]
        
        try:
            # 并发调用AI生成标签
            tasks = [self.generate_tags(content, max_tags) for content in contents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果（过滤异常）
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch tag generation failed for item {i}: {result}")
                    final_results.append([])
                else:
                    final_results.append(result)
            
            logger.info(f"Batch generated tags for {len(contents)} items")
            return final_results
            
        except Exception as e:
            logger.error(f"Batch generate tags error: {e}", exc_info=True)
            return [[] for _ in contents]
    
    async def generate_note_from_content(
        self,
        content: str,
        content_type: str,
        max_length: int = 250,
        language: str = 'zh-CN'
    ) -> str:
        """
        根据内容生成笔记
        
        Args:
            content: 原始内容
            content_type: 内容类型 (text/link/document)
            max_length: 笔记最大长度
            language: 语言
            
        Returns:
            生成的笔记内容
        """
        if not self.is_available():
            return ""
        
        try:
            # 构建prompt
            if language.startswith('zh'):
                prompt = f"请为以下{content_type}内容生成一份简洁的笔记({max_length}字以内)\n\n"
                prompt += "要求:\n"
                prompt += "1. 突出核心内容和关键信息\n"
                prompt += "2. 使用清晰简练的语言\n"
                prompt += "3. 适合快速回顾和检索\n"
                prompt += "4. 不要在末尾添加字数统计或任何元信息\n\n"
                prompt += f"内容:\n{content[:3000]}\n\n"
                prompt += "请直接输出笔记文本"
            else:
                prompt = f"Please generate a concise note (within {max_length} words) for the following {content_type} content.\n\n"
                prompt += "Requirements:\n"
                prompt += "1. Highlight core content and key information\n"
                prompt += "2. Use clear and concise language\n"
                prompt += "3. Suitable for quick review and search\n"
                prompt += "4. Do not add word count or any meta information at the end\n\n"
                prompt += f"Content:\n{content[:3000]}\n\n"
                prompt += "Output the note text directly"
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500
                }
            )
            note_content = r.json()['choices'][0]['message']['content'].strip()
            
            logger.info(f"Generated note from content: {len(note_content)} chars")
            return note_content
            
        except Exception as e:
            logger.error(f"Generate note from content error: {e}", exc_info=True)
            return ""
    
    async def generate_note_from_ai_analysis(
        self,
        ai_summary: str,
        ai_key_points: List[str],
        ai_category: str,
        title: str,
        language: str = 'zh-CN'
    ) -> str:
        """
        根据AI分析结果整理文档笔记
        
        Args:
            ai_summary: AI摘要
            ai_key_points: AI关键点
            ai_category: AI分类
            title: 文档标题
            language: 语言
            
        Returns:
            整理的完整笔记
        """
        if not self.is_available():
            return ""
        
        try:
            # 构建prompt
            key_points_text = '\n'.join([f"- {point}" for point in ai_key_points]) if ai_key_points else "无"
            
            if language.startswith('zh'):
                prompt = f"请根据以下AI分析内容整理一份完整的文档笔记\n\n"
                prompt += f"文档标题: {title}\n"
                prompt += f"分类: {ai_category}\n\n"
                prompt += f"AI摘要:\n{ai_summary}\n\n"
                prompt += f"关键点:\n{key_points_text}\n\n"
                prompt += "要求:\n"
                prompt += "1. 整合摘要和关键点信息\n"
                prompt += "2. 组织成结构清晰的笔记格式\n"
                prompt += "3. 便于理解和记忆\n"
                prompt += "4. 不要在末尾添加字数统计或任何元信息\n\n"
                prompt += "请直接输出笔记文本"
            else:
                prompt = "Please organize a complete document note based on the following AI analysis.\n\n"
                prompt += f"Document Title: {title}\n"
                prompt += f"Category: {ai_category}\n\n"
                prompt += f"AI Summary:\n{ai_summary}\n\n"
                prompt += f"Key Points:\n{key_points_text}\n\n"
                prompt += "Requirements:\n"
                prompt += "1. Integrate summary and key points\n"
                prompt += "2. Organize into clear note format\n"
                prompt += "3. Easy to understand and remember\n"
                prompt += "4. Do not add word count or any meta information at the end\n\n"
                prompt += "Output the note text directly"
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000
                }
            )
            note_content = r.json()['choices'][0]['message']['content'].strip()
            
            logger.info(f"Generated note from AI analysis: {len(note_content)} chars")
            return note_content
            
        except Exception as e:
            logger.error(f"Generate note from AI analysis error: {e}", exc_info=True)
            return ""
    
    async def generate_title_from_text(self, content: str, max_length: int = 32, language: str = 'zh-CN') -> str:
        """
        从文本内容生成标题
        
        Args:
            content: 文本内容
            max_length: 标题最大长度(字符数)
            language: 语言代码
            
        Returns:
            生成的标题
        """
        if not content or not content.strip():
            return "无标题"
        
        try:
            # 检测语言
            detected_lang = detect_content_language(content)
            
            if language.startswith('zh') or detected_lang == 'zh':
                prompt = "请为以下文本生成一个简洁准确的标题\n\n要求:\n"
                prompt += f"1. 标题长度不超过{max_length}个字符\n"
                prompt += "2. 准确概括文本核心内容\n"
                prompt += "3. 简洁明了便于理解\n"
                prompt += "4. 不要使用引号或其他标点符号包裹标题\n"
                prompt += "5. 直接输出标题文本不要任何解释\n\n"
                prompt += f"文本内容:\n{content[:1000]}\n\n"
                prompt += "请直接输出标题"
            else:
                prompt = "Generate a concise and accurate title for the following text.\n\n"
                prompt += "Requirements:\n"
                prompt += f"1. Title length should not exceed {max_length} characters\n"
                prompt += "2. Accurately summarize the core content\n"
                prompt += "3. Clear and easy to understand\n"
                prompt += "4. Do not use quotes or other punctuation to wrap the title\n"
                prompt += "5. Output only the title text, no explanations\n\n"
                prompt += f"Text content:\n{content[:1000]}\n\n"
                prompt += "Output the title directly"
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50
                }
            )
            title = r.json()['choices'][0]['message']['content'].strip()
            
            # 移除可能的引号
            title = title.strip('"\'""''')
            
            # 确保标题不超过最大长度
            if len(title) > max_length:
                title = title[:max_length-3] + "..."
            
            logger.info(f"Generated title from text: {title}")
            return title
            
        except Exception as e:
            logger.error(f"Generate title from text error: {e}", exc_info=True)
            # 降级：返回截断的文本
            fallback = content[:max_length].strip()
            if len(content) > max_length:
                fallback = fallback[:max_length-3] + "..."
            return fallback

_summarizer = None
def get_ai_summarizer(config=None):
    global _summarizer
    if not _summarizer and config: _summarizer = AISummarizer(config)
    return _summarizer

async def summarize_link(url, content, config):
    summarizer = get_ai_summarizer(config)
    return await summarizer.summarize_content(content, url)
