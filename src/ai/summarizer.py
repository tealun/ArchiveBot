"""
AI Summarizer - 云端API服务
"""
import logging, json, asyncio, re, time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from .prompts import PromptManager
from ..core.ai_cache import AICache, content_hash

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

def is_formal_content(content: str, content_type: str = '', category: str = '') -> bool:
    """
    判断内容是否属于技术/严肃/知识类（需要正式风格）
    
    Args:
        content: 内容文本
        content_type: 内容类型
        category: AI分类结果
        
    Returns:
        True表示正式内容，False表示轻松内容
    """
    # 正式类别关键词
    formal_categories = [
        '技术', '科技', '学习', '教育', '研究', '学术', '专业', '医疗', '法律', '金融',
        'Technology', 'Science', 'Learning', 'Education', 'Research', 'Academic', 
        'Professional', 'Medical', 'Legal', 'Finance', 'Business'
    ]
    
    # 轻松类别关键词
    casual_categories = [
        '娱乐', '生活', '日常', '美食', '旅游', '影视', '音乐', '游戏', '聊天',
        'Entertainment', 'Life', 'Daily', 'Food', 'Travel', 'Movie', 'Music', 'Game', 'Chat'
    ]
    
    # 优先根据分类判断
    if category:
        if any(keyword in category for keyword in formal_categories):
            return True
        if any(keyword in category for keyword in casual_categories):
            return False
    
    # 根据内容类型判断
    formal_types = ['document', 'pdf', 'code', 'data']
    if any(ftype in content_type.lower() for ftype in formal_types):
        return True
    
    # 根据内容关键词判断（技术类特征）
    tech_keywords = [
        'API', 'SDK', 'HTTP', 'JSON', 'SQL', 'Python', 'JavaScript', 'Git',
        '算法', '数据结构', '编程', '代码', '开发', '架构', '设计模式',
        '函数', '类', '方法', '变量', '配置', '部署', '测试'
    ]
    
    content_sample = content[:1000]
    tech_count = sum(1 for keyword in tech_keywords if keyword in content_sample)
    
    # 如果技术关键词出现3个以上，判定为正式内容
    if tech_count >= 3:
        return True
    
    # 默认返回轻松风格（更自然）
    return False

class AIProvider(ABC):
    @abstractmethod
    async def summarize(self, content: str, max_tokens: int = 500, language: str = 'zh-CN', 
                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: pass
    @abstractmethod
    async def generate_tags(self, content: str, max_tags: int = 5, language: str = 'zh-CN') -> List[str]: pass
    @abstractmethod
    async def categorize(self, content: str, language: str = 'zh-CN') -> str: pass

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

class AISummarizer:
    def __init__(self, config):
        self.config, self.provider = config, None
        self.cache = None
        self._last_call_info = {}
        if not config.get('enabled'):
            return

        # 只使用云端API
        api = config.get('api', {})
        # 使用 config.get() 方法以支持环境变量（AI_API_KEY）
        api_key = config.get('ai.api.api_key') or api.get('api_key') or api.get('api_key_env')
        if not api_key:
            logger.warning("AI enabled but no API key provided in config.api")
            # 继续允许 provider 初始化失败后的 graceful behavior
        provider_type = api.get('provider', 'openai')
        if provider_type in ['openai', 'grok']:
            try:
                temperature = config.get('ai.api.temperature', 0.7)
                self.provider = OpenAIProvider(
                    api_key,
                    config.get('ai.api.model') or api.get('model', 'gpt-3.5-turbo'),
                    config.get('ai.api.api_url') or api.get('api_url'),  # 支持自定义API URL
                    temperature
                )
                logger.info(f"Using {provider_type.upper()} API: {api.get('model', 'gpt-3.5-turbo')}")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_type} provider: {e}")

        # 初始化缓存（如果启用）
        try:
            cache_enabled = bool(config.get('cache_enabled', False))
            cache_path = config.get('cache_path') or api.get('cache_path') or 'data/ai_cache.db'
            cache_ttl = int(config.get('cache_ttl_seconds', 604800))
            if cache_enabled:
                try:
                    self.cache = AICache(db_path=cache_path, ttl=cache_ttl)
                    logger.info(f"AI cache enabled at {cache_path}, ttl={cache_ttl}s")
                except Exception as e:
                    logger.warning(f"Failed to initialize AI cache: {e}")
        except Exception:
            pass
        # 速率限制配置（calls per minute）
        try:
            self.rate_limit = int(config.get('rate_limit_per_minute', 0) or 0)
        except Exception:
            self.rate_limit = 0
        self._rate_count = 0
        self._rate_window_start = int(time.time())

    def _allow_call(self) -> bool:
        """简单的每分钟速率限制（非分布式）"""
        if not self.rate_limit or self.rate_limit <= 0:
            return True
        now = int(time.time())
        # window start per minute
        if now - self._rate_window_start >= 60:
            self._rate_window_start = now
            self._rate_count = 0
        if self._rate_count < self.rate_limit:
            self._rate_count += 1
            return True
        return False
    
    def is_available(self):
        """Check if AI provider is available"""
        return self.provider is not None and hasattr(self.provider, 'available') and self.provider.available
    
    async def summarize_content(self, content, url=None, language='zh-CN', context: Optional[Dict[str, Any]] = None):
        if not self.is_available():
            return {'success': False, 'error': 'AI不可用'}

        try:
            # 尝试从缓存读取（cache key 包含 model 与上下文以避免冲突）
            if self.cache:
                try:
                    ctx_ser = json.dumps(context or {}, sort_keys=True, ensure_ascii=False)
                    key_src = f"{getattr(self.provider, 'model', '')}|{ctx_ser}|{content}"
                    cache_key = content_hash(key_src)
                    cached = self.cache.get(cache_key)
                    if cached:
                        cached['success'] = True
                        cached['provider'] = 'CACHE'
                        return cached
                except Exception as e:
                    logger.debug(f"AI cache lookup error: {e}")

            # 速率检测：如超过限制，优先返回缓存或失败
            if not self._allow_call():
                logger.warning("AI rate limit reached, skipping external summarize call")
                if self.cache and cached:
                    cached['success'] = True
                    cached['provider'] = 'CACHE'
                    return cached
                return {'success': False, 'error': 'AI rate limit exceeded'}

            start = time.time()
            result = await self.provider.summarize(content, 1000, language=language, context=context)
            duration = time.time() - start
            result['success'] = True
            result['provider'] = 'CLOUD'
            # 记录调用信息
            try:
                self._last_call_info = {'provider': 'CLOUD', 'duration': duration}
            except Exception:
                pass

            # 如果summarize没有返回category，单独调用categorize
            default_category = '其他' if language.startswith('zh') else 'Other'
            if not result.get('category') or result.get('category') == default_category:
                result['category'] = await self.provider.categorize(content, language=language)

            # 写回缓存
            if self.cache:
                try:
                    ctx_ser = json.dumps(context or {}, sort_keys=True, ensure_ascii=False)
                    key_src = f"{getattr(self.provider, 'model', '')}|{ctx_ser}|{content}"
                    cache_key = content_hash(key_src)
                    self.cache.set(cache_key, result)
                except Exception as e:
                    logger.debug(f"AI cache write error: {e}")

            return result
        except Exception as e:
            try:
                self._last_call_info = {'provider': 'ERROR', 'duration': 0}
            except Exception:
                pass
            return {'success': False, 'error': str(e)}
    
    async def generate_tags(self, content, max_tags=5, language='zh-CN'):
        if not self.is_available(): return []
        try:
            # 缓存优先
            if self.cache:
                try:
                    key_src = f"tags|{getattr(self.provider, 'model', '')}|{max_tags}|{content}"
                    cache_key = content_hash(key_src)
                    cached = self.cache.get(cache_key)
                    if cached:
                        return cached
                except Exception as e:
                    logger.debug(f"AI tag cache lookup error: {e}")

            # 速率检测：如超过限制，优先返回缓存或空列表
            if not self._allow_call():
                logger.warning("AI rate limit reached, skipping external generate_tags call")
                if self.cache and cached:
                    try:
                        self._last_call_info = {'provider': 'CACHE', 'duration': 0}
                    except Exception:
                        pass
                    return cached
                try:
                    self._last_call_info = {'provider': 'RATE_LIMIT', 'duration': 0}
                except Exception:
                    pass
                return []

            start = time.time()
            tags = await self.provider.generate_tags(content, max_tags, language=language)
            duration = time.time() - start
            try:
                self._last_call_info = {'provider': 'CLOUD', 'duration': duration}
            except Exception:
                pass

            # 写回缓存
            if self.cache:
                try:
                    key_src = f"tags|{getattr(self.provider, 'model', '')}|{max_tags}|{content}"
                    cache_key = content_hash(key_src)
                    self.cache.set(cache_key, tags)
                except Exception as e:
                    logger.debug(f"AI tag cache write error: {e}")

            return tags
        except Exception as e:
            logger.error(f"Generate tags error: {e}")
            return []
    
    async def batch_generate_tags(self, contents: list, max_tags: int = 5, language: str = 'zh-CN'):
        """
        批量生成标签（并发处理）
        
        Args:
            contents: 内容列表
            max_tags: 每个内容的最大标签数
            language: 输出语言
        
        Returns:
            标签列表的列表
        """
        if not self.is_available():
            return [[] for _ in contents]
        
        start = time.time()
        tasks = [self.generate_tags(content, max_tags, language) for content in contents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        try:
            self._last_call_info = {'provider': 'BATCH', 'duration': time.time() - start}
        except Exception:
            pass
        return results
    
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
                    "max_tokens": 10,
                    "temperature": self.provider.temperature
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
            # 判断是否为正式内容
            is_formal = is_formal_content(content[:1000], content_type)
            
            # 构建prompt
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
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": self.provider.temperature
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
            # 判断是否为正式内容（基于分类）
            is_formal = is_formal_content("", "", ai_category)
            
            # 构建prompt
            key_points_text = '\n'.join([f"- {point}" for point in ai_key_points]) if ai_key_points else "无"
            
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
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": self.provider.temperature
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
            # 检测语言和判断内容类型
            detected_lang = detect_content_language(content)
            is_formal = is_formal_content(content[:1000])
            
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
            
            # 调用 API
            r = await self.provider.client.post(
                self.provider.api_url,
                json={
                    "model": self.provider.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": self.provider.temperature
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
