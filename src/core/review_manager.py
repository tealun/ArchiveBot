"""
Review and statistics manager
Provides recap, random review, and activity summaries
"""

import logging
from typing import Optional, Dict, Any

from ..storage.database import DatabaseStorage
from .tag_manager import TagManager
from ..utils.helpers import format_datetime
from ..utils.i18n import get_i18n

logger = logging.getLogger(__name__)


class ReviewManager:
    """Encapsulates recap and statistics operations (no command wiring here)"""

    def __init__(self, db_storage: DatabaseStorage, tag_manager: TagManager):
        self.db_storage = db_storage
        self.tag_manager = tag_manager
        self.i18n = get_i18n()

    def get_random_archive(self, content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Pick a random (non-deleted) archive for revisit"""
        return self.db_storage.get_random_archive(exclude_deleted=True, content_type=content_type)

    def get_activity_summary(self, period: str = "month") -> Optional[Dict[str, Any]]:
        """Return activity summary for a period (week/month/year)"""
        days_map = {
            "week": 7,
            "month": 30,
            "year": 365,
        }
        days = days_map.get(period, 30)
        summary = self.db_storage.get_activity_summary(days)
        if not summary:
            return None

        trend = summary.get("trend", [])
        active_days = sum(1 for item in trend if item.get("count", 0) > 0)

        summary.update(
            {
                "period": period,
                "days": days,
                "generated_at": format_datetime(),
                "active_days": active_days,
            }
        )
        return summary

    def build_report(self, period: str = "month", include_random: bool = True) -> Dict[str, Any]:
        """Assemble a structured stats report for later rendering/export"""
        summary = self.get_activity_summary(period) or {}
        report = {
            "period": summary.get("period", period),
            "days": summary.get("days"),
            "generated_at": summary.get("generated_at", format_datetime()),
            "totals": {
                "archives": summary.get("archives", 0),
                "deleted": summary.get("deleted", 0),
                "notes": summary.get("notes", 0),
            },
            "trend": summary.get("trend", []),
            "top_tags": summary.get("top_tags", []),
            "active_days": summary.get("active_days", 0),
        }

        if include_random:
            random_archive = self.get_random_archive()
            if random_archive:
                report["random_archive"] = random_archive
                try:
                    report["random_tags"] = self.tag_manager.get_archive_tags(random_archive["id"])
                except Exception:
                    report["random_tags"] = []

        return report
