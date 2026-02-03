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
from ..prompts import PromptManager
from ...core.ai_cache import AICache, content_hash

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProvider):
    def __init__(self, api_key, model="gpt-3.5-turbo", api_url=None, temperature=0.7):
        self.api_key, self.model = api_key, model
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
        self.temperature = temperature
        try:
            import httpx
            # 增加超时时间，添加重试配置
            # 数据隐私声明：通知AI服务商所有交互数据仅用于分析和生成内容，不得用于数据训练和公开
            privacy_headers = {
                "Authorization": f"Bearer {api_key}",
                "X-Data-Privacy": "no-training",  # 通用数据隐私声明
                "OpenAI-Beta": "user-data-opt-out",  # OpenAI特定的退出训练
            }
            self.client = httpx.AsyncClient(
                headers=privacy_headers, 
                timeout=httpx.Timeout(60.0, connect=10.0),  # 60秒总超时，10秒连接超时
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                transport=httpx.AsyncHTTPTransport(retries=2)  # 自动重试2次
            )
            self.available = True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI provider: {e}")
            self.available = False
    
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
            # 判断内容风格（正式/非正式）- 必须在使用前定义
            is_formal = is_formal_content(content[:1000], content_type)
            
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
            
            # 从 prompts 模块获取角色描述
            from ..prompts.summarize import SummarizePrompts
            role_desc = SummarizePrompts.get_role_description(is_formal, content_lang)
            
            # 构建上下文信息
            file_size_str = f"{file_size / 1024 / 1024:.2f}MB" if file_size > 0 else "文本内容"
            context_info = f"""给你一些背景信息：
• 内容类型是{content_type}{f'，具体是{file_ext}格式' if file_ext else ''}
• 文件大小{file_size_str}
• 用户之前已经打了这些标签：{', '.join(existing_tags) if existing_tags else '还没有'}（别重复了）
• 标题{title if title else '暂时没有'}
• 内容主要语言是{content_lang}
• 深度要求：{depth_instruction[analysis_depth]}"""
            
            # 使用 SummarizePrompts 统一生成 prompt
            prompt = SummarizePrompts.get_prompt(
                content=content,
                is_formal=is_formal,
                language=content_lang,
                language_instruction=language_instruction,
                context_info=context_info,
                example_categories=example_categories,
                example_tags=example_tags
            )
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
        # 支持中文逗号（、）和英文逗号（,）的分割
        tags = [t.strip().replace('#', '').replace('、', ',') for t in tags_str.replace('、', ',').split(',') if t.strip()][:max_tags]
        return tags
    
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
        except Exception as e:
            logger.warning(f"Failed to classify category: {e}")
            return default_category
