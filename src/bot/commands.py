"""
Bot commands - Main Entry Point
Handles /start, /help, /search, /tags, /stats, /language etc.
"""

# Import all commands from submodules
from .commands import (
    start_command,
    help_command,
    search_command,
    tags_command,
    stats_command,
    language_command,
    ai_status_command,
    note_command,
    cancel_command,
    notes_command,
    trash_command,
    export_command,
    backup_command,
    review_command,
    setting_command,
)

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
]
