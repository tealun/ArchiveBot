"""
Content extraction from HTML
使用trafilatura和readability提取正文
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractResult:
    """正文提取结果"""
    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    word_count: int = 0
    language: Optional[str] = None
    extractor_used: Optional[str] = None
    quality_score: float = 0.0
    error: Optional[str] = None


class ContentExtractor:
    """智能正文提取器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.min_length = self.config.get('min_length', 200)
        self.favor_recall = self.config.get('favor_recall', True)
    
    def extract(self, html: str, url: str = None) -> ExtractResult:
        """
        从HTML提取正文（多策略）
        
        Args:
            html: HTML内容
            url: 页面URL（可选）
            
        Returns:
            ExtractResult对象
        """
        if not html:
            return ExtractResult(
                success=False,
                error="No HTML content"
            )
        
        # 策略1: Trafilatura（主）
        result = self._extract_with_trafilatura(html, url)
        if result.success and result.word_count >= self.min_length:
            logger.info(f"Trafilatura extraction success: {result.word_count} chars")
            return result
        
        # 策略2: Readability（备）
        result = self._extract_with_readability(html)
        if result.success:
            logger.info(f"Readability extraction success: {result.word_count} chars")
            return result
        
        # 策略3: 基础提取（兜底）
        result = self._extract_basic(html)
        logger.info(f"Basic extraction: {result.word_count} chars")
        return result
    
    def _extract_with_trafilatura(self, html: str, url: str = None) -> ExtractResult:
        """使用trafilatura提取正文"""
        try:
            import trafilatura
            
            # 提取正文（保留格式）
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_recall=self.favor_recall,  # 宁滥勿缺
                url=url,
                output_format='txt',  # 纯文本格式
                include_formatting=True  # 保留基本格式（段落、换行）
            )
            
            if not content:
                return ExtractResult(success=False, error="No content extracted")
            
            # 规范化段落格式：确保段落之间有明确的空行
            # trafilatura 的段落用 \n\n 分隔，但有时不一致
            lines = content.split('\n')
            formatted_lines = []
            prev_empty = False
            
            for line in lines:
                line_stripped = line.strip()
                is_empty = not line_stripped
                
                if is_empty:
                    # 连续空行只保留一个
                    if not prev_empty:
                        formatted_lines.append('')
                    prev_empty = True
                else:
                    formatted_lines.append(line_stripped)
                    prev_empty = False
            
            # 组合成格式化的文本
            content = '\n\n'.join(
                para for para in '\n'.join(formatted_lines).split('\n\n') 
                if para.strip()
            )
            
            # 提取metadata
            metadata = trafilatura.extract_metadata(html)
            
            title = None
            author = None
            date = None
            language = None
            
            if metadata:
                title = metadata.title
                author = metadata.author
                date = metadata.date
                language = metadata.language
            
            word_count = len(content)
            
            # 计算质量分数
            quality_score = self._calculate_quality(content, title, author, date)
            
            return ExtractResult(
                success=True,
                content=content,
                title=title,
                author=author,
                date=date,
                word_count=word_count,
                language=language,
                extractor_used='trafilatura',
                quality_score=quality_score
            )
            
        except ImportError:
            logger.warning("trafilatura not installed, skipping")
            return ExtractResult(success=False, error="trafilatura not available")
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
            return ExtractResult(success=False, error=str(e))
    
    def _extract_with_readability(self, html: str) -> ExtractResult:
        """使用readability提取正文"""
        try:
            from readability import Document
            from bs4 import BeautifulSoup
            
            doc = Document(html)
            
            title = doc.title()
            html_content = doc.summary()
            
            # 清理HTML标签
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除script和style标签
            for tag in soup(['script', 'style']):
                tag.decompose()
            
            content = soup.get_text(separator='\n', strip=True)
            
            if not content:
                return ExtractResult(success=False, error="No content extracted")
            
            word_count = len(content)
            
            # 计算质量分数
            quality_score = self._calculate_quality(content, title, None, None)
            
            return ExtractResult(
                success=True,
                content=content,
                title=title,
                word_count=word_count,
                extractor_used='readability',
                quality_score=quality_score * 0.8  # readability质量稍低
            )
            
        except ImportError:
            logger.warning("readability-lxml not installed, skipping")
            return ExtractResult(success=False, error="readability not available")
        except Exception as e:
            logger.warning(f"Readability extraction failed: {e}")
            return ExtractResult(success=False, error=str(e))
    
    def _extract_basic(self, html: str) -> ExtractResult:
        """基础提取（BeautifulSoup兜底）"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取title
            title_tag = soup.find('title')
            title = title_tag.get_text() if title_tag else None
            
            # 移除不需要的标签
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # 提取文本
            content = soup.get_text(separator='\n', strip=True)
            
            word_count = len(content)
            
            return ExtractResult(
                success=bool(content),
                content=content if content else None,
                title=title,
                word_count=word_count,
                extractor_used='basic',
                quality_score=0.3,  # 基础提取质量较低
                error=None if content else "No content found"
            )
            
        except Exception as e:
            logger.error(f"Basic extraction failed: {e}")
            return ExtractResult(
                success=False,
                error=str(e)
            )
    
    def _calculate_quality(self, content: str, title: str, author: str, date: str) -> float:
        """计算提取质量分数"""
        score = 0.0
        
        # 内容长度（0-0.5）
        if content:
            content_len = len(content)
            if content_len > 3000:
                score += 0.5
            elif content_len > 1500:
                score += 0.4
            elif content_len > 800:
                score += 0.3
            elif content_len > 400:
                score += 0.2
            elif content_len > 200:
                score += 0.1
        
        # Metadata完整性（0-0.5）
        if title:
            score += 0.2
        if author:
            score += 0.15
        if date:
            score += 0.15
        
        return min(score, 1.0)
