"""
Bot commands module
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from ...utils.language_context import get_language_context

from .basic import start_command, help_command
from .search import search_command
from .tag import tags_command
from .stats import stats_command
from .language import language_command
from .ai import ai_status_command
from .note import note_command, cancel_command, notes_command
from .trash import trash_command
from .export import export_command
from .backup import backup_command
from .review import review_command
from .setting import setting_command
from .rand import rand_command

logger = logging.getLogger(__name__)

__all__ = [
    'start_command',
    'help_command',
    'search_command',
    'tags_command',
    'stats_command',
    'language_command',
    'ai_status_command',
    'note_command',
    'cancel_command',
    'notes_command',
    'trash_command',
    'export_command',
    'backup_command',
    'review_command',
    'setting_command',
    'rand_command',
    'dispatch_command_after_note',
]


# Command mapping for dispatch
COMMAND_HANDLERS = {
    '/start': start_command,
    '/help': help_command,
    '/search': search_command,
    '/s': search_command,
    '/tags': tags_command,
    '/t': tags_command,
    '/stats': stats_command,
    '/st': stats_command,
    '/language': language_command,
    '/la': language_command,
    '/ai': ai_status_command,
    '/note': note_command,
    '/n': note_command,
    '/notes': notes_command,
    '/cancel': cancel_command,
    '/trash': trash_command,
    '/export': export_command,
    '/backup': backup_command,
    '/review': review_command,
    '/setting': setting_command,
    '/set': setting_command,
    '/rand': rand_command,
    '/r': rand_command,
}


async def dispatch_command_after_note(
    command_text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Dispatch command after exiting note mode
    
    This function executes a command that was sent during note mode.
    It parses the command, finds the handler, and calls it with proper context.
    
    Args:
        command_text: Full command text (e.g., "/search xxx")
        update: Telegram update (from callback query)
        context: Bot context
        
    Returns:
        True if command was executed successfully, False otherwise
    """
    try:
        # Parse command and arguments
        parts = command_text.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        logger.info(f"Dispatching command after note: {command} with args: {args}")
        
        # Find command handler
        handler = COMMAND_HANDLERS.get(command)
        if not handler:
            logger.warning(f"Unknown command: {command}")
            # Get language context only when needed for error message
            lang_ctx = get_language_context(update, context)
            await update.callback_query.message.reply_text(
                lang_ctx.t('unknown_command_hint', command=command)
            )
            return False
        
        # Set command arguments
        if args:
            context.args = args.split()
        else:
            context.args = []
        
        # Execute command handler
        # Note: Don't pass lang_ctx here - let the @with_language_context decorator handle it
        # The handler will use update.effective_message which works for callbacks
        if update.callback_query and update.callback_query.message:
            await handler(update, context)
            
            logger.info(f"✓ Command executed: {command}")
            return True
        else:
            logger.error("No message in callback query, cannot execute command")
            return False
            
    except Exception as e:
        logger.error(f"Error dispatching command '{command_text}': {e}", exc_info=True)
        try:
            lang_ctx = get_language_context(update, context)
            await update.callback_query.message.reply_text(
                lang_ctx.t('error_occurred', error=str(e))
            )
        except Exception:
            pass
        return False

