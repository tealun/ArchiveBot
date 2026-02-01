"""
Telegram preview extraction strategy
从Telegram消息的链接预览中提取信息
"""

import logging
from typing import Dict, Any, Optional
from .base import FetchStrategy, FetchResult

logger = logging.getLogger(__name__)


class TelegramStrategy(FetchStrategy):
    """从Telegram链接预览提取信息的策略"""
    
    @property
    def name(self) -> str:
        return 'telegram_preview'
    
    async def fetch(self, url: str, telegram_message=None, **kwargs) -> FetchResult:
        """
        从Telegram消息的链接预览提取信息
        
        Args:
            url: 链接URL
            telegram_message: Telegram Message对象（可选）
            **kwargs: 额外参数
            
        Returns:
            FetchResult对象
        """
        try:
            if not telegram_message:
                logger.debug("No telegram message provided for preview extraction")
                return FetchResult.empty(url, "No telegram message")
            
            # 提取链接预览信息
            preview_data = self._extract_preview_data(telegram_message)
            
            if not preview_data:
                logger.debug("No preview data found in telegram message")
                return FetchResult.empty(url, "No preview data")
            
            title = preview_data.get('title', '')
            description = preview_data.get('description', '')
            image_url = preview_data.get('image_url')
            site_name = preview_data.get('site_name')
            
            # 组合文本内容
            text_parts = []
            if title:
                text_parts.append(title)
            if description:
                text_parts.append(description)
            text = '\n\n'.join(text_parts)
            
            # 计算质量分数（预览信息质量较低）
            quality_score = 0.0
            if title:
                quality_score += 0.2
            if description and len(description) > 100:
                quality_score += 0.3
            elif description:
                quality_score += 0.1
            if image_url:
                quality_score += 0.1
            
            metadata = {
                'source': 'telegram_preview',
                'site_name': site_name,
                'image_url': image_url,
                'has_preview': True
            }
            
            title_preview = (title[:50] + '...') if title and len(title) > 50 else (title or 'Untitled')
            logger.info(f"Telegram preview extracted: title='{title_preview}', quality={quality_score:.2f}")
            
            return FetchResult(
                success=True,
                text=text,
                title=title or "Untitled",
                url=url,
                metadata=metadata,
                strategy_used=self.name,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"Telegram preview extraction error: {e}", exc_info=True)
            return FetchResult.empty(url, str(e))
    
    def _extract_preview_data(self, message) -> Optional[Dict[str, Any]]:
        """
        从Telegram消息中提取链接预览数据
        
        Args:
            message: Telegram Message对象
            
        Returns:
            预览数据字典或None
        """
        try:
            # 检查是否有link_preview_options（新API）
            if hasattr(message, 'link_preview_options') and message.link_preview_options:
                preview = message.link_preview_options
                
                data = {
                    'title': getattr(preview, 'title', None),
                    'description': getattr(preview, 'description', None),
                    'site_name': getattr(preview, 'site_name', None),
                    'image_url': None
                }
                
                # 提取图片URL（如果有）
                if hasattr(preview, 'image') and preview.image:
                    # image可能是PhotoSize对象
                    data['image_url'] = getattr(preview.image, 'file_id', None)
                
                return data
            
            # 检查旧的web_page属性
            if hasattr(message, 'web_page') and message.web_page:
                web_page = message.web_page
                
                data = {
                    'title': getattr(web_page, 'title', None),
                    'description': getattr(web_page, 'description', None),
                    'site_name': getattr(web_page, 'site_name', None),
                    'image_url': None
                }
                
                # 提取图片
                if hasattr(web_page, 'photo') and web_page.photo:
                    if isinstance(web_page.photo, list) and web_page.photo:
                        data['image_url'] = web_page.photo[-1].file_id
                    else:
                        data['image_url'] = getattr(web_page.photo, 'file_id', None)
                
                return data
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting telegram preview: {e}")
            return None
