"""
AI Data Cache Manager

轻量级内存缓存，用于AI对话的数据收集
采用事件驱动更新，避免重复查询
"""
import logging
import time
from typing import Dict, Any, Optional, List
from threading import Lock

logger = logging.getLogger(__name__)


class AIDataCache:
    """AI对话数据缓存管理器"""
    
    def __init__(self, db_storage, config=None):
        self.db_storage = db_storage
        self.config = config
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        # 缓存TTL配置
        self.ttl = {
            'statistics': 300,      # 5分钟（轻量数据，可长缓存）
            'recent_samples': 300,  # 5分钟
            'tag_analysis': 300,    # 5分钟
        }
        
        logger.info("AIDataCache initialized")
    
    def _get_excluded_channel_ids(self) -> List[int]:
        """获取需要排除的频道ID列表"""
        if not self.config:
            return []
        excluded = self.config.get('ai.exclude_from_context.channel_ids', [])
        return excluded if excluded else []
    
    def _get_excluded_tags(self) -> List[str]:
        """获取需要排除的标签列表"""
        if not self.config:
            return []
        excluded = self.config.get('ai.exclude_from_context.tags', [])
        return excluded if excluded else []
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计数据（总数、标签数、最近7天）"""
        return self._get_or_compute('statistics', self._compute_statistics)
    
    def get_recent_samples(self, limit: int = 10) -> list:
        """获取最近归档示例"""
        return self._get_or_compute('recent_samples', 
                                     lambda: self._compute_recent_samples(limit))
    
    def get_tag_analysis(self, limit: int = 15) -> list:
        """获取标签分析（TOP N标签及计数）"""
        return self._get_or_compute('tag_analysis',
                                     lambda: self._compute_tag_analysis(limit))
    
    def invalidate(self, *keys):
        """
        失效指定缓存
        
        Args:
            *keys: 缓存键名，不传则清空全部
        """
        with self._lock:
            if not keys:
                self._cache.clear()
                logger.debug("All cache cleared")
            else:
                for key in keys:
                    if key in self._cache:
                        del self._cache[key]
                        logger.debug(f"Cache invalidated: {key}")
    
    def invalidate_all(self):
        """清空所有缓存"""
        self.invalidate()
    
    def _get_or_compute(self, key: str, compute_func):
        """通用缓存获取或计算逻辑"""
        with self._lock:
            # 检查缓存
            if key in self._cache:
                cached = self._cache[key]
                if time.time() - cached['timestamp'] < self.ttl.get(key, 300):
                    logger.debug(f"Cache hit: {key}")
                    return cached['data']
                else:
                    logger.debug(f"Cache expired: {key}")
            
            # 缓存未命中或已过期，重新计算
            try:
                data = compute_func()
                self._cache[key] = {
                    'data': data,
                    'timestamp': time.time()
                }
                logger.debug(f"Cache computed: {key}")
                return data
            except Exception as e:
                logger.error(f"Cache computation error for {key}: {e}", exc_info=True)
                return self._get_fallback_data(key)
    
    def _compute_statistics(self) -> Dict[str, int]:
        """计算统计数据"""
        total = self.db_storage.db.execute(
            "SELECT COUNT(*) FROM archives WHERE deleted = 0"
        ).fetchone()[0]
        
        tag_count = self.db_storage.db.execute("""
            SELECT COUNT(DISTINCT tag_id) FROM archive_tags 
            WHERE archive_id IN (SELECT id FROM archives WHERE deleted = 0)
        """).fetchone()[0]
        
        week_ago = int(time.time()) - 7 * 24 * 3600
        recent = self.db_storage.db.execute(
            "SELECT COUNT(*) FROM archives WHERE deleted = 0 AND created_at > ?",
            (week_ago,)
        ).fetchone()[0]
        
        return {
            'total': total,
            'tags': tag_count,
            'recent_week': recent
        }
    
    def _compute_recent_samples(self, limit: int) -> list:
        """计算最近归档示例（排除指定频道和标签的内容）"""
        excluded_channel_ids = self._get_excluded_channel_ids()
        excluded_tags = self._get_excluded_tags()
        
        # 构建查询条件
        where_conditions = ["deleted = 0"]
        params = []
        
        # 排除指定频道的内容
        if excluded_channel_ids:
            # storage_path 格式为 "telegram:channel_id:message_id"
            channel_conditions = []
            for channel_id in excluded_channel_ids:
                channel_conditions.append("storage_path NOT LIKE ?")
                params.append(f"telegram:{channel_id}:%")
            where_conditions.append(f"({' AND '.join(channel_conditions)})")
        
        # 排除包含指定标签的归档
        if excluded_tags:
            # 获取排除标签的ID
            placeholders = ','.join(['?'] * len(excluded_tags))
            excluded_tag_ids_query = f"""
                SELECT id FROM tags WHERE tag_name IN ({placeholders})
            """
            excluded_tag_ids = [
                row[0] for row in self.db_storage.db.execute(
                    excluded_tag_ids_query, excluded_tags
                ).fetchall()
            ]
            
            if excluded_tag_ids:
                # 排除包含这些标签的归档
                placeholders = ','.join(['?'] * len(excluded_tag_ids))
                where_conditions.append(f"""
                    id NOT IN (
                        SELECT archive_id FROM archive_tags 
                        WHERE tag_id IN ({placeholders})
                    )
                """)
                params.extend(excluded_tag_ids)
        
        where_clause = " AND ".join(where_conditions)
        params.append(limit)
        
        query = f"""
            SELECT id, title, content, created_at FROM archives 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT ?
        """
        
        samples = self.db_storage.db.execute(query, tuple(params)).fetchall()
        
        result = [
            {
                'id': aid,
                'title': (title or content or '无标题')[:50],
                'created_at': created_at
            }
            for aid, title, content, created_at in samples
        ]
        
        if excluded_channel_ids or excluded_tags:
            logger.debug(f"Recent samples filtered: excluded {len(excluded_channel_ids)} channels, {len(excluded_tags)} tags")
        
        return result
    
    def _compute_tag_analysis(self, limit: int) -> list:
        """计算标签分析（排除指定标签）"""
        excluded_tags = self._get_excluded_tags()
        excluded_channel_ids = self._get_excluded_channel_ids()
        
        # 构建查询条件
        where_conditions = ["a.deleted = 0"]
        params = []
        
        # 排除指定标签
        if excluded_tags:
            placeholders = ','.join(['?'] * len(excluded_tags))
            where_conditions.append(f"t.tag_name NOT IN ({placeholders})")
            params.extend(excluded_tags)
        
        # 排除来自指定频道的归档
        if excluded_channel_ids:
            channel_conditions = []
            for channel_id in excluded_channel_ids:
                channel_conditions.append("a.storage_path NOT LIKE ?")
                params.append(f"telegram:{channel_id}:%")
            where_conditions.append(f"({' AND '.join(channel_conditions)})")
        
        where_clause = " AND ".join(where_conditions)
        params.append(limit)
        
        query = f"""
            SELECT t.tag_name, COUNT(*) as cnt
            FROM tags t
            JOIN archive_tags at ON t.id = at.tag_id
            JOIN archives a ON at.archive_id = a.id
            WHERE {where_clause}
            GROUP BY t.id
            ORDER BY cnt DESC
            LIMIT ?
        """
        
        tag_stats = self.db_storage.db.execute(query, tuple(params)).fetchall()
        
        result = [{'tag': tag, 'count': cnt} for tag, cnt in tag_stats]
        
        if excluded_tags or excluded_channel_ids:
            logger.debug(f"Tag analysis filtered: excluded {len(excluded_tags)} tags, {len(excluded_channel_ids)} channels")
        
        return result
    
    def _get_fallback_data(self, key: str):
        """获取失败时的回退数据"""
        fallbacks = {
            'statistics': {'total': 0, 'tags': 0, 'recent_week': 0},
            'recent_samples': [],
            'tag_analysis': []
        }
        return fallbacks.get(key, {})
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存状态信息（调试用）"""
        with self._lock:
            info = {}
            for key, value in self._cache.items():
                age = time.time() - value['timestamp']
                info[key] = {
                    'age_seconds': int(age),
                    'ttl': self.ttl.get(key, 300),
                    'expired': age >= self.ttl.get(key, 300)
                }
            return info
