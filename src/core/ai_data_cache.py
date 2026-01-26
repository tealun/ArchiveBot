"""
AI Data Cache Manager

轻量级缓存管理，优化内存消耗
采用：
1. 短TTL（减少过期数据驻留）
2. LRU策略（限制缓存容量）
3. 仅缓存结果而非完整数据
"""
import logging
import time
from typing import Dict, Any, Optional, List
from threading import Lock
from collections import OrderedDict

logger = logging.getLogger(__name__)


class LRUCache:
    """简单的LRU缓存实现"""
    
    def __init__(self, capacity: int = 10):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.cache:
                return None
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                # 更新并移到末尾
                self.cache.move_to_end(key)
            self.cache[key] = value
            # 超过容量，删除最旧的
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
    
    def remove(self, key: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        with self.lock:
            return len(self.cache)


class AIDataCache:
    """AI对话数据缓存管理器（优化版）"""
    
    def __init__(self, db_storage, config=None, max_cache_size: int = 10):
        self.db_storage = db_storage
        self.config = config
        # 使用LRU缓存替代普通字典，限制内存使用
        self._cache = LRUCache(capacity=max_cache_size)
        self._timestamp_cache = {}  # 仅存储时间戳，轻量级
        self._lock = Lock()
        
        # 缩短TTL，减少过期数据驻留时间
        self.ttl = {
            'statistics': 180,      # 3分钟（从5分钟缩短）
            'recent_samples': 120,  # 2分钟（从5分钟缩短）
            'tag_analysis': 180,    # 3分钟（从5分钟缩短）
        }
        
        logger.info(f"AIDataCache initialized with LRU (max_size={max_cache_size}, shorter TTL)")
    
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
        if not keys:
            self._cache.clear()
            with self._lock:
                self._timestamp_cache.clear()
            logger.debug("All cache cleared")
        else:
            for key in keys:
                self._cache.remove(key)
                with self._lock:
                    if key in self._timestamp_cache:
                        del self._timestamp_cache[key]
                logger.debug(f"Cache invalidated: {key}")
    
    def invalidate_all(self):
        """清空所有缓存"""
        self.invalidate()
    
    def _get_or_compute(self, key: str, compute_func):
        """通用缓存获取或计算逻辑（优化版）"""
        # 检查缓存和时间戳
        cached_data = self._cache.get(key)
        
        with self._lock:
            cached_time = self._timestamp_cache.get(key, 0)
        
        # 缓存命中且未过期
        if cached_data is not None and time.time() - cached_time < self.ttl.get(key, 180):
            logger.debug(f"Cache hit: {key}")
            return cached_data
        
        if cached_data is not None:
            logger.debug(f"Cache expired: {key}")
        
        # 缓存未命中或已过期，重新计算
        try:
            data = compute_func()
            
            # 存入LRU缓存
            self._cache.put(key, data)
            with self._lock:
                self._timestamp_cache[key] = time.time()
            
            logger.debug(f"Cache updated: {key}, size={self._cache.size()}")
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
        
        stats = {
            'total': total,
            'tags': tag_count,
            'recent_week': recent
        }
        
        logger.debug(f"📊 Statistics computed: {stats}")
        return stats
    
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
        
        logger.debug(f"📝 Recent samples: Retrieved {len(result)} items")
        
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
        info = {
            'cache_size': self._cache.size(),
            'max_capacity': self._cache.capacity,
            'items': {}
        }
        
        with self._lock:
            for key, timestamp in self._timestamp_cache.items():
                age = time.time() - timestamp
                info['items'][key] = {
                    'age_seconds': int(age),
                    'ttl': self.ttl.get(key, 180),
                    'expired': age >= self.ttl.get(key, 180)
                }
        
        return info
