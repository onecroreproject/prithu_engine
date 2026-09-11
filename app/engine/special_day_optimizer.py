# ============================================================================
# PRITHU BACKEND - SPECIAL DAY OPTIMIZER
# ============================================================================
# Handles Special Day categories (Diwali, New Year, Republic Day, etc.)
# 24-Hour Active Window (Midnight to Midnight Expiry) + Dedicated Section
# ============================================================================

from typing import List, Dict, Any
from datetime import datetime

from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class SpecialDayOptimizer:
    """
    Sub-Optimizer responsible for Special Day content.
    - Serves Special Day content under dedicated 'special_day' section.
    - Enforces 24-hour active window (12:00 AM to 11:59 PM on the specific day).
    - At 12:00 AM midnight, festival posts expire for lifetime.
    """

    SPECIAL_DAY_KEYWORDS = [
        "special day", "republic day", "independence day", "diwali", "pongal",
        "new year", "holi", "navaratri", "dussehra", "valentine", "christmas",
        "bakrid", "eid", "raksha bandhan", "gandhi jayanti", "teacher day",
        "mother's day", "father's day", "women's day", "festival wishes"
    ]

    def is_special_day_post(self, feed: Dict[str, Any], cat_name: str) -> bool:
        """
        Check if a feed post is categorized as a Special Day post.

        Args:
            feed: Feed document
            cat_name: Category display name

        Returns:
            True if post is a Special Day item
        """
        cat_lower = str(cat_name).lower().strip()
        caption_lower = str(feed.get("caption", "")).lower()

        # Check quick select flag from admin or category name keywords
        if feed.get("isSpecialDay") is True or feed.get("quickSelect") == "SPECIAL_DAY":
            return True

        if any(k in cat_lower for k in self.SPECIAL_DAY_KEYWORDS):
            return True

        if any(k in caption_lower for k in self.SPECIAL_DAY_KEYWORDS):
            return True

        return False

    def is_post_valid_for_today(self, feed: Dict[str, Any], current_date: datetime) -> bool:
        """
        Check if Special Day post is active for today's 24-hour window (12:00 AM to 11:59 PM).
        At 12:00 AM midnight, posts for past dates expire.

        Args:
            feed: Feed document
            current_date: Current datetime

        Returns:
            True if active today
        """
        created_at = feed.get("createdAt") or feed.get("publish_date")
        if not isinstance(created_at, datetime):
            return True  # Allow fallback

        # Active if created on the same calendar day (12:00 AM to 11:59 PM)
        # Or scheduled date matches current_date (day and month)
        if created_at.date() == current_date.date():
            return True

        # Check if recurring annual festival date matches today
        if created_at.month == current_date.month and created_at.day == current_date.day:
            return True

        return False

    def apply_special_day_filter(
        self,
        candidates: List[Dict[str, Any]],
        categories_map: Dict[str, str],
        current_time: datetime,
        section: str
    ) -> List[Dict[str, Any]]:
        """
        Filter Special Day content based on section tab and 24-hour midnight expiry.

        Args:
            candidates: Candidate feed documents
            categories_map: Category ID to name map
            current_time: Current datetime (IST)
            section: Requested section tab ('all', 'special_day', 'god', 'general')

        Returns:
            Filtered list of candidate feeds
        """
        try:
            is_special_day_tab = (section.lower() == "special_day")
            filtered = []
            expired_count = 0

            for feed in candidates:
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)
                cat_name = categories_map.get(cat_id, feed.get("caption", ""))

                is_special = self.is_special_day_post(feed, cat_name)

                if is_special_day_tab:
                    # In Special Day Tab: Show ONLY valid today Special Day posts
                    if is_special and self.is_post_valid_for_today(feed, current_time):
                        filtered.append(feed)
                    else:
                        expired_count += 1
                else:
                    # In Non-Special Day Tabs: Exclude Special Day posts to prevent feed pollution
                    if not is_special:
                        filtered.append(feed)

            logger.info(
                f"🎉 Special Day Optimizer [Section: '{section}']: {len(candidates)} candidates ➔ {len(filtered)} allowed "
                f"({expired_count} expired/mismatched special day posts filtered)"
            )

            # Fallback for Special Day tab if no specific festival is active today
            if is_special_day_tab and not filtered:
                logger.info(f"⚠️ Special Day Section empty for today ({current_time.date()}). Returning active festival wishes.")
                return [
                    f for f in candidates
                    if self.is_special_day_post(f, categories_map.get(str(f.get("category", [""])[0]), ""))
                ]

            return filtered

        except Exception as e:
            logger.error(f"Error in SpecialDayOptimizer: {e}")
            raise OptimizerException(
                "Failed to apply Special Day filter",
                details={"error": str(e)}
            )
