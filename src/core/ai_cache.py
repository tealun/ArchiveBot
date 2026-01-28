"""
Lightweight AI response cache.

Provides a simple sqlite-backed cache keyed by content hash to avoid
duplicate calls to external AI providers. TTL-based expiration is supported.

This module is intentionally minimal and configuration-driven. Do not
store secrets here. Path and TTL should come from configuration.
"""
import sqlite3
import json
import hashlib
import time
from typing import Optional, Any
from pathlib import Path


def _ensure_db(path: str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_cache (
            key TEXT PRIMARY KEY,
            result_json TEXT,
            created_at INTEGER
        )
        """
    )
    conn.commit()
    return conn


def content_hash(content: str) -> str:
    h = hashlib.sha256()
    h.update(content.encode('utf-8'))
    return h.hexdigest()


class AICache:
    def __init__(self, db_path: str = "data/ai_cache.db", ttl: int = 604800):
        self.db_path = db_path
        self.ttl = int(ttl)
        self._conn = _ensure_db(self.db_path)

    def get(self, key: str) -> Optional[Any]:
        cur = self._conn.cursor()
        cur.execute("SELECT result_json, created_at FROM ai_cache WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        result_json, created_at = row
        if int(time.time()) - int(created_at) > self.ttl:
            # expired
            try:
                cur.execute("DELETE FROM ai_cache WHERE key = ?", (key,))
                self._conn.commit()
            except Exception:
                pass
            return None
        try:
            return json.loads(result_json)
        except Exception:
            return None

    def set(self, key: str, value: Any):
        cur = self._conn.cursor()
        result_json = json.dumps(value, ensure_ascii=False)
        now = int(time.time())
        cur.execute(
            "INSERT OR REPLACE INTO ai_cache (key, result_json, created_at) VALUES (?, ?, ?)",
            (key, result_json, now),
        )
        self._conn.commit()

    def cleanup(self) -> int:
        """清理过期缓存条目"""
        try:
            cur = self._conn.cursor()
            now = int(time.time())
            cur.execute("DELETE FROM ai_cache WHERE ? - created_at > ?", (now, self.ttl))
            deleted = cur.rowcount
            self._conn.commit()
            if deleted > 0:
                logger.info(f"AI cache cleanup: removed {deleted} expired entries")
            return deleted
        except Exception as e:
            logger.error(f"AI cache cleanup error: {e}")
            return 0
    
    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


# Example usage (for development/testing only)
# Uncomment if needed for debugging
# def example_usage():
#     cache = AICache("data/ai_cache.db", ttl=60)
#     key = content_hash("hello world")
#     cache.set(key, {"summary": "hi"})
#     print(cache.get(key))
#     cache.close()
# 
# 
# if __name__ == "__main__":
#     example_usage()
