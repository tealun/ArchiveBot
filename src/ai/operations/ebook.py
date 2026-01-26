"""
E-book detection operations
"""
import logging

logger = logging.getLogger(__name__)


async def is_ebook_operation(
    provider,
    file_name: str,
    language: str = 'zh-CN'
) -> bool:
    """
    判断文件是否为电子书
    """
    if not provider or not hasattr(provider, 'client'):
        return False
    
    try:
        # 根据语言构建prompt
        if language.startswith('zh'):
            if language in ['zh-TW', 'zh-HK', 'zh-MO']:
                prompt = "請判斷以下檔案名稱是否為電子書\n"
                prompt += "包括書籍雜誌期刊畫報漫畫等\n只需回答是或否\n\n"
                prompt += f"檔案名稱{file_name}\n\n這是電子書嗎"
            else:
                prompt = "请判断以下文件名是否为电子书\n"
                prompt += "包括书籍杂志期刊画报漫画等\n只需回答是或否\n\n"
                prompt += f"文件名{file_name}\n\n这是电子书吗"
        else:
            prompt = "Please determine if the following file name is an eBook\n"
            prompt += "including books magazines journals pictorials comics etc\n"
            prompt += "Just answer Yes or No\n\n"
            prompt += f"File name {file_name}\n\nIs this an eBook"
        
        r = await provider.client.post(
            provider.api_url,
            json={
                "model": provider.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": provider.temperature
            }
        )
        
        response = r.json()['choices'][0]['message']['content'].strip().lower()
        
        # 判断回答
        positive_answers = ['yes', '是', 'true', 'y']
        return any(ans in response for ans in positive_answers)
        
    except Exception as e:
        logger.error(f"AI判断电子书失败: {e}")
        return False
