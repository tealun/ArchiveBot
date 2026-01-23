"""
AI 降级策略模块
当 AI 不可用时，提供基础的内容分析能力
"""
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class AIFallbackAnalyzer:
    """AI 不可用时的降级分析器"""
    
    # 文件类型到分类的映射（简繁体）
    CATEGORY_MAP_ZH = {
        'document': {'zh-CN': '文档', 'zh-TW': '文件'},
        'image': {'zh-CN': '图片', 'zh-TW': '圖片'},
        'video': {'zh-CN': '视频', 'zh-TW': '影片'},
        'audio': {'zh-CN': '音频', 'zh-TW': '音訊'},
        'archive': {'zh-CN': '压缩包', 'zh-TW': '壓縮檔'},
        'code': {'zh-CN': '代码', 'zh-TW': '程式碼'},
        'ebook': {'zh-CN': '电子书', 'zh-TW': '電子書'},
        'other': {'zh-CN': '其他', 'zh-TW': '其他'}
    }
    
    CATEGORY_MAP_EN = {
        'document': 'Document',
        'image': 'Image',
        'video': 'Video',
        'audio': 'Audio',
        'archive': 'Archive',
        'code': 'Code',
        'ebook': 'E-book',
        'other': 'Other'
    }
    
    # 扩展名到类型的映射
    EXT_TO_TYPE = {
        # 文档
        'pdf': 'document', 'doc': 'document', 'docx': 'document', 
        'txt': 'document', 'md': 'document', 'rtf': 'document',
        'odt': 'document', 'pages': 'document',
        
        # 图片
        'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image',
        'webp': 'image', 'bmp': 'image', 'svg': 'image', 'ico': 'image',
        
        # 视频
        'mp4': 'video', 'avi': 'video', 'mkv': 'video', 'mov': 'video',
        'wmv': 'video', 'flv': 'video', 'webm': 'video', 'm4v': 'video',
        
        # 音频
        'mp3': 'audio', 'wav': 'audio', 'flac': 'audio', 'aac': 'audio',
        'ogg': 'audio', 'm4a': 'audio', 'wma': 'audio',
        
        # 压缩包
        'zip': 'archive', 'rar': 'archive', '7z': 'archive', 'tar': 'archive',
        'gz': 'archive', 'bz2': 'archive',
        
        # 代码
        'py': 'code', 'js': 'code', 'java': 'code', 'cpp': 'code',
        'c': 'code', 'h': 'code', 'ts': 'code', 'jsx': 'code',
        'go': 'code', 'rs': 'code', 'php': 'code', 'rb': 'code',
        
        # 电子书
        'epub': 'ebook', 'mobi': 'ebook', 'azw3': 'ebook', 'azw': 'ebook',
    }
    
    # 域名到分类的映射
    DOMAIN_CATEGORIES = {
        # 视频平台
        'youtube.com': 'video', 'youtu.be': 'video', 'bilibili.com': 'video',
        'vimeo.com': 'video', 'twitch.tv': 'video',
        
        # 技术平台
        'github.com': 'code', 'stackoverflow.com': 'code', 'gitlab.com': 'code',
        
        # 社交媒体
        'twitter.com': 'social', 'x.com': 'social', 'facebook.com': 'social',
        'instagram.com': 'social', 'weibo.com': 'social',
        
        # 新闻
        'nytimes.com': 'news', 'bbc.com': 'news', 'cnn.com': 'news',
        
        # 学术
        'arxiv.org': 'academic', 'scholar.google.com': 'academic',
    }
    
    # 简繁体常用词映射
    COMMON_TAGS_ZH = {
        'zh-CN': {
            'document': ['文档', 'PDF', '资料'],
            'image': ['图片', '照片', '截图'],
            'video': ['视频', '电影', '教程'],
            'audio': ['音频', '音乐', '播客'],
            'code': ['代码', '编程', '技术'],
            'ebook': ['电子书', '书籍', '阅读'],
        },
        'zh-TW': {
            'document': ['文件', 'PDF', '資料'],
            'image': ['圖片', '相片', '截圖'],
            'video': ['影片', '電影', '教學'],
            'audio': ['音訊', '音樂', '播客'],
            'code': ['程式碼', '程式設計', '技術'],
            'ebook': ['電子書', '書籍', '閱讀'],
        }
    }
    
    @staticmethod
    def analyze_file(
        file_name: str,
        file_ext: str,
        file_size: int = 0,
        language: str = 'zh-CN'
    ) -> Dict[str, Any]:
        """
        分析文件基础信息（无需 AI）
        
        Args:
            file_name: 文件名
            file_ext: 文件扩展名（带点，如 .pdf）
            file_size: 文件大小（字节）
            language: 用户语言
            
        Returns:
            分析结果字典
        """
        try:
            # 清理扩展名
            ext = file_ext.lower().lstrip('.')
            
            # 1. 确定文件类型
            file_type = AIFallbackAnalyzer.EXT_TO_TYPE.get(ext, 'other')
            
            # 2. 生成分类
            category = AIFallbackAnalyzer._get_category_name(file_type, language)
            
            # 3. 生成标题（清理文件名）
            title = AIFallbackAnalyzer._clean_filename(file_name)
            
            # 4. 生成标签
            tags = AIFallbackAnalyzer._generate_file_tags(
                file_name, ext, file_type, language
            )
            
            # 5. 生成简单摘要
            summary = AIFallbackAnalyzer._generate_file_summary(
                file_name, ext, file_size, language
            )
            
            logger.info(f"Fallback analysis for file: {file_name} → {category}")
            
            return {
                'success': True,
                'category': category,
                'title': title,
                'summary': summary,
                'tags': tags,
                'provider': 'FALLBACK',
                'file_type': file_type
            }
            
        except Exception as e:
            logger.error(f"Fallback file analysis error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'provider': 'FALLBACK'
            }
    
    @staticmethod
    def analyze_url(url: str, language: str = 'zh-CN') -> Dict[str, Any]:
        """
        分析 URL 基础信息（无需 AI）
        
        Args:
            url: URL 地址
            language: 用户语言
            
        Returns:
            分析结果字典
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            path = parsed.path
            
            # 1. 根据域名确定分类
            file_type = AIFallbackAnalyzer.DOMAIN_CATEGORIES.get(domain, 'other')
            category = AIFallbackAnalyzer._get_category_name(file_type, language)
            
            # 2. 生成标题
            if path and path != '/':
                # 从路径提取标题
                title = path.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            else:
                title = domain
            
            # 3. 生成标签
            tags = [domain]
            if language.startswith('zh'):
                lang_key = 'zh-TW' if language in ['zh-TW', 'zh-HK', 'zh-MO'] else 'zh-CN'
                tags.extend(AIFallbackAnalyzer.COMMON_TAGS_ZH[lang_key].get(file_type, [])[:2])
            else:
                tags.append(category)
            
            # 4. 生成简单摘要
            if language.startswith('zh'):
                summary = f"来自 {domain} 的链接"
            else:
                summary = f"Link from {domain}"
            
            logger.info(f"Fallback analysis for URL: {url} → {category}")
            
            return {
                'success': True,
                'category': category,
                'title': title[:50],  # 限制长度
                'summary': summary,
                'tags': tags[:5],
                'provider': 'FALLBACK'
            }
            
        except Exception as e:
            logger.error(f"Fallback URL analysis error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'provider': 'FALLBACK'
            }
    
    @staticmethod
    def analyze_text(
        content: str,
        content_type: str = 'text',
        language: str = 'zh-CN'
    ) -> Dict[str, Any]:
        """
        分析文本内容基础信息（无需 AI）
        
        Args:
            content: 文本内容
            content_type: 内容类型
            language: 用户语言
            
        Returns:
            分析结果字典
        """
        try:
            # 1. 生成分类（默认文本类）
            is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
            if language.startswith('zh'):
                category = '文字' if is_traditional else '文本'
            else:
                category = 'Text'
            
            # 2. 生成标题（使用前50字符）
            title = content[:50].strip()
            if len(content) > 50:
                title += "..."
            
            # 3. 生成摘要（使用前200字符）
            summary = content[:200].strip()
            if len(content) > 200:
                summary += "..."
            
            # 4. 简单的关键词提取
            tags = AIFallbackAnalyzer._extract_simple_keywords(content, language)
            
            logger.info(f"Fallback analysis for text: {len(content)} chars")
            
            return {
                'success': True,
                'category': category,
                'title': title,
                'summary': summary,
                'tags': tags,
                'provider': 'FALLBACK'
            }
            
        except Exception as e:
            logger.error(f"Fallback text analysis error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'provider': 'FALLBACK'
            }
    
    @staticmethod
    def _get_category_name(file_type: str, language: str) -> str:
        """获取分类名称"""
        if language.startswith('zh'):
            lang_key = 'zh-TW' if language in ['zh-TW', 'zh-HK', 'zh-MO'] else 'zh-CN'
            return AIFallbackAnalyzer.CATEGORY_MAP_ZH.get(file_type, {}).get(
                lang_key, 
                AIFallbackAnalyzer.CATEGORY_MAP_ZH['other'][lang_key]
            )
        else:
            return AIFallbackAnalyzer.CATEGORY_MAP_EN.get(file_type, 'Other')
    
    @staticmethod
    def _clean_filename(filename: str) -> str:
        """清理文件名，使其适合作为标题"""
        # 移除扩展名
        name = re.sub(r'\.[^.]+$', '', filename)
        
        # 替换常见分隔符为空格
        name = re.sub(r'[-_.]', ' ', name)
        
        # 移除多余空格
        name = ' '.join(name.split())
        
        # 限制长度
        if len(name) > 50:
            name = name[:47] + "..."
        
        return name or filename
    
    @staticmethod
    def _generate_file_tags(
        filename: str,
        ext: str,
        file_type: str,
        language: str
    ) -> List[str]:
        """生成文件标签"""
        tags = []
        
        # 1. 添加文件类型标签
        if language.startswith('zh'):
            lang_key = 'zh-TW' if language in ['zh-TW', 'zh-HK', 'zh-MO'] else 'zh-CN'
            tags.extend(AIFallbackAnalyzer.COMMON_TAGS_ZH[lang_key].get(file_type, [])[:2])
        else:
            tags.append(file_type.capitalize())
        
        # 2. 添加扩展名标签
        if ext:
            tags.append(ext.upper())
        
        # 3. 从文件名提取关键词
        keywords = AIFallbackAnalyzer._extract_filename_keywords(filename)
        tags.extend(keywords[:2])
        
        # 去重并限制数量
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag and tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags[:5]
    
    @staticmethod
    def _extract_filename_keywords(filename: str) -> List[str]:
        """从文件名提取关键词"""
        # 移除扩展名
        name = re.sub(r'\.[^.]+$', '', filename)
        
        # 分割并清理
        words = re.split(r'[-_.\s]+', name)
        
        # 过滤短词和数字
        keywords = [
            word for word in words 
            if len(word) > 2 and not word.isdigit()
        ]
        
        return keywords[:3]
    
    @staticmethod
    def _generate_file_summary(
        filename: str,
        ext: str,
        file_size: int,
        language: str
    ) -> str:
        """生成文件摘要"""
        size_str = AIFallbackAnalyzer._format_file_size(file_size)
        
        is_traditional = language in ['zh-TW', 'zh-HK', 'zh-MO']
        
        if language.startswith('zh'):
            if is_traditional:
                return f"{ext.upper()} 文件，大小 {size_str}"
            else:
                return f"{ext.upper()} 文件，大小 {size_str}"
        else:
            return f"{ext.upper()} file, size {size_str}"
    
    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "未知"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        
        return f"{size_bytes:.1f}TB"
    
    @staticmethod
    def _extract_simple_keywords(content: str, language: str) -> List[str]:
        """简单的关键词提取（基于长度和位置）"""
        # 对于中文，取前100个字符的词
        # 对于英文，取前100个单词
        
        if language.startswith('zh'):
            # 简单处理：提取数字、英文词、特殊符号周围的词
            keywords = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fa5]{2,}', content[:500])
        else:
            # 英文：按单词分割
            keywords = re.findall(r'\b[a-zA-Z]{3,}\b', content[:500])
        
        # 去重并限制数量
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and len(unique_keywords) < 5:
                seen.add(kw_lower)
                unique_keywords.append(kw)
        
        return unique_keywords[:5]
