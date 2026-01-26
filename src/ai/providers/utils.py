"""
AI utility functions
"""

import re

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
