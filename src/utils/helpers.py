"""
Helper utility functions
"""

import html
import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
from .config import get_config

logger = logging.getLogger(__name__)


def escape_html(text: str) -> str:
    """
    转义HTML特殊字符，防止HTML注入
    
    统一的HTML转义函数，用于所有需要在Telegram HTML消息中显示的用户输入文本。
    
    Args:
        text: 需要转义的文本
        
    Returns:
        转义后的安全HTML文本
        
    Examples:
        >>> escape_html("A<B>&C")
        'A&lt;B&gt;&amp;C'
        >>> escape_html("正常文本")
        '正常文本'
    """
    if not text:
        return text
    return html.escape(str(text))


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def format_source_header(message, source_info: Optional[dict] = None) -> str:
    """
    格式化消息来源信息头部
    
    Args:
        message: Telegram Message对象
        source_info: 来源信息 {'name': str, 'id': int, 'type': str}
        
    Returns:
        格式化的来源信息字符串
        - 转发消息: "来源 <a href='链接'>频道名</a> | 日期 2026-02-01 10:30\n--------------------"
        - 直发消息: "[存档]  |  日期 2026-02-01 10:30\n--------------------"
    """
    from telegram import MessageOriginChannel, MessageOriginChat
    
    # 获取消息日期
    msg_date = message.date
    date_str = msg_date.strftime("%Y-%m-%d %H:%M")
    
    # 检查是否为转发消息
    if not message.forward_origin or not source_info:
        return f"[存档]  |  日期 {date_str}\n--------------------"
    
    # 获取转发日期（转发消息使用原始消息日期）
    forward_date = message.forward_origin.date
    date_str = forward_date.strftime("%Y-%m-%d %H:%M")
    
    # 获取来源名称
    source_name = source_info.get('name', '未知')
    
    # 格式化来源信息（纯文本，不使用链接）
    return f"来源 {escape_html(source_name)}  |  日期 {date_str}\n--------------------"


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text
    
    Args:
        text: Input text
        
    Returns:
        List of hashtags (without # symbol)
    """
    if not text:
        return []
    
    # Match hashtags (support English, Chinese, numbers, underscore)
    pattern = r'#([\w\u4e00-\u9fa5]+)'
    matches = re.findall(pattern, text)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in matches:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    return unique_tags


def should_create_note(content: str) -> tuple:
    """
    判断内容是否应该创建笔记以及笔记类型
    
    Args:
        content: 输入内容
        
    Returns:
        (is_short_note, note_type)
        - is_short_note: True=直接作为笔记（不归档），False=归档并可能生成AI笔记
        - note_type: 'short'（短文本）| 'long'（长文本）| 'none'（空内容）
    """
    if not content:
        return False, 'none'
    
    # 从配置获取阈值
    config = get_config()
    ai_config = config.get('ai', {})
    text_thresholds = ai_config.get('text_thresholds', {})
    
    # 检测中英文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    english_chars = len(re.findall(r'[a-zA-Z]', content))
    
    # 判断阈值（聊天友好型）
    if chinese_chars > english_chars:
        # 中文为主
        threshold = int(text_thresholds.get('note_chinese', 150))
    else:
        # 英文为主
        threshold = int(text_thresholds.get('note_english', 250))
    
    char_count = len(content)
    
    if char_count < threshold:
        return True, 'short'  # 短文本，直接作为笔记
    else:
        return False, 'long'  # 长文本，需要归档并可能生成AI笔记


def is_url(text: str) -> bool:
    """
    Check if text is a URL
    
    Args:
        text: Input text
        
    Returns:
        True if text is a URL, False otherwise
    """
    if not text:
        return False
    
    try:
        result = urlparse(text.strip())
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text
    
    Args:
        text: Input text
        
    Returns:
        List of URLs
    """
    if not text:
        return []
    
    # URL pattern
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    
    return urls


def remove_forward_signature(text: Optional[str], source_name: Optional[str]) -> Optional[str]:
    """
    移除转发消息中的来源签名行（如“频道名 + URL”尾部签名）
    
    仅在检测到尾部两行分别为来源名称和URL时移除。
    """
    if not text or not source_name:
        return text
    
    lines = [line.rstrip() for line in str(text).splitlines()]
    # 去掉尾部空行
    while lines and not lines[-1].strip():
        lines.pop()
    
    if len(lines) < 2:
        return text
    
    last_line = lines[-1].strip()
    prev_line = lines[-2].strip()
    
    if prev_line == source_name and is_url(last_line):
        lines = lines[:-2]
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines).strip() if lines else None
    
    return text


def extract_user_comment_from_merged(
    merged_caption: Optional[str],
    original_caption: Optional[str]
) -> Optional[str]:
    """
    从合并的caption中提取用户评论部分，避免与原始caption重复
    """
    if not merged_caption:
        return None
    
    merged = str(merged_caption).strip()
    if not merged:
        return None
    
    original = str(original_caption).strip() if original_caption else ''
    if original:
        if merged == original:
            return None
        # 移除原始caption内容
        pattern = re.escape(original)
        cleaned = re.sub(rf"(?:^|\n+)({pattern})(?:\n+|$)", "\n", merged)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned or None
    
    return merged


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


async def smart_sort_messages(messages: List[tuple], ai_summarizer=None) -> List[tuple]:
    """
    智能排序消息列表（处理Telegram自动分片可能导致的乱序）
    
    消息格式：[(timestamp, message_id, text), ...]
    
    策略：
    1. 如果消息数量<=2，按message_id排序（简单场景）
    2. 如果消息数量>2，检查是否存在长度差异>3000的情况
       - 存在：按长度降序排列（长消息在前）
       - 不存在：按message_id排序（时间顺序）
    
    Args:
        messages: 消息列表 [(timestamp, message_id, text), ...]
        ai_summarizer: AI总结器实例（可选，用于未来AI排序优化）
        
    Returns:
        排序后的消息列表
    """
    if not messages:
        return []
    
    if len(messages) <= 2:
        # 简单场景：直接按message_id排序
        return sorted(messages, key=lambda x: x[1])
    
    # 复杂场景：检查长度差异
    lengths = [len(msg[2]) for msg in messages]
    max_len = max(lengths)
    min_len = min(lengths)
    length_diff = max_len - min_len
    
    if length_diff > 3000:
        # 存在显著长度差异，按长度降序（长消息可能是主体）
        sorted_msgs = sorted(messages, key=lambda x: len(x[2]), reverse=True)
        logger.info(f"Sorted by length (diff={length_diff}): {[len(m[2]) for m in sorted_msgs]}")
        return sorted_msgs
    else:
        # 长度相近，按message_id排序（时间顺序）
        sorted_msgs = sorted(messages, key=lambda x: x[1])
        logger.info(f"Smart sorted {len(messages)} messages into {len(sorted_msgs)} groups")
        return sorted_msgs


def split_long_message(text: str, max_length: int = 4096, preserve_newlines: bool = True) -> List[str]:
    """
    智能分割超长消息为多条消息（Telegram单条消息限制4096字符）
    
    Args:
        text: 要分割的文本
        max_length: 单条消息最大长度（默认4096）
        preserve_newlines: 是否在段落边界分割（优先在\\n\\n处分割）
        
    Returns:
        分割后的消息列表
    """
    if not text or len(text) <= max_length:
        return [text] if text else []
    
    parts = []
    remaining = text
    
    while remaining:
        if len(remaining) <= max_length:
            # 剩余内容小于限制，直接添加
            parts.append(remaining)
            break
        
        # 寻找合适的分割点
        split_pos = max_length
        
        if preserve_newlines:
            # 优先在段落边界（\\n\\n）分割
            last_paragraph = remaining[:max_length].rfind('\\n\\n')
            if last_paragraph > max_length * 0.7:  # 如果段落边界在70%之后，使用它
                split_pos = last_paragraph + 2  # +2 包含\\n\\n
            else:
                # 其次在单个换行符处分割
                last_newline = remaining[:max_length].rfind('\\n')
                if last_newline > max_length * 0.7:
                    split_pos = last_newline + 1  # +1 包含\\n
                else:
                    # 最后在空格处分割
                    last_space = remaining[:max_length].rfind(' ')
                    if last_space > max_length * 0.7:
                        split_pos = last_space + 1  # +1 包含空格
        
        # 分割并添加到列表
        parts.append(remaining[:split_pos])
        remaining = remaining[split_pos:]
    
    logger.debug(f"Split long message into {len(parts)} parts (original length: {len(text)})")
    return parts


async def smart_sort_messages(messages: List[tuple], ai_summarizer=None) -> List[tuple]:
    """
    智能排序消息（处理Telegram分片消息可能乱序的问题）
    
    Args:
        messages: [(timestamp, message_id, text), ...] 格式的消息列表
        ai_summarizer: AI summarizer实例（用于分析文本顺序）
        
    Returns:
        排序后的消息列表
    """
    if len(messages) <= 1:
        return messages
    
    # 检测时间窗口（1秒内）同时到达的消息组
    TIME_WINDOW = 1.0  # 秒
    groups = []
    current_group = [messages[0]]
    
    for i in range(1, len(messages)):
        time_diff = messages[i][0] - current_group[-1][0]  # timestamp差异
        if time_diff <= TIME_WINDOW:
            current_group.append(messages[i])
        else:
            groups.append(current_group)
            current_group = [messages[i]]
    
    if current_group:
        groups.append(current_group)
    
    # 对每个组进行智能排序
    sorted_messages = []
    for group in groups:
        if len(group) == 1:
            sorted_messages.extend(group)
        else:
            # 多条消息需要智能排序
            sorted_group = await _smart_sort_group(group, ai_summarizer)
            sorted_messages.extend(sorted_group)
    
    logger.info(f"Smart sorted {len(messages)} messages into {len(groups)} groups")
    return sorted_messages


async def _smart_sort_group(group: List[tuple], ai_summarizer) -> List[tuple]:
    """
    智能排序一组同时到达的消息
    
    策略：
    1. 如果长度差异明显（>500字符），长的在前（接近4096的先发）
    2. 如果长度相近，使用AI分析首尾50字符判断顺序
    
    Args:
        group: 消息组
        ai_summarizer: AI summarizer实例
        
    Returns:
        排序后的消息组
    """
    if len(group) <= 1:
        return group
    
    # 提取文本长度
    lengths = [(i, len(msg[2])) for i, msg in enumerate(group)]
    
    # 检查长度差异
    max_length = max(lengths, key=lambda x: x[1])[1]
    min_length = min(lengths, key=lambda x: x[1])[1]
    length_diff = max_length - min_length
    
    LENGTH_THRESHOLD = 500  # 长度差异阈值
    
    # 情况1：长度差异明显 -> 长的在前（接近4096的）
    if length_diff > LENGTH_THRESHOLD:
        # 按长度降序排列（长的在前）
        sorted_indices = sorted(range(len(group)), key=lambda i: len(group[i][2]), reverse=True)
        sorted_group = [group[i] for i in sorted_indices]
        logger.info(f"Sorted by length (diff={length_diff}): {[len(m[2]) for m in sorted_group]}")
        return sorted_group
    
    # 情况2：长度相近 -> 使用AI分析
    if ai_summarizer and ai_summarizer.is_available() and len(group) == 2:
        try:
            # 提取首尾50字符
            msg1_text = group[0][2]
            msg2_text = group[1][2]
            
            msg1_sample = msg1_text[:50] + "..." + msg1_text[-50:] if len(msg1_text) > 100 else msg1_text
            msg2_sample = msg2_text[:50] + "..." + msg2_text[-50:] if len(msg2_text) > 100 else msg2_text
            
            # 构造AI判断prompt
            prompt = f"""请判断以下两段文本的先后顺序。每段文本显示了开头和结尾部分。

文本A（长度{len(msg1_text)}字符）：
{msg1_sample}

文本B（长度{len(msg2_text)}字符）：
{msg2_sample}

请分析：如果这是一段被分割的长文本，哪种顺序更合理？
1. A在前B在后
2. B在前A在后

请只回答数字1或2，不要解释。"""

            # 调用AI
            result = await ai_summarizer.summarize_content(
                content=prompt,
                content_type='text_order_analysis',
                max_tokens=10,
                language='zh-CN'
            )
            
            if result and result.get('success'):
                answer = result.get('summary', '').strip()
                if '2' in answer or 'B在前' in answer or 'BA' in answer:
                    # B在前A在后，需要交换
                    logger.info(f"AI determined order: B-A (reversed)")
                    return [group[1], group[0]]
                else:
                    # A在前B在后，保持原序
                    logger.info(f"AI determined order: A-B (original)")
                    return group
        except Exception as e:
            logger.warning(f"AI order analysis failed: {e}")
    
    # 降级：按message_id排序（Telegram保证递增）
    sorted_group = sorted(group, key=lambda x: x[1])  # x[1] is message_id
    logger.info(f"Sorted by message_id (fallback)")
    return sorted_group


def format_datetime(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object
    
    Args:
        dt: Datetime object (if None, use current time)
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        dt = datetime.now()
    elif isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    return dt.strftime(format_str)


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse datetime string
    
    Args:
        dt_str: Datetime string
        
    Returns:
        Datetime object or None if parsing failed
    """
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        logger.warning(f"Failed to parse datetime: {dt_str}")
        return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "untitled"
    
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = splitext(sanitized)
        if len(ext) > 10:
            ext = ext[:10]
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def splitext(filename: str) -> tuple:
    """
    Split filename into name and extension
    
    Args:
        filename: Filename
        
    Returns:
        Tuple of (name, extension)
    """
    if '.' in filename:
        parts = filename.rsplit('.', 1)
        return parts[0], '.' + parts[1]
    return filename, ''


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2
    
    Args:
        text: Input text
        
    Returns:
        Escaped text
    """
    if not text:
        return ""
    
    # Characters that need to be escaped in MarkdownV2
    special_chars = r'_*[]()~`>#+-=|{}.!'
    
    escaped = text
    for char in special_chars:
        escaped = escaped.replace(char, '\\' + char)
    
    return escaped


def validate_telegram_id(telegram_id: int) -> bool:
    """
    Validate Telegram user/chat ID
    
    Args:
        telegram_id: Telegram ID
        
    Returns:
        True if valid, False otherwise
    """
    # Telegram IDs are positive integers for users
    # Negative integers for groups/channels
    # Must be non-zero
    return telegram_id != 0 and isinstance(telegram_id, int)


def get_content_type_emoji(content_type: str) -> str:
    """
    Get emoji for content type
    
    Args:
        content_type: Content type
        
    Returns:
        Emoji string
    """
    emoji_map = {
        'text': '📝',
        'image': '🖼️',
        'video': '🎬',
        'document': '📄',
        'link': '🔗',
        'audio': '🎵',
        'voice': '🎤',
        'sticker': '🎨',
        'animation': '🎞️',
        'contact': '👤',
        'location': '📍',
    }
    
    return emoji_map.get(content_type, '📦')


async def send_or_update_reply(update, context, text, command_name, **kwargs):
    """
    Send a reply message or update existing one if found
    Delete old command reply and send new one to keep chat clean
    
    Args:
        update: Telegram update
        context: Bot context
        text: Message text
        command_name: Command name (e.g., 'backup', 'stats')
        **kwargs: Additional arguments for send_message/reply_text
        
    Returns:
        Sent message object
    """
    from telegram.error import BadRequest
    
    # Get user_id and chat_id
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Use bot_data for persistence across sessions, keyed by user_id and command
    reply_key = f'last_reply_{user_id}_{command_name}'
    
    # Try to delete old reply if exists
    old_data = context.bot_data.get(reply_key)
    if old_data and isinstance(old_data, dict):
        old_message_id = old_data.get('message_id')
        old_chat_id = old_data.get('chat_id')
        
        if old_message_id and old_chat_id:
            try:
                await context.bot.delete_message(
                    chat_id=old_chat_id,
                    message_id=old_message_id
                )
                logger.info(f"🗑️ Deleted old reply for /{command_name} (msg_id: {old_message_id})")
            except BadRequest as e:
                # Message might be already deleted or too old
                logger.debug(f"Could not delete old reply for /{command_name}: {e}")
            except Exception as e:
                logger.warning(f"Error deleting old reply for /{command_name}: {e}")
    
    # Send new reply
    if hasattr(update, 'message') and update.message:
        sent_message = await update.message.reply_text(text, **kwargs)
    else:
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            **kwargs
        )
    
    # Store new message_id and chat_id in bot_data for persistence
    context.bot_data[reply_key] = {
        'message_id': sent_message.message_id,
        'chat_id': chat_id,
        'command': command_name,
        'timestamp': sent_message.date.timestamp() if sent_message.date else None
    }
    
    logger.info(f"📝 Stored reply for /{command_name} (msg_id: {sent_message.message_id})")
    
    return sent_message
