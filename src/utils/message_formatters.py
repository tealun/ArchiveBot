"""
Message Formatters - 统一的消息格式化工具

提供系统各功能模块的统一格式化函数，确保命令和AI对话的回复格式一致。
职责：将数据结构格式化为用户可读的文本，不包含业务逻辑。
"""

import logging
from typing import Dict, List, Any, Optional
from .i18n import I18n

logger = logging.getLogger(__name__)


def format_stats_text(stats: Dict[str, Any], language: str = 'zh-CN', db_size: int = 0) -> str:
    """
    格式化统计信息文本
    
    Args:
        stats: 统计数据字典，包含 total_archives, total_tags, total_size, last_archive 等
        language: 语言代码
        db_size: 数据库文件大小（字节）
        
    Returns:
        格式化后的统计文本
    """
    from .helpers import format_file_size
    
    i18n = I18n(language)
    
    total_archives = stats.get('total_archives', 0) or stats.get('total', 0)
    total_tags = stats.get('total_tags', 0) or stats.get('tags', 0)
    total_size = format_file_size(stats.get('total_size', 0))
    db_size_formatted = format_file_size(db_size) if db_size > 0 else None
    last_archive = stats.get('last_archive', 'N/A')
    
    # 构建消息
    if db_size_formatted:
        # 完整版本（包含数据库大小）
        message = i18n.t(
            'stats',
            total_archives=total_archives,
            total_tags=total_tags,
            storage_used=total_size,
            db_size=db_size_formatted,
            last_archive=last_archive
        )
    else:
        # 简化版本（AI对话使用）
        if language == 'en':
            message = f"📊 Statistics:\n"
            message += f"• Archives: {total_archives}\n"
            message += f"• Tags: {total_tags}\n"
            message += f"• Storage: {total_size}"
        elif language == 'zh-TW':
            message = f"📊 統計資訊：\n"
            message += f"• 歸檔數：{total_archives}\n"
            message += f"• 標籤數：{total_tags}\n"
            message += f"• 存儲：{total_size}"
        else:
            message = f"📊 统计信息：\n"
            message += f"• 归档数：{total_archives}\n"
            message += f"• 标签数：{total_tags}\n"
            message += f"• 存储：{total_size}"
    
    return message


def format_search_results_summary(
    results: List[Dict], 
    total_count: int, 
    query: str,
    language: str = 'zh-CN',
    max_items: int = 5
) -> str:
    """
    格式化搜索结果摘要（用于AI对话）
    
    Args:
        results: 搜索结果列表
        total_count: 总结果数
        query: 搜索关键词
        language: 语言代码
        max_items: 最多显示项数
        
    Returns:
        格式化后的搜索结果摘要文本
    """
    if not results:
        if language == 'en':
            return f"🔍 No results found for '{query}'"
        elif language == 'zh-TW':
            return f"🔍 沒有找到關於「{query}」的結果"
        else:
            return f"🔍 没有找到关于「{query}」的结果"
    
    # 构建摘要
    if language == 'en':
        text = f"🔍 Found {total_count} result(s) for '{query}':\n\n"
    elif language == 'zh-TW':
        text = f"🔍 找到 {total_count} 個關於「{query}」的結果：\n\n"
    else:
        text = f"🔍 找到 {total_count} 个关于「{query}」的结果：\n\n"
    
    # 显示前N条
    for i, item in enumerate(results[:max_items], 1):
        title = item.get('title', 'No title' if language == 'en' else '無標題' if language == 'zh-TW' else '无标题')
        # 截断标题
        if len(title) > 50:
            title = title[:50] + '...'
        text += f"{i}. {title}\n"
    
    if total_count > max_items:
        if language == 'en':
            text += f"\n... and {total_count - max_items} more"
        elif language == 'zh-TW':
            text += f"\n...還有 {total_count - max_items} 個"
        else:
            text += f"\n...还有 {total_count - max_items} 个"
    
    return text


def format_tag_analysis_text(
    tags: List[Dict], 
    language: str = 'zh-CN',
    max_tags: int = 10
) -> str:
    """
    格式化标签分析文本
    
    Args:
        tags: 标签列表，每项包含 tag/tag_name 和 count
        language: 语言代码
        max_tags: 最多显示标签数
        
    Returns:
        格式化后的标签分析文本
    """
    if not tags:
        if language == 'en':
            return "No tags available"
        elif language == 'zh-TW':
            return "暫無標籤"
        else:
            return "暂无标签"
    
    # 构建标签列表
    tag_texts = []
    for tag in tags[:max_tags]:
        tag_name = tag.get('tag') or tag.get('tag_name')
        count = tag.get('count', 0)
        tag_texts.append(f"#{tag_name}({count})")
    
    if language == 'en':
        header = f"🏷️ Top {len(tag_texts)} Tags:\n"
    elif language == 'zh-TW':
        header = f"🏷️ 熱門標籤 TOP {len(tag_texts)}：\n"
    else:
        header = f"🏷️ 热门标签 TOP {len(tag_texts)}：\n"
    
    return header + ' '.join(tag_texts)


def format_recent_archives_text(
    archives: List[Dict],
    language: str = 'zh-CN',
    max_items: int = 5
) -> str:
    """
    格式化最近归档列表
    
    Args:
        archives: 归档列表
        language: 语言代码
        max_items: 最多显示条数
        
    Returns:
        格式化后的最近归档文本
    """
    if not archives:
        if language == 'en':
            return "No recent archives"
        elif language == 'zh-TW':
            return "暫無最近歸檔"
        else:
            return "暂无最近归档"
    
    if language == 'en':
        header = f"📚 Recent {len(archives[:max_items])} Archives:\n"
    elif language == 'zh-TW':
        header = f"📚 最近 {len(archives[:max_items])} 條歸檔：\n"
    else:
        header = f"📚 最近 {len(archives[:max_items])} 条归档：\n"
    
    text = header
    for archive in archives[:max_items]:
        title = archive.get('title', '')
        if len(title) > 40:
            title = title[:40] + '...'
        text += f"• {title}\n"
    
    return text


def format_ai_context_summary(
    data_context: Dict[str, Any],
    user_intent: str,
    language: str = 'zh-CN'
) -> str:
    """
    根据用户意图格式化AI上下文数据摘要
    
    Args:
        data_context: AI收集的数据上下文
        user_intent: 用户意图类型
        language: 语言代码
        
    Returns:
        格式化后的数据摘要文本，供AI参考
    """
    parts = []
    
    # 只在需要时显示统计
    show_stats = user_intent in ['specific_search', 'stats_analysis', 'resource_request']
    
    if data_context.get('statistics') and show_stats:
        stats = data_context['statistics']
        parts.append(format_stats_text(stats, language, db_size=0))
    
    if data_context.get('search_results'):
        results = data_context['search_results']
        query = data_context.get('search_query', '')
        parts.append(format_search_results_summary(results, len(results), query, language))
    
    if data_context.get('tag_analysis'):
        tags = data_context['tag_analysis']
        parts.append(format_tag_analysis_text(tags, language))
    
    if data_context.get('sample_archives'):
        archives = data_context['sample_archives']
        parts.append(format_recent_archives_text(archives, language))
    
    if not parts:
        if language == 'en':
            return "No relevant data available"
        elif language == 'zh-TW':
            return "暫無相關數據"
        else:
            return "暂无相关数据"
    
    return '\n\n'.join(parts)
