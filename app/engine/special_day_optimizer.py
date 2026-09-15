# ============================================================================
# PRITHU BACKEND - SPECIAL DAY OPTIMIZER (DATABASE-DRIVEN)
# ============================================================================
# Handles Special Day categories (Diwali, New Year, Republic Day, Pongal, etc.)
# Reads active calendar dates directly from MongoDB PostGlobalOptions.specialDays
# ============================================================================

from typing import List, Dict, Any, Set
from datetime import datetime

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class SpecialDayOptimizer:
    """
    Sub-Optimizer responsible for Special Day content.
    - Queries MongoDB PostGlobalOptions (specialDays array) for active festival dates.
    - Enforces 24-hour active window (12:00 AM to 11:59 PM on the specific day).
    - At 12:00 AM midnight, festival posts expire for lifetime.
    """

    FALLBACK_SPECIAL_KEYWORDS = [
        "special day", "republic day", "independence day", "diwali", "pongal",
        "new year", "holi", "navaratri", "dussehra", "valentine", "christmas",
        "bakrid", "eid", "raksha bandhan", "gandhi jayanti", "teacher day",
        "mother's day", "father's day", "women's day", "festival wishes"
    ]

    def __init__(self):
        self.db = get_db_manager()

    def get_todays_active_festivals_from_db(self, current_date: datetime) -> Set[str]:
        """
        Query MongoDB PostGlobalOptions.specialDays for active festival names matching today's date.

        Args:
            current_date: Current datetime

        Returns:
            Set of active festival name strings
        """
        try:
            today_str = current_date.strftime("%Y-%m-%d")
            global_options = self.db.find_one("PostGlobalOptions", {})

            active_festivals = set()

            if global_options and "specialDays" in global_options:
                special_days = global_options.get("specialDays", [])
                for item in special_days:
                    if item.get("isActive", True):
                        item_name = str(item.get("name", "")).lower().strip()
                        item_date_str = str(item.get("date", "")).strip()

                        # Exact date match ("YYYY-MM-DD")
                        is_active_today = (item_date_str == today_str)

                        # Recurring yearly match (Month & Day match)
                        if not is_active_today and item.get("isRecurringYearly", True) and len(item_date_str) >= 10:
                            try:
                                item_date = datetime.strptime(item_date_str[:10], "%Y-%m-%d")
                                if item_date.month == current_date.month and item_date.day == current_date.day:
                                    is_active_today = True
                            except ValueError:
                                pass

                        if is_active_today:
                            # Split combined names (e.g., "Pongal / Makar Sankranti" -> "pongal", "makar sankranti")
                            for part in item_name.split("/"):
                                active_festivals.add(part.strip())

            if active_festivals:
                logger.debug(f"🎉 Active DB Festivals for today ({today_str}): {active_festivals}")

            return active_festivals

        except Exception as e:
            logger.warning(f"Error reading specialDays from PostGlobalOptions: {e}")
            return set()

    def is_special_day_post(self, feed: Dict[str, Any], cat_name: str) -> bool:
        """Check if a post is a Special Day item."""
        cat_lower = str(cat_name).lower().strip()
        caption_lower = str(feed.get("caption", "")).lower()

        if feed.get("isSpecialDay") is True or feed.get("quickSelect") == "SPECIAL_DAY":
            return True

        if any(k in cat_lower for k in self.FALLBACK_SPECIAL_KEYWORDS):
            return True

        if any(k in caption_lower for k in self.FALLBACK_SPECIAL_KEYWORDS):
            return True

        return False

    def apply_special_day_filter(
        self,
        candidates: List[Dict[str, Any]],
        categories_map: Dict[str, str],
        current_time: datetime,
        section: str
    ) -> List[Dict[str, Any]]:
        """Apply Special Day filter dynamically from MongoDB."""
        try:
            is_special_day_tab = (section.lower() == "special_day")
            active_db_festivals = self.get_todays_active_festivals_from_db(current_time)

            filtered = []
            expired_count = 0

            for feed in candidates:
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)
                cat_name = categories_map.get(cat_id, feed.get("caption", ""))

                is_special = self.is_special_day_post(feed, cat_name)

                if is_special_day_tab:
                    # Under Special Day tab: Return Special Day posts matching today's active festival
                    if is_special:
                        cat_lower = cat_name.lower()
                        caption_lower = str(feed.get("caption", "")).lower()

                        if not active_db_festivals or any(f in cat_lower or f in caption_lower for f in active_db_festivals):
                            filtered.append(feed)
                        else:
                            expired_count += 1
                    else:
                        expired_count += 1
                else:
                    # In non-Special Day tabs: Exclude Special Day posts to prevent feed pollution
                    if not is_special:
                        filtered.append(feed)

            logger.info(
                f"🎉 Special Day Optimizer [Section: '{section}']: {len(candidates)} candidates ➔ {len(filtered)} allowed "
                f"({expired_count} expired/mismatched special day posts filtered)"
            )

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
