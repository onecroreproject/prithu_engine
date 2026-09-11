# ============================================================================
# PRITHU BACKEND - GOD CATEGORY OPTIMIZER (DATABASE-DRIVEN)
# ============================================================================
# Enforces the 24-Hour Day-of-Week God Schedule dynamically from MongoDB
# Collection: PostGlobalOptions (weekGods array)
# ============================================================================

from typing import List, Dict, Any, Set
from datetime import datetime

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class GodCategoryOptimizer:
    """
    Sub-Optimizer enforcing 24-hour Day-of-Week God Schedule.
    Dynamically queries PostGlobalOptions (weekGods array) in MongoDB.
    """

    # Static fallback schedule if DB options are unpopulated
    FALLBACK_GOD_SCHEDULE = {
        0: {"day": "Monday", "gods": ["shiva", "parvati", "natarajar", "nataraja", "sivan"]},
        1: {"day": "Tuesday", "gods": ["murugan", "amman", "karuppasamy", "subramanya"]},
        2: {"day": "Wednesday", "gods": ["vinayagar", "ganesha", "ganesh", "saraswati", "ayyanar"]},
        3: {"day": "Thursday", "gods": ["dakshinamurthy", "perumal", "rama", "baba", "sai baba"]},
        4: {"day": "Friday", "gods": ["meenakshi", "mariamman", "mahalakshmi", "lakshmi", "andal", "durga"]},
        5: {"day": "Saturday", "gods": ["saneeswaran", "shani", "ayyappan", "hanuman", "anjaneya"]},
        6: {"day": "Sunday", "gods": ["surya", "krishna", "perumal", "murugan"]}
    }

    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self):
        self.db = get_db_manager()

    def get_todays_god_keywords_from_db(self, current_weekday: int) -> Set[str]:
        """
        Query MongoDB PostGlobalOptions.weekGods for active God names assigned to today's weekday.

        Args:
            current_weekday: Weekday index (0 = Monday, ..., 6 = Sunday)

        Returns:
            Set of active God name keyword strings
        """
        try:
            day_name = self.DAY_NAMES[current_weekday]
            global_options = self.db.find_one("PostGlobalOptions", {})

            god_keywords = set()

            if global_options and "weekGods" in global_options:
                week_gods = global_options.get("weekGods", [])
                for item in week_gods:
                    if item.get("isActive", True) and str(item.get("day")).lower() == day_name.lower():
                        gname = str(item.get("godName", "")).lower().strip()
                        cname = str(item.get("categoryName", "")).lower().strip()
                        if gname:
                            god_keywords.add(gname)
                            # Split individual deity names (e.g. "Goddess Durga / Amman" -> ["durga", "amman"])
                            for part in gname.replace("/", " ").replace("-", " ").split():
                                if len(part) > 3 and part not in ["goddess", "lord", "mother"]:
                                    god_keywords.add(part)
                        if cname:
                            god_keywords.add(cname)

            if god_keywords:
                logger.debug(f"🙏 Loaded {len(god_keywords)} active God keywords dynamically from MongoDB for {day_name}")
                return god_keywords

            # Fallback to static schedule if MongoDB weekGods is empty
            fallback_gods = self.FALLBACK_GOD_SCHEDULE.get(current_weekday, {}).get("gods", [])
            logger.debug(f"🙏 Using fallback God keywords for {day_name}: {fallback_gods}")
            return set(fallback_gods)

        except Exception as e:
            logger.warning(f"Error reading weekGods from PostGlobalOptions: {e}")
            fallback_gods = self.FALLBACK_GOD_SCHEDULE.get(current_weekday, {}).get("gods", [])
            return set(fallback_gods)

    def is_god_post(self, feed: Dict[str, Any], cat_name: str) -> bool:
        """Check if post is God/Devotional content."""
        cat_lower = str(cat_name).lower().strip()
        caption_lower = str(feed.get("caption", "")).lower()

        if feed.get("isGod") is True or feed.get("quickSelect") == "GOD":
            return True

        god_indicators = ["god", "bhakti", "devotional", "god quotes", "spiritual", "worship", "temple"]
        if any(k in cat_lower for k in god_indicators) or any(k in caption_lower for k in god_indicators):
            return True

        return False

    def is_god_matching_today(self, feed: Dict[str, Any], cat_name: str, active_god_keywords: Set[str]) -> bool:
        """Check if God post matches today's active deities."""
        cat_lower = str(cat_name).lower().strip()
        caption_lower = str(feed.get("caption", "")).lower()

        # Generic God posts (e.g. "God Quotes", "Devotional") match every day
        if cat_lower in ["god", "god quotes", "devotional", "bhakti", "spiritual"]:
            return True

        # Check if category or caption matches any of today's active God keywords from DB
        if any(k in cat_lower for k in active_god_keywords):
            return True

        if any(k in caption_lower for k in active_god_keywords):
            return True

        return False

    def apply_god_schedule_filter(
        self,
        candidates: List[Dict[str, Any]],
        categories_map: Dict[str, str],
        current_time: datetime,
        section: str
    ) -> List[Dict[str, Any]]:
        """Apply 24-hour Day-of-Week God Schedule filter dynamically from MongoDB."""
        try:
            current_weekday = current_time.weekday()
            day_name = self.DAY_NAMES[current_weekday]
            active_god_keywords = self.get_todays_god_keywords_from_db(current_weekday)

            logger.info(f"🙏 24-Hour God Schedule [{day_name}]: Active DB Keywords ➔ {list(active_god_keywords)[:6]}")

            is_god_section = (section.lower() == "god")
            filtered = []
            mismatched_count = 0

            for feed in candidates:
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)
                cat_name = categories_map.get(cat_id, feed.get("caption", ""))

                is_god = self.is_god_post(feed, cat_name)

                if is_god_section:
                    if is_god and self.is_god_matching_today(feed, cat_name, active_god_keywords):
                        filtered.append(feed)
                    else:
                        mismatched_count += 1
                else:
                    if is_god:
                        if self.is_god_matching_today(feed, cat_name, active_god_keywords):
                            filtered.append(feed)
                        else:
                            mismatched_count += 1
                    else:
                        filtered.append(feed)

            logger.info(
                f"🙏 God Optimizer [{day_name}]: {len(candidates)} candidates ➔ {len(filtered)} allowed "
                f"({mismatched_count} mismatched day-of-week God posts locked out for midnight transition)"
            )

            return filtered

        except Exception as e:
            logger.error(f"Error in GodCategoryOptimizer: {e}")
            raise OptimizerException(
                "Failed to apply God Schedule filter",
                details={"error": str(e)}
            )
