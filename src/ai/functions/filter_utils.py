"""
Filter Utilities for AI Functions
Provides exclusion filtering for AI interaction mode
"""
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def should_apply_exclusion(context) -> bool:
    """
    检查是否应将排除规则应用于AI互动模式
    
    Args:
        context: Bot context
        
    Returns:
        bool: True表示应用排除规则，False表示不应用
    """
    try:
        from ...utils.config import get_config
        config = get_config()
        return config.get('ai.exclude_from_context.apply_to_ai_interactions', True)
    except Exception as e:
        logger.warning(f"Failed to get exclusion config, defaulting to True: {e}")
        return True  # 默认启用保护隐私


def get_exclusion_filters(context) -> Tuple[List[int], List[str]]:
    """
    获取排除的频道ID和标签列表
    
    Args:
        context: Bot context
        
    Returns:
        Tuple[List[int], List[str]]: (excluded_channel_ids, excluded_tags)
    """
    try:
        from ...utils.config import get_config
        config = get_config()
        
        excluded_channels = config.get('ai.exclude_from_context.channel_ids', [])
        excluded_tags = config.get('ai.exclude_from_context.tags', [])
        
        return (excluded_channels if excluded_channels else [], 
                excluded_tags if excluded_tags else [])
    except Exception as e:
        logger.warning(f"Failed to get exclusion filters: {e}")
        return ([], [])


def build_channel_exclusion_sql(excluded_channel_ids: List[int]) -> Tuple[str, List[str]]:
    """
    构建频道排除的SQL条件和参数
    
    Args:
        excluded_channel_ids: 排除的频道ID列表
        
    Returns:
        Tuple[str, List[str]]: (sql_condition, params)
        例如: ("(storage_path NOT LIKE ? AND storage_path NOT LIKE ?)", ["telegram:123:%", "telegram:456:%"])
    """
    if not excluded_channel_ids:
        return ("", [])
    
    conditions = []
    params = []
    for channel_id in excluded_channel_ids:
        conditions.append("storage_path NOT LIKE ?")
        params.append(f"telegram:{channel_id}:%")
    
    sql = f"({' AND '.join(conditions)})"
    return (sql, params)


def build_tag_exclusion_sql(storage, excluded_tags: List[str]) -> Tuple[str, List[int]]:
    """
    构建标签排除的SQL条件和参数
    
    Args:
        storage: Database storage instance
        excluded_tags: 排除的标签名称列表
        
    Returns:
        Tuple[str, List[int]]: (sql_condition, excluded_tag_ids)
        例如: ("id NOT IN (SELECT archive_id FROM archive_tags WHERE tag_id IN (?,?))", [1, 2])
    """
    if not excluded_tags:
        return ("", [])
    
    # 获取排除标签的ID
    placeholders = ','.join(['?'] * len(excluded_tags))
    excluded_tag_ids_query = f"""
        SELECT id FROM tags WHERE tag_name IN ({placeholders})
    """
    
    try:
        excluded_tag_ids = [
            row[0] for row in storage.db.execute(
                excluded_tag_ids_query, excluded_tags
            ).fetchall()
        ]
        
        if not excluded_tag_ids:
            return ("", [])
        
        placeholders = ','.join(['?'] * len(excluded_tag_ids))
        sql = f"""id NOT IN (
            SELECT archive_id FROM archive_tags 
            WHERE tag_id IN ({placeholders})
        )"""
        
        return (sql, excluded_tag_ids)
    except Exception as e:
        logger.error(f"Error building tag exclusion SQL: {e}", exc_info=True)
        return ("", [])


def apply_exclusion_to_query(
    context,
    storage,
    base_where: str = "deleted = 0",
    base_params: List = None
) -> Tuple[str, List]:
    """
    应用排除规则到SQL查询
    
    Args:
        context: Bot context
        storage: Database storage instance
        base_where: 基础WHERE条件
        base_params: 基础参数列表
        
    Returns:
        Tuple[str, List]: (where_clause, params)
    """
    if base_params is None:
        base_params = []
    
    # 检查是否应用排除规则
    if not should_apply_exclusion(context):
        return (base_where, base_params)
    
    # 获取排除配置
    excluded_channels, excluded_tags = get_exclusion_filters(context)
    
    if not excluded_channels and not excluded_tags:
        return (base_where, base_params)
    
    # 构建WHERE条件
    where_conditions = [base_where] if base_where else []
    params = list(base_params)
    
    # 添加频道排除条件
    if excluded_channels:
        channel_sql, channel_params = build_channel_exclusion_sql(excluded_channels)
        if channel_sql:
            where_conditions.append(channel_sql)
            params.extend(channel_params)
    
    # 添加标签排除条件
    if excluded_tags:
        tag_sql, tag_ids = build_tag_exclusion_sql(storage, excluded_tags)
        if tag_sql:
            where_conditions.append(tag_sql)
            params.extend(tag_ids)
    
    where_clause = " AND ".join(where_conditions)
    
    logger.debug(f"Applied exclusion: {len(excluded_channels)} channels, {len(excluded_tags)} tags")
    
    return (where_clause, params)
