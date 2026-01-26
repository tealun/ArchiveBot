"""
OpenAI Provider implementation
"""

import logging
import json
import asyncio
import time
from typing import Dict, Any, List, Optional

from .base import AIProvider
from .utils import detect_content_language, is_formal_content
from ...prompts import PromptManager
from ....core.ai_cache import AICache, content_hash

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProvider):
    def __init__(self, api_key, model="gpt-3.5-turbo", api_url=None, temperature=0.7):
        self.api_key, self.model = api_key, model
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        self.temperature = temperature
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
            
            # 判断是否为正式内容
            is_formal = is_formal_content(content[:1000], content_type)
            
            # 构建上下文信息
            file_size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 0 else "文本内容"
            context_info = f"""给你一些背景信息：
• 内容类型是{content_type}{f'，具体是{file_ext}格式' if file_ext else ''}
• 文件大小{file_size_str}
• 用户之前已经打了这些标签：{', '.join(existing_tags) if existing_tags else '还没有'}（别重复了）
• 标题{title if title else '暂时没有'}
• 内容主要语言是{content_lang}
• 深度要求：{depth_instruction[analysis_depth]}"""
            
            # 根据内容风格选择不同的prompt
            if is_formal:
                # 正式风格 - 技术/严肃/知识类
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
            
            prompt = f"""{role_desc}
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
        else:
            # English prompt with style adaptation
            is_formal = is_formal_content(content[:1000], content_type)
            file_size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 0 else "Text content"
            context_info = f"""Here's some context:
• Content type is {content_type}{f', specifically {file_ext} format' if file_ext else ''}
• File size is {file_size_str}
• Existing tags: {', '.join(existing_tags) if existing_tags else 'none yet'} (avoid duplicates)
• Title is {title if title else 'not available'}
• Content language appears to be {content_lang}"""
            
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
            
            prompt = f"""{role_desc}
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
        
        r = await self.client.post(self.api_url,
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens, "temperature": self.temperature})
        
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
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 50, "temperature": self.temperature})
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
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 20, "temperature": self.temperature})
            category = r.json()['choices'][0]['message']['content'].strip()
            return category if category else default_category
        except:
            return default_category
