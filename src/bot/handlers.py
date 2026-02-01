"""
Message handlers - Lightweight Entry Point
This file serves as a simple forwarding layer to the modularized handlers.

All actual implementations are in the handlers/ submodule package:
- handlers/message_processor.py: Single message processing
- handlers/batch_processor.py: Batch message processing
- handlers/note_mode.py: Note mode handling
- handlers/note_operations.py: Note editing operations
- handlers/ai_chat_handler.py: AI chat mode
- handlers/media_handlers.py: Media message routing
- handlers/utils.py: Utility functions
"""

# Re-export all handlers from the modularized package
from .handlers import (
    # Utils
    _cleanup_user_data,
    _is_media_message,
    # Message processor
    _process_single_message,
    _auto_generate_note,
    # Batch processor
    _process_batch_messages,
    _batch_callback,
    # Note mode
    _handle_note_mode_message,
    note_timeout_callback,
    _finalize_note_internal,
    # Note operations
    handle_note_edit_mode,
    handle_note_append_mode,
    handle_waiting_note,
    handle_note_refine,
    # AI Chat
    handle_ai_chat_mode,
    # Media handlers
    handle_photo,
    handle_video,
    handle_document,
    handle_audio,
    handle_voice,
    handle_animation,
    handle_sticker,
    handle_contact,
    handle_location,
)

# Re-export for backward compatibility
__all__ = [
    '_cleanup_user_data',
    '_is_media_message',
    '_process_single_message',
    '_auto_generate_note',
    '_process_batch_messages',
    '_batch_callback',
    '_handle_note_mode_message',
    'note_timeout_callback',
    '_finalize_note_internal',
    'handle_note_edit_mode',
    'handle_note_append_mode',
    'handle_waiting_note',
    'handle_note_refine',
    'handle_ai_chat_mode',
    'handle_photo',
    'handle_video',
    'handle_document',
    'handle_audio',
    'handle_voice',
    'handle_animation',
    'handle_sticker',
    'handle_contact',
    'handle_location',
]
