"""
AI Session Manager

Lightweight session storage for single-user AI interactive mode.
Stores sessions as individual JSON files under `data/temp/ai_sessions/` with TTL.

API:
  create_session(session_id) -> creates empty session dict with created_at
  get_session(session_id) -> returns session dict or None
  update_session(session_id, data) -> merge and persist
  clear_session(session_id) -> remove session
  cleanup_expired() -> remove expired sessions

Session data is a plain dict. This module is intentionally simple and
fits single-user requirements (no multi-user isolation needed).
"""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any


SESSIONS_DIR = Path("data/temp/ai_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_path(session_id: str) -> Path:
    safe = session_id.replace("/", "_")
    return SESSIONS_DIR / f"{safe}.json"


class AISessionManager:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl = int(ttl_seconds)

    def create_session(self, session_id: str) -> Dict[str, Any]:
        now = int(time.time())
        data = {"created_at": now, "last_active": now, "context": {}}
        p = _session_path(session_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        p = _session_path(session_id)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # check TTL based on last_active
            now = int(time.time())
            last_active = int(data.get("last_active", data.get("created_at", now)))
            if now - last_active > self.ttl:
                try:
                    p.unlink()
                except Exception:
                    pass
                return None
            return data
        except Exception:
            return None

    def update_session(self, session_id: str, delta: Dict[str, Any]) -> Dict[str, Any]:
        data = self.get_session(session_id) or self.create_session(session_id)
        # merge delta into context
        ctx = data.get("context", {})
        ctx.update(delta)
        data["context"] = ctx
        # 更新最后活跃时间，延长会话有效期
        data["last_active"] = int(time.time())
        p = _session_path(session_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data

    def clear_session(self, session_id: str) -> bool:
        """清除会话（包括pending数据清理）"""
        p = _session_path(session_id)
        try:
            if p.exists():
                p.unlink()
            return True
        except Exception:
            return False

    def cleanup_expired(self):
        """清理过期会话（包括pending数据）"""
        now = int(time.time())
        cleaned = 0
        for p in SESSIONS_DIR.glob("*.json"):
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                last_active = int(data.get("last_active", data.get("created_at", now)))
                if now - last_active > self.ttl:
                    p.unlink()
                    cleaned += 1
            except Exception:
                try:
                    p.unlink()
                    cleaned += 1
                except Exception:
                    pass
        if cleaned > 0:
            logger.info(f"Cleaned {cleaned} expired sessions")


_default_session_manager: Optional[AISessionManager] = None


def get_session_manager(ttl_seconds: int = 600) -> AISessionManager:
    global _default_session_manager
    if not _default_session_manager:
        _default_session_manager = AISessionManager(ttl_seconds=ttl_seconds)
    return _default_session_manager
