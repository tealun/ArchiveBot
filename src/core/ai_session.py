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
    
    def add_conversation_turn(
        self, 
        session_id: str, 
        user_message: str, 
        bot_response: str,
        intent: str = None,
        result_data: Dict = None,
        max_history: int = 5
    ) -> Dict[str, Any]:
        """
        添加一轮对话到历史记录
        
        Args:
            session_id: 会话ID
            user_message: 用户消息
            bot_response: 机器人回复
            intent: 用户意图类型
            result_data: 本轮结果数据（如搜索结果、资源等）
            max_history: 保留的最大对话轮数（默认5轮）
            
        Returns:
            更新后的会话数据
        """
        data = self.get_session(session_id) or self.create_session(session_id)
        
        # 获取或初始化对话历史
        history = data.get("conversation_history", [])
        
        # 添加新的对话轮次
        turn = {
            "timestamp": int(time.time()),
            "user_message": user_message,
            "bot_response": bot_response,
            "intent": intent
        }
        
        # 如果有结果数据，存储简化版本（避免数据过大）
        if result_data:
            turn["result_summary"] = {
                "type": result_data.get("type"),  # search/resource/stats等
                "count": result_data.get("count", 0),
                "items": result_data.get("items", [])[:3]  # 只保留前3个结果
            }
        
        history.append(turn)
        
        # 保持历史记录在限定轮数内
        if len(history) > max_history:
            history = history[-max_history:]
        
        data["conversation_history"] = history
        data["last_active"] = int(time.time())
        
        p = _session_path(session_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        
        return data
    
    def get_conversation_history(self, session_id: str, limit: int = 5) -> list:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
            limit: 返回的最大轮数
            
        Returns:
            对话历史列表
        """
        data = self.get_session(session_id)
        if not data:
            return []
        
        history = data.get("conversation_history", [])
        return history[-limit:] if limit else history

    def set_pending_action(
        self, 
        session_id: str, 
        action_type: str, 
        action_params: Dict[str, Any] = None,
        description: str = None
    ) -> Dict[str, Any]:
        """
        设置待确认操作
        
        Args:
            session_id: 会话ID
            action_type: 操作类型（如 delete_archive, clear_trash, export_data 等）
            action_params: 操作参数（如 archive_id, export_format 等）
            description: 操作描述（用于向用户展示）
            
        Returns:
            更新后的会话数据
        """
        data = self.get_session(session_id) or self.create_session(session_id)
        
        data["pending_action"] = {
            "type": action_type,
            "params": action_params or {},
            "description": description,
            "created_at": int(time.time())
        }
        
        data["last_active"] = int(time.time())
        
        p = _session_path(session_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        
        return data
    
    def get_pending_action(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取待确认操作
        
        Args:
            session_id: 会话ID
            
        Returns:
            待确认操作信息，如果没有则返回 None
        """
        data = self.get_session(session_id)
        if not data:
            return None
        
        return data.get("pending_action")
    
    def clear_pending_action(self, session_id: str) -> Dict[str, Any]:
        """
        清除待确认操作
        
        Args:
            session_id: 会话ID
            
        Returns:
            更新后的会话数据
        """
        data = self.get_session(session_id)
        if not data:
            return {}
        
        if "pending_action" in data:
            del data["pending_action"]
        
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
