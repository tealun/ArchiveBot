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

# Media handlers are simple wrappers that call handle_message


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo message"""
    await handle_message(update, context)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video message"""
    await handle_message(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document message"""
    await handle_message(update, context)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio message"""
    await handle_message(update, context)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice message"""
    await handle_message(update, context)


async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle animation (GIF) message"""
    await handle_message(update, context)


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker message"""
    await handle_message(update, context)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle contact message"""
    await handle_message(update, context)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle location message"""
    await handle_message(update, context)
