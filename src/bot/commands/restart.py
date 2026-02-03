"""
Restart command - 重启系统命令
"""

import sys
import os
import json
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from .note_mode_interceptor import intercept_in_note_mode
from ...utils.helpers import send_or_update_reply

logger = logging.getLogger(__name__)

# Restart state file path
RESTART_STATE_FILE = Path("data/restart_state.json")


def save_restart_state(user_id: int, chat_id: int, language: str) -> None:
    """
    Save restart state to file for post-restart notification
    
    Args:
        user_id: User who initiated restart
        chat_id: Chat to send notification to
        language: User's language preference
    """
    try:
        RESTART_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            'user_id': user_id,
            'chat_id': chat_id,
            'language': language,
            'timestamp': str(Path.cwd())  # Just to verify it's a valid restart
        }
        with open(RESTART_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        logger.info(f"Restart state saved for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save restart state: {e}", exc_info=True)


def load_restart_state() -> dict:
    """
    Load restart state from file
    
    Returns:
        dict: Restart state or empty dict if not found
    """
    try:
        if RESTART_STATE_FILE.exists():
            with open(RESTART_STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
            logger.info(f"Restart state loaded for user {state.get('user_id')}")
            return state
    except Exception as e:
        logger.error(f"Failed to load restart state: {e}", exc_info=True)
    return {}


def clear_restart_state() -> None:
    """Remove restart state file"""
    try:
        if RESTART_STATE_FILE.exists():
            RESTART_STATE_FILE.unlink()
            logger.info("Restart state cleared")
    except Exception as e:
        logger.error(f"Failed to clear restart state: {e}", exc_info=True)


@intercept_in_note_mode
@with_language_context
async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /restart command - 重启系统
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 发送重启确认消息
        restart_msg = lang_ctx.t('restart_initiated')
        await send_or_update_reply(update, context, restart_msg, 'restart', parse_mode=ParseMode.HTML)
        
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        logger.info(f"Restart command executed by user {user_id}")
        logger.info("System restart initiated...")
        
        # 保存重启状态，用于重启后发送通知
        save_restart_state(user_id, chat_id, lang_ctx.language)
        
        # 清理资源
        # 获取 application 实例
        application = context.application
        
        # 停止应用（这将触发优雅关闭）
        await application.stop()
        await application.shutdown()
        
        # 使用 os.execv 原地重启进程
        logger.info("Restarting process using os.execv...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)
        
    except Exception as e:
        logger.error(f"Error in restart_command: {e}", exc_info=True)
        error_msg = lang_ctx.t('restart_failed', error=str(e))
        await send_or_update_reply(update, context, error_msg, 'restart')
