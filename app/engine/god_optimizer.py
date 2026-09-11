# ============================================================================
# PRITHU BACKEND - GOD CATEGORY OPTIMIZER
# ============================================================================
# Enforces the 24-Hour Day-of-Week God Schedule (12:00 AM to 11:59 PM)
# ============================================================================
# Monday:    🔱 Shiva / Parvati / Natarajar
# Tuesday:   🦚 Murugan / Amman / Karuppasamy
# Wednesday: 🐘 Vinayagar (Ganesha) / Saraswati / Ayyanar
# Thursday:  🙏 Dakshinamurthy / Perumal / Rama
# Friday:    🌺 Meenakshi / Mariamman / Mahalakshmi / Andal
# Saturday:  🪐 Saneeswaran / Ayyappan / Hanuman
# Sunday:    ☀️ Surya / Krishna / Perumal / Murugan
# ============================================================================

from typing import List, Dict, Any, Tuple
from datetime import datetime

from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class GodCategoryOptimizer:
    """
    Sub-Optimizer enforcing 24-hour Day-of-Week God Schedule.
    Filters devotional/God content so that only the deities assigned to today's day
    are active from 12:00 AM to 11:59 PM.
    """

    # Day of Week Schedule Mapping (0 = Monday, 1 = Tuesday, ..., 6 = Sunday)
    DAY_GOD_SCHEDULE = {
        0: {  # Monday
            "day": "Monday",
            "gods": ["shiva", "parvati", "natarajar", "nataraja", "sivan"],
            "description": "🔱 Shiva / Parvati / Natarajar"
        },
        1: {  # Tuesday
            "day": "Tuesday",
            "gods": ["murugan", "amman", "karuppasamy", "subramanya", "karthikeya"],
            "description": "🦚 Murugan / Amman / Karuppasamy"
        },
        2: {  # Wednesday
            "day": "Wednesday",
            "gods": ["vinayagar", "ganesha", "ganesh", "saraswati", "ayyanar", "pillayar"],
            "description": "🐘 Vinayagar (Ganesha) / Saraswati / Ayyanar"
        },
        3: {  # Thursday
            "day": "Thursday",
            "gods": ["dakshinamurthy", "perumal", "rama", "baba", "sai baba", "guru"],
            "description": "🙏 Dakshinamurthy / Perumal / Rama"
        },
        4: {  # Friday
            "day": "Friday",
            "gods": ["meenakshi", "mariamman", "mahalakshmi", "lakshmi", "andal", "durga", "devi"],
            "description": "🌺 Meenakshi / Mariamman / Mahalakshmi / Andal"
        },
        5: {  # Saturday
            "day": "Saturday",
            "gods": ["saneeswaran", "shani", "ayyappan", "ayyappa", "hanuman", "anjaneya", "venkateswara"],
            "description": "🪐 Saneeswaran / Ayyappan / Hanuman"
        },
        6: {  # Sunday
            "day": "Sunday",
            "gods": ["surya", "krishna", "perumal", "murugan", "sun god"],
            "description": "☀️ Surya / Krishna / Perumal / Murugan"
        }
    }

    # All known God keywords for identification
    ALL_GOD_KEYWORDS = [
        "god", "bhakti", "devotional", "god quotes", "shiva", "parvati", "natarajar",
        "murugan", "amman", "karuppasamy", "vinayagar", "ganesha", "saraswati",
        "ayyanar", "dakshinamurthy", "perumal", "rama", "meenakshi", "mariamman",
        "mahalakshmi", "andal", "saneeswaran", "ayyappan", "hanuman", "surya", "krishna"
    ]

    def is_god_post(self, feed: Dict[str, Any], cat_name: str) -> bool:
        """
        Check if a post is a God/Devotional content post.

        Args:
            feed: Feed document
            cat_name: Category display name

        Returns:
            True if post is God/Devotional content
        """
        cat_lower = str(cat_name).lower().strip()
        caption_lower = str(feed.get("caption", "")).lower()

        if feed.get("isGod") is True or feed.get("quickSelect") == "GOD":
            return True

        if any(k in cat_lower for k in self.ALL_GOD_KEYWORDS):
            return True

        if any(k in caption_lower for k in self.ALL_GOD_KEYWORDS):
            return True

        return False

    def is_god_matching_today(self, cat_name: str, current_weekday: int) -> bool:
        """
        Check if God category matches today's designated weekday deities.

        Args:
            cat_name: Category name or feed text
            current_weekday: Weekday index (0 = Monday ... 6 = Sunday)

        Returns:
            True if deity matches today's schedule
        """
        cat_lower = str(cat_name).lower().strip()
        today_info = self.DAY_GOD_SCHEDULE.get(current_weekday, {})
        today_gods = today_info.get("gods", [])

        # Generic "God", "Devotional", "Bhakti" posts match any day
        if cat_lower in ["god", "god quotes", "devotional", "bhakti"]:
            return True

        # Specific God posts match if deity is in today's allowed list
        return any(g in cat_lower for g in today_gods)

    def apply_god_schedule_filter(
        self,
        candidates: List[Dict[str, Any]],
        categories_map: Dict[str, str],
        current_time: datetime,
        section: str
    ) -> List[Dict[str, Any]]:
        """
        Apply 24-hour Day-of-Week God Schedule filter.
        At 12:00 AM midnight, Friday's Gods expire and Saturday's Gods unlock.

        Args:
            candidates: Candidate feed documents
            categories_map: Category ID to name map
            current_time: Current datetime (IST)
            section: Requested section tab ('all', 'special_day', 'god', 'general')

        Returns:
            Filtered list of candidate feeds
        """
        try:
            current_weekday = current_time.weekday()
            today_schedule = self.DAY_GOD_SCHEDULE.get(current_weekday, {})
            day_name = today_schedule.get("day", "Today")
            description = today_schedule.get("description", "")

            logger.info(f"🙏 24-Hour God Schedule [{day_name}]: Active Deities ➔ {description}")

            is_god_section = (section.lower() == "god")
            filtered = []
            mismatched_count = 0

            for feed in candidates:
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)
                cat_name = categories_map.get(cat_id, feed.get("caption", ""))

                is_god = self.is_god_post(feed, cat_name)

                if is_god_section:
                    # Under God section: Return ONLY God posts that match TODAY'S weekday schedule
                    if is_god and self.is_god_matching_today(cat_name, current_weekday):
                        filtered.append(feed)
                    else:
                        mismatched_count += 1
                else:
                    # In other sections: If it's a God post, only allow if it matches today's schedule
                    if is_god:
                        if self.is_god_matching_today(cat_name, current_weekday):
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
