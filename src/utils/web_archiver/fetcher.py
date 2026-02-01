"""
Main web archiver module
智能网页抓取、正文提取、PDF生成、AI摘要的统一入口
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from .strategies import HttpStrategy, TelegramStrategy, FetchResult
from .extractors import ContentExtractor, MetadataExtractor
from .generators import PDFGenerator
from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ArchiveResult:
    """网页归档结果"""
    success: bool
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    pdf_bytes: Optional[bytes] = None
    quality_score: float = 0.0
    strategies_tried: list = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # PDF bytes不序列化
        if 'pdf_bytes' in data:
            data['pdf_bytes'] = f"<{len(self.pdf_bytes)} bytes>" if self.pdf_bytes else None
        return data


class WebArchiver:
    """
    智能网页归档器
    
    功能：
    1. 多策略抓取（HTTP -> Telegram预览）
    2. 智能正文提取（trafilatura + readability）
    3. PDF生成（weasyprint）
    4. AI摘要（复用现有summarizer）
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化归档器
        
        Args:
            config: 配置字典，如果为None则从全局配置读取
        """
        if config is None:
            global_config = get_config()
            config = global_config.get('web_archiver', {})
        
        self.config = config
        self.enabled = self.config.get('enabled', True)
        
        # 初始化各模块
        self._init_strategies()
        self._init_extractors()
        self._init_generators()
        
        # 质量阈值
        self.quality_thresholds = self.config.get('quality', {})
        self.min_score_for_pdf = self.quality_thresholds.get('min_score_for_pdf', 0.5)
        self.min_score_for_ai = self.quality_thresholds.get('min_score_for_ai', 0.3)
        
        logger.info(f"WebArchiver initialized: enabled={self.enabled}")
    
    def _init_strategies(self):
        """初始化抓取策略"""
        strategies_config = self.config.get('strategies', {})
        
        self.strategies = []
        
        # HTTP策略
        if strategies_config.get('http', {}).get('enabled', True):
            http_config = strategies_config.get('http', {})
            self.strategies.append(HttpStrategy(http_config))
        
        # Telegram预览策略（总是启用，作为fallback）
        telegram_config = strategies_config.get('telegram', {})
        self.strategies.append(TelegramStrategy(telegram_config))
        
        logger.info(f"Initialized {len(self.strategies)} fetch strategies")
    
    def _init_extractors(self):
        """初始化提取器"""
        extraction_config = self.config.get('content_extraction', {})
        self.content_extractor = ContentExtractor(extraction_config)
        self.metadata_extractor = MetadataExtractor()
    
    def _init_generators(self):
        """初始化生成器"""
        pdf_config = self.config.get('pdf_generation', {})
        self.pdf_generator = PDFGenerator(pdf_config)
        self.pdf_enabled = pdf_config.get('enabled', True)
    
    async def archive(
        self,
        url: str,
        telegram_message=None,
        generate_pdf: bool = None,
        generate_summary: bool = None
    ) -> ArchiveResult:
        """
        归档网页（完整流程）
        
        Args:
            url: 目标URL
            telegram_message: Telegram消息对象（可选，用于提取预览）
            generate_pdf: 是否生成PDF（None=自动判断）
            generate_summary: 是否生成AI摘要（None=自动判断）
            
        Returns:
            ArchiveResult对象
        """
        if not self.enabled:
            logger.warning("WebArchiver is disabled")
            return ArchiveResult(
                success=False,
                url=url,
                error="WebArchiver disabled"
            )
        
        logger.info(f"Archiving: {url}")
        strategies_tried = []
        
        # 步骤1: 抓取网页
        fetch_result = await self._fetch_with_fallback(url, telegram_message)
        strategies_tried.append(fetch_result.strategy_used)
        
        if not fetch_result.success:
            logger.warning(f"All fetch strategies failed for {url}")
            return ArchiveResult(
                success=False,
                url=url,
                error=fetch_result.error,
                strategies_tried=strategies_tried
            )
        
        # 步骤2: 提取正文和元数据
        title, content, metadata = await self._extract_content(fetch_result)
        
        # 步骤3: 计算最终质量分数
        quality_score = self._calculate_final_quality(fetch_result, content)
        
        logger.info(f"Final quality score: {quality_score:.2f}")
        
        # 步骤4: 决定是否生成PDF
        should_generate_pdf = self._should_generate_pdf(
            quality_score,
            content,
            generate_pdf
        )
        
        pdf_bytes = None
        if should_generate_pdf:
            pdf_bytes = await self._generate_pdf(
                fetch_result,
                title,
                url,
                metadata
            )
        
        # 步骤5: 决定是否生成AI摘要
        should_generate_summary = self._should_generate_summary(
            quality_score,
            content,
            generate_summary
        )
        
        summary = None
        if should_generate_summary:
            summary = await self._generate_summary(content, url)
        
        return ArchiveResult(
            success=True,
            url=url,
            title=title,
            content=content,
            summary=summary,
            metadata=metadata,
            pdf_bytes=pdf_bytes,
            quality_score=quality_score,
            strategies_tried=strategies_tried
        )
    
    async def _fetch_with_fallback(
        self,
        url: str,
        telegram_message=None
    ) -> FetchResult:
        """多策略抓取（自动fallback）"""
        for strategy in self.strategies:
            try:
                logger.info(f"Trying strategy: {strategy.name}")
                
                kwargs = {}
                if isinstance(strategy, TelegramStrategy):
                    kwargs['telegram_message'] = telegram_message
                
                result = await strategy.fetch(url, **kwargs)
                
                if result.success and result.quality_score > 0.2:
                    logger.info(f"Strategy {strategy.name} succeeded: quality={result.quality_score:.2f}")
                    return result
                else:
                    logger.info(f"Strategy {strategy.name} low quality, trying next")
                    
            except Exception as e:
                logger.warning(f"Strategy {strategy.name} error: {e}")
                continue
        
        # 全部失败
        return FetchResult.empty(url, "All strategies failed")
    
    async def _extract_content(self, fetch_result: FetchResult) -> tuple:
        """提取正文和元数据"""
        title = fetch_result.title
        content = fetch_result.text
        metadata = fetch_result.metadata or {}
        
        # 如果有HTML，使用正文提取器
        if fetch_result.html:
            try:
                extract_result = self.content_extractor.extract(
                    fetch_result.html,
                    fetch_result.url
                )
                
                if extract_result.success:
                    # 使用提取的内容
                    if extract_result.content:
                        content = extract_result.content
                    if extract_result.title and not title:
                        title = extract_result.title
                    
                    # 合并元数据
                    if extract_result.author:
                        metadata['author'] = extract_result.author
                    if extract_result.date:
                        metadata['date'] = extract_result.date
                    if extract_result.language:
                        metadata['language'] = extract_result.language
                    
                    metadata['extractor'] = extract_result.extractor_used
                    metadata['extraction_quality'] = extract_result.quality_score
                
            except Exception as e:
                logger.warning(f"Content extraction failed: {e}")
        
        # 提取meta信息（补充）
        if fetch_result.html:
            try:
                meta_data = self.metadata_extractor.extract(
                    fetch_result.html,
                    fetch_result.url
                )
                
                # 合并metadata（不覆盖已有的）
                for key, value in meta_data.items():
                    if key not in metadata:
                        metadata[key] = value
                
            except Exception as e:
                logger.warning(f"Metadata extraction failed: {e}")
        
        return title, content, metadata
    
    def _calculate_final_quality(self, fetch_result: FetchResult, content: str) -> float:
        """计算最终质量分数"""
        score = fetch_result.quality_score
        
        # 内容长度加成
        if content:
            content_len = len(content)
            if content_len > 3000:
                score += 0.2
            elif content_len > 1500:
                score += 0.1
            elif content_len > 800:
                score += 0.05
        
        return min(score, 1.0)
    
    def _should_generate_pdf(
        self,
        quality_score: float,
        content: str,
        explicit_request: Optional[bool]
    ) -> bool:
        """判断是否生成PDF"""
        if explicit_request is not None:
            return explicit_request
        
        if not self.pdf_enabled:
            return False
        
        if quality_score < self.min_score_for_pdf:
            return False
        
        if not content or len(content) < 500:
            return False
        
        return True
    
    def _should_generate_summary(
        self,
        quality_score: float,
        content: str,
        explicit_request: Optional[bool]
    ) -> bool:
        """判断是否生成AI摘要"""
        if explicit_request is not None:
            return explicit_request
        
        if quality_score < self.min_score_for_ai:
            return False
        
        # 从AI配置读取最小内容长度阈值
        global_config = get_config()
        min_length = global_config.get('ai.min_content_length_for_summary', 150)
        if not content or len(content) < min_length:
            return False
        
        return True
    
    async def _generate_pdf(
        self,
        fetch_result: FetchResult,
        title: str,
        url: str,
        metadata: Dict[str, Any]
    ) -> Optional[bytes]:
        """生成PDF"""
        try:
            logger.info("Generating PDF...")
            
            # 优先使用HTML生成（保留格式）
            if fetch_result.html:
                pdf_bytes = self.pdf_generator.generate_from_html(
                    fetch_result.html,
                    title=title,
                    url=url,
                    author=metadata.get('author')
                )
            # 否则使用纯文本
            elif fetch_result.text:
                pdf_bytes = self.pdf_generator.generate_from_content(
                    fetch_result.text,
                    title=title,
                    url=url,
                    author=metadata.get('author'),
                    date=metadata.get('date')
                )
            else:
                logger.warning("No content for PDF generation")
                return None
            
            if pdf_bytes:
                logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
            else:
                logger.warning("PDF generation returned None")
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            return None
    
    async def _generate_summary(self, content: str, url: str) -> Optional[str]:
        """生成AI摘要（复用现有summarizer）"""
        try:
            from ...ai.summarizer import AISummarizer
            from ...utils.config import get_config
            
            logger.info("Generating AI summary for web archive...")
            
            # 从配置获取语言（不依赖language_context，因为可能没有Update对象）
            config = get_config()
            language = config.get('bot.language', 'zh-CN')
            
            # 使用现有的AI summarizer（需要传入ai配置）
            ai_config = config.get('ai', {})
            summarizer = AISummarizer(ai_config)
            
            # 直接使用内容，不需要额外提示词（summarizer会自动处理）
            # 限制长度避免token溢出
            content_for_summary = content[:5000] if len(content) > 5000 else content
            
            summary = await summarizer.summarize_content(
                content=content_for_summary,
                language=language,
                context={'content_type': 'web_archive', 'url': url}
            )
            
            if summary:
                logger.info(f"AI summary generated: {len(summary)} chars, language={language}")
            else:
                logger.warning("AI summary returned None")
            
            return summary
            
        except Exception as e:
            logger.error(f"AI summary generation error: {e}", exc_info=True)
            return None
