"""
PDF generation from HTML content
使用WeasyPrint从HTML生成PDF
"""

import logging
import io
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFGenerator:
    """PDF生成器"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.page_size = self.config.get('page_size', 'A4')
        self.include_images = self.config.get('include_images', True)
    
    def generate_from_html(
        self, 
        html: str, 
        title: str = None,
        url: str = None,
        author: str = None
    ) -> Optional[bytes]:
        """
        从HTML生成PDF
        
        Args:
            html: HTML内容
            title: 文档标题
            url: 原始URL
            author: 作者
            
        Returns:
            PDF字节数据或None
        """
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            
            # 构建完整的HTML文档
            full_html = self._build_html_document(html, title, url, author)
            
            # 自定义CSS样式
            css = self._get_pdf_css()
            
            # 字体配置
            font_config = FontConfiguration()
            
            # 生成PDF
            logger.info(f"Generating PDF: title='{title}'")
            
            html_obj = HTML(string=full_html, base_url=url or '')
            pdf_bytes = html_obj.write_pdf(
                stylesheets=[CSS(string=css, font_config=font_config)],
                font_config=font_config
            )
            
            logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except ImportError as e:
            logger.warning(f"WeasyPrint not available: {e}")
            logger.info("Falling back to simple PDF generator...")
            return self._generate_simple_pdf(html, title, url, author)
        except Exception as e:
            logger.error(f"WeasyPrint PDF generation failed: {e}")
            logger.info("Falling back to simple PDF generator...")
            return self._generate_simple_pdf(html, title, url, author)
    
    def generate_from_content(
        self,
        content: str,
        title: str = None,
        url: str = None,
        author: str = None,
        date: str = None
    ) -> Optional[bytes]:
        """
        从纯文本内容生成PDF（将文本转为HTML）
        
        Args:
            content: 纯文本内容
            title: 标题
            url: 原始URL
            author: 作者
            date: 发布日期
            
        Returns:
            PDF字节数据或None
        """
        # 转换文本为HTML段落
        paragraphs = content.split('\n\n')
        html_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # 转义HTML特殊字符
                para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                # 保留换行
                para = para.replace('\n', '<br>')
                html_paragraphs.append(f'<p>{para}</p>')
        
        html_content = '\n'.join(html_paragraphs)
        
        return self.generate_from_html(html_content, title, url, author)
    
    def _build_html_document(
        self,
        content: str,
        title: str = None,
        url: str = None,
        author: str = None
    ) -> str:
        """构建完整的HTML文档"""
        
        title_escaped = (title or 'Untitled').replace('<', '&lt;').replace('>', '&gt;')
        
        # 构建头部信息
        header_parts = []
        if title:
            header_parts.append(f'<h1 class="doc-title">{title_escaped}</h1>')
        
        metadata_parts = []
        if author:
            metadata_parts.append(f'<span class="author">作者: {author}</span>')
        if url:
            url_display = url if len(url) <= 80 else url[:77] + '...'
            metadata_parts.append(f'<span class="url">来源: <a href="{url}">{url_display}</a></span>')
        
        metadata_parts.append(f'<span class="date">归档时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>')
        
        metadata_html = ' | '.join(metadata_parts) if metadata_parts else ''
        
        # 组装完整文档
        html_doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_escaped}</title>
</head>
<body>
    <div class="document-header">
        {"".join(header_parts)}
        {f'<div class="metadata">{metadata_html}</div>' if metadata_html else ''}
    </div>
    <div class="content">
        {content}
    </div>
    <div class="document-footer">
        <p class="footer-text">由 ArchiveBot 生成</p>
    </div>
</body>
</html>'''
        
        return html_doc
    
    def _get_pdf_css(self) -> str:
        """获取PDF样式"""
        return '''
@page {
    size: A4;
    margin: 2cm;
    @bottom-right {
        content: counter(page) " / " counter(pages);
        font-size: 10pt;
        color: #666;
    }
}

body {
    font-family: "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
}

.document-header {
    border-bottom: 2px solid #4A90E2;
    padding-bottom: 15px;
    margin-bottom: 20px;
}

.doc-title {
    font-size: 20pt;
    font-weight: bold;
    color: #2C3E50;
    margin: 0 0 10px 0;
}

.metadata {
    font-size: 9pt;
    color: #666;
    line-height: 1.4;
}

.metadata span {
    display: inline-block;
    margin-right: 15px;
}

.metadata a {
    color: #4A90E2;
    text-decoration: none;
}

.content {
    margin-top: 20px;
}

.content h1 {
    font-size: 16pt;
    color: #2C3E50;
    margin-top: 20px;
    margin-bottom: 10px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 5px;
}

.content h2 {
    font-size: 14pt;
    color: #34495E;
    margin-top: 15px;
    margin-bottom: 8px;
}

.content h3 {
    font-size: 12pt;
    color: #34495E;
    margin-top: 12px;
    margin-bottom: 6px;
}

.content p {
    margin: 8px 0;
    text-align: justify;
}

.content a {
    color: #4A90E2;
    text-decoration: none;
}

.content img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 15px auto;
}

.content code {
    background-color: #f5f5f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "Courier New", monospace;
    font-size: 10pt;
}

.content pre {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
    font-family: "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.4;
}

.content blockquote {
    border-left: 4px solid #4A90E2;
    padding-left: 15px;
    margin-left: 0;
    color: #666;
    font-style: italic;
}

.content ul, .content ol {
    margin: 10px 0;
    padding-left: 30px;
}

.content li {
    margin: 5px 0;
}

.content table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}

.content th, .content td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}

.content th {
    background-color: #f5f5f5;
    font-weight: bold;
}

.document-footer {
    margin-top: 40px;
    padding-top: 15px;
    border-top: 1px solid #ddd;
}

.footer-text {
    text-align: center;
    font-size: 9pt;
    color: #999;
}
'''
    
    def _generate_simple_pdf(
        self,
        html: str,
        title: str = None,
        url: str = None,
        author: str = None
    ) -> Optional[bytes]:
        """
        简单的PDF生成（不依赖GTK，使用reportlab）
        
        Args:
            html: HTML内容
            title: 文档标题
            url: 原始URL
            author: 作者
            
        Returns:
            PDF字节数据或None
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
            from bs4 import BeautifulSoup
            import io
            
            logger.info("Using simple PDF generator (reportlab)")
            
            # 注册中文字体（尝试多个Windows常见字体）
            try:
                import os
                # 尝试注册微软雅黑
                font_paths = [
                    'C:/Windows/Fonts/msyh.ttc',  # 微软雅黑
                    'C:/Windows/Fonts/simhei.ttf',  # 黑体
                    'C:/Windows/Fonts/simsun.ttc',  # 宋体
                ]
                
                font_registered = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            logger.info(f"Registered Chinese font: {font_path}")
                            break
                        except Exception as e:
                            logger.debug(f"Failed to register {font_path}: {e}")
                            continue
                
                if not font_registered:
                    logger.warning("No Chinese font registered, using default (may show squares for Chinese)")
            except Exception as e:
                logger.error(f"Error registering Chinese font: {e}")
            
            # 创建PDF buffer
            buffer = io.BytesIO()
            
            # 创建PDF文档
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )
            
            # 样式（使用注册的中文字体）
            styles = getSampleStyleSheet()
            
            # 确定字体名称
            font_name = 'ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=font_name,
                fontSize=18,
                textColor='#333333',
                spaceAfter=12,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=font_name,
                fontSize=14,
                textColor='#555555',
                spaceAfter=10,
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['BodyText'],
                fontName=font_name,
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
            )
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=8,
                textColor='#999999',
                alignment=TA_CENTER
            )
            
            # 构建内容
            story = []
            
            # 标题
            if title:
                story.append(Paragraph(title, title_style))
                story.append(Spacer(1, 0.2*inch))
            
            # 元信息
            if url:
                story.append(Paragraph(f"<b>来源:</b> {url}", body_style))
            if author:
                story.append(Paragraph(f"<b>作者:</b> {author}", body_style))
            
            story.append(Paragraph(f"<b>生成时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
            story.append(Spacer(1, 0.3*inch))
            
            # 从HTML提取纯文本
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除不需要的标签
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # 处理段落
            for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = element.get_text(strip=True)
                if not text:
                    continue
                
                # 转义特殊字符
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                # 根据标签类型选择样式
                if element.name in ['h1', 'h2', 'h3']:
                    story.append(Paragraph(text, heading_style))
                else:
                    story.append(Paragraph(text, body_style))
            
            # 页脚
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(f"由 ArchiveBot 生成", footer_style))
            
            # 生成PDF
            doc.build(story)
            
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Simple PDF generated: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except ImportError as e:
            logger.error(f"reportlab not available: {e}")
            logger.info("Install with: pip install reportlab")
            return None
        except Exception as e:
            logger.error(f"Simple PDF generation failed: {e}", exc_info=True)
            return None

