"""
Message handlers module
"""

from .utils import _cleanup_user_data, _is_media_message
from .message_processor import _process_single_message, _auto_generate_note
from .batch_processor import _process_batch_messages, _batch_callback
from .note_mode import _handle_note_mode_message, note_timeout_callback, _finalize_note_internal
from .media_handlers import (
    handle_photo,
    handle_video,
    handle_document,
    handle_audio,
    handle_voice,
    handle_animation,
    handle_sticker,
    handle_contact,
    handle_location
)

__all__ = [
    # Utils
    '_cleanup_user_data',
    '_is_media_message',
    # Message processor
    '_process_single_message',
    '_auto_generate_note',
    # Batch processor
    '_process_batch_messages',
    '_batch_callback',
    # Note mode
    '_handle_note_mode_message',
    'note_timeout_callback',
    '_finalize_note_internal',
    # Media handlers
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
