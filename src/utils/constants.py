"""
Constants and configuration values
"""

# Storage thresholds (in bytes)
# Telegram file_id转发支持最大2GB文件，无需区分大小
TELEGRAM_MAX_SIZE = 2000 * 1024 * 1024  # 2 GB - Telegram限制

# Search limits
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 100
MAX_TAGS_DISPLAY = 50

# Database
DB_TIMEOUT = 30.0
DB_MAX_RETRIES = 3

# Content types
CONTENT_TYPE_TEXT = 'text'
CONTENT_TYPE_IMAGE = 'image'
CONTENT_TYPE_VIDEO = 'video'
CONTENT_TYPE_DOCUMENT = 'document'
CONTENT_TYPE_EBOOK = 'ebook'
CONTENT_TYPE_LINK = 'link'
CONTENT_TYPE_AUDIO = 'audio'
CONTENT_TYPE_VOICE = 'voice'
CONTENT_TYPE_ANIMATION = 'animation'
CONTENT_TYPE_STICKER = 'sticker'
CONTENT_TYPE_CONTACT = 'contact'
CONTENT_TYPE_LOCATION = 'location'

# Storage types
STORAGE_DATABASE = 'database'  # 文本、链接等元数据
STORAGE_TELEGRAM = 'telegram'  # 所有媒体文件（<2GB）
STORAGE_REFERENCE = 'reference'  # 超过2GB或无法存储的文件

# Tag types
TAG_TYPE_AUTO = 'auto'
TAG_TYPE_MANUAL = 'manual'
TAG_TYPE_AI = 'ai'

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'zh-CN': '简体中文',
    'zh-TW': '繁體中文',
    'ja': '日本語',
    'ko': '한국어',
    'es': 'Español'
}

# Ebook file extensions
EBOOK_EXTENSIONS = [
    '.epub', '.mobi', '.azw', '.azw3',
    '.fb2', '.djvu', '.cbz', '.cbr'
]

# File cleanup
TEMP_FILE_MAX_AGE_HOURS = 24
