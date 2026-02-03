"""
Callback handlers module
"""

# Language callbacks
from .language import handle_language_callback

# Tag callbacks
from .tag import (
    handle_tag_callback,
    handle_tags_page_callback,
    handle_tag_list_page_callback
)

# Search callbacks
from .search import handle_search_page_callback

# AI callbacks
from .ai import (
    handle_ai_view_callback,
    handle_ai_confirm_callback,
    handle_ai_cancel_callback
)

# Trash callbacks
from .trash import (
    handle_delete_callback,
    handle_trash_restore_callback,
    handle_trash_delete_callback
)

# Note callbacks
from .note import (
    handle_note_callback,
    handle_note_view_callback,
    handle_notes_page_callback,
    handle_note_exit_save_callback,
    handle_note_finish_callback,
    handle_note_continue_callback,
    handle_note_add_callback,
    handle_note_edit_callback,
    handle_note_modify_callback,
    handle_note_append_callback,
    handle_note_share_callback,
    handle_note_delete_callback,
    handle_note_quick_edit_callback,
    handle_note_quick_append_callback,
    handle_note_quick_delete_callback,
    handle_note_quick_delete_confirm_callback,
    handle_continuity_callback,
    handle_refine_note_callback
)

# Review callbacks
from .review import handle_review_callback

# Intent callbacks
from .intent import (
    handle_short_text_intent_callback,
    handle_long_text_intent_callback
)

# Favorite callbacks
from .favorite import (
    handle_favorite_callback,
    handle_forward_callback
)

# Backup callbacks
from .backup import (
    handle_backup_create_now_callback,
    handle_backup_keep_callback,
    handle_backup_delete_all_callback
)

# Export callbacks
from .export import handle_export_format_callback

# Setting callbacks
from .setting import (
    handle_setting_category_callback,
    handle_setting_item_callback,
    handle_setting_set_callback,
    handle_setting_back_callback,
    handle_setting_input,
    handle_auto_install_callback,
    handle_manual_install_callback,
)

__all__ = [
    # Language
    'handle_language_callback',
    # Tag
    'handle_tag_callback',
    'handle_tags_page_callback',
    'handle_tag_list_page_callback',
    # Search
    'handle_search_page_callback',
    # AI
    'handle_ai_view_callback',
    # Trash
    'handle_delete_callback',
    'handle_trash_restore_callback',
    'handle_trash_delete_callback',
    # Note
    'handle_note_callback',
    'handle_note_view_callback',
    'handle_note_exit_save_callback',
    'handle_note_finish_callback',
    'handle_note_continue_callback',
    'handle_note_add_callback',
    'handle_note_edit_callback',
    'handle_note_modify_callback',
    'handle_note_append_callback',
    'handle_note_share_callback',
    'handle_note_delete_callback',
    'handle_note_quick_edit_callback',
    'handle_note_quick_append_callback',
    'handle_note_quick_delete_callback',
    'handle_note_quick_delete_confirm_callback',
    'handle_continuity_callback',
    'handle_refine_note_callback',
    # Review
    'handle_review_callback',
    # Intent
    'handle_short_text_intent_callback',
    'handle_long_text_intent_callback',
    # Favorite
    'handle_favorite_callback',
    'handle_forward_callback',
    # Backup
    'handle_backup_create_now_callback',
    'handle_backup_keep_callback',
    'handle_backup_delete_all_callback',
    # Export
    'handle_export_format_callback',
    # Setting
    'handle_setting_category_callback',
    'handle_setting_item_callback',
    'handle_setting_set_callback',
    'handle_setting_back_callback',
    'handle_setting_input',
    'handle_auto_install_callback',
    'handle_manual_install_callback',
]
