# ============================================================================
# PRITHU BACKEND - SESSION TIME SLOT OPTIMIZER (DATABASE-DRIVEN)
# ============================================================================
# Enforces strict 4-session time slot boundaries dynamically from MongoDB
# Reads sessionsDetailed array from PostGlobalOptions collection
# ============================================================================

from typing import List, Dict, Any, Tuple
from datetime import datetime

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class SessionTimeSlotOptimizer:
    """
    Sub-Optimizer responsible for enforcing session time slots.
    Queries PostGlobalOptions.sessionsDetailed dynamically from MongoDB.
    """

    SESSION_MORNING = "Morning"      # 5:00 AM to 11:59 AM
    SESSION_AFTERNOON = "Afternoon"  # 12:00 PM to 3:59 PM
    SESSION_EVENING = "Evening"      # 4:00 PM to 6:59 PM
    SESSION_NIGHT = "Night"          # 7:00 PM to 4:59 AM

    SESSION_KEYWORDS = {
        SESSION_MORNING: ["good morning", "morning motivation", "morning spiritual"],
        SESSION_AFTERNOON: ["good afternoon"],
        SESSION_EVENING: ["good evening"],
        SESSION_NIGHT: ["good night", "night motivation"]
    }

    def __init__(self):
        self.db = get_db_manager()

    def get_current_session_from_db(self, current_hour: int) -> str:
        """
        Determine current active session dynamically from MongoDB PostGlobalOptions.sessionsDetailed.

        Args:
            current_hour: Hour of day (0-23)

        Returns:
            Session name string (Morning, Afternoon, Evening, Night)
        """
        try:
            global_options = self.db.find_one("PostGlobalOptions", {})
            if global_options and "sessionsDetailed" in global_options:
                sessions_detailed = global_options.get("sessionsDetailed", [])
                for s in sessions_detailed:
                    if s.get("isActive", True):
                        sname = str(s.get("name", "")).title()
                        start_time = str(s.get("startTime", "")).upper()
                        end_time = str(s.get("endTime", "")).upper()

                        # Example parsing: "12:00 PM" -> 12, "05:00 PM" -> 17
                        start_h = self._parse_hour_string(start_time)
                        end_h = self._parse_hour_string(end_time)

                        if start_h is not None and end_h is not None:
                            if start_h <= end_h and start_h <= current_hour < end_h:
                                return sname
                            elif start_h > end_h and (current_hour >= start_h or current_hour < end_h):
                                return sname

            # Fallback to standard time slot ranges
            return self.get_fallback_session(current_hour)

        except Exception as e:
            logger.warning(f"Error reading sessionsDetailed from PostGlobalOptions: {e}")
            return self.get_fallback_session(current_hour)

    def _parse_hour_string(self, time_str: str) -> int:
        """Parse time string like '05:00 AM' or '12:00 PM' into hour (0-23)."""
        try:
            t = datetime.strptime(time_str.strip(), "%I:%M %p")
            return t.hour
        except Exception:
            return None

    @classmethod
    def get_current_session(cls, current_hour: int) -> str:
        """Helper to get fallback session name."""
        return cls.get_fallback_session(current_hour)

    def is_post_matching_session(
        self,
        category_name: str,
        active_session: str
    ) -> Tuple[bool, bool]:
        """Check if post is a session greeting post and if it matches active session."""
        cat_lower = str(category_name).lower().strip()

        post_session = None
        for sess_name, keywords in self.SESSION_KEYWORDS.items():
            if any(k in cat_lower for k in keywords):
                post_session = sess_name
                break

        if post_session is None:
            return False, True

        return True, (post_session == active_session)

    def apply_session_filter(
        self,
        candidates: List[Dict[str, Any]],
        categories_map: Dict[str, str],
        current_time: datetime
    ) -> List[Dict[str, Any]]:
        """Apply strict session boundary filter dynamically."""
        try:
            active_session = self.get_current_session_from_db(current_time.hour)
            logger.info(f"⏰ Active Session Slot at Hour {current_time.hour:02d}:00 ➔ [{active_session} Session]")

            filtered_feeds = []
            locked_count = 0

            for feed in candidates:
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)
                cat_name = categories_map.get(cat_id, feed.get("caption", ""))

                is_session_post, matches_active = self.is_post_matching_session(cat_name, active_session)

                if is_session_post and not matches_active:
                    locked_count += 1
                    continue

                filtered_feeds.append(feed)

            logger.info(f"⏰ Session Optimizer: {len(candidates)} feeds ➔ {len(filtered_feeds)} allowed ({locked_count} mismatched session posts hard-locked for future window)")
            return filtered_feeds

        except Exception as e:
            logger.error(f"Error in SessionTimeSlotOptimizer: {e}")
            raise OptimizerException(
                "Failed to apply session time slot filter",
                details={"error": str(e)}
            )
