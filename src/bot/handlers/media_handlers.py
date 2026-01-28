"""
Media message handlers
"""

import logging
from typing import List, Optional, Dict
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import get_language_context
from ...utils.helpers import format_file_size, truncate_text

logger = logging.getLogger(__name__)

# Media handlers are simple wrappers that delegate to message_handlers
# These are imported and re-exported by message_handlers.py to avoid circular imports


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo message"""
    # Import here to avoid circular dependency
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle animation (GIF) message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle contact message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle location message"""
    from ..message_handlers import handle_message
    await handle_message(update, context)
