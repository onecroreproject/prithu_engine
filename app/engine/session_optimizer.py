# ============================================================================
# PRITHU BACKEND - SESSION TIME SLOT OPTIMIZER
# ============================================================================
# Enforces strict 4-session time slot boundaries & greeting post filtering
# ============================================================================
# 🌅 Morning Session:   5:00 AM – 11:59 AM  (Good Morning Greetings)
# ☀️ Afternoon Session: 12:00 PM – 3:59 PM  (Good Afternoon Greetings)
# 🌆 Evening Session:   4:00 PM – 6:59 PM   (Good Evening Greetings)
# 🌙 Night Session:     7:00 PM – 4:59 AM   (Good Night Greetings)
# ============================================================================

from typing import List, Dict, Any, Tuple
from datetime import datetime

from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class SessionTimeSlotOptimizer:
    """
    Sub-Optimizer responsible for enforcing session time slots.
    Ensures session greeting posts (Good Morning, Good Afternoon, Good Evening, Good Night)
    are strictly shown ONLY during their designated session time windows.
    """

    SESSION_MORNING = "Morning"      # 5:00 AM to 11:59 AM
    SESSION_AFTERNOON = "Afternoon"  # 12:00 PM to 3:59 PM
    SESSION_EVENING = "Evening"      # 4:00 PM to 6:59 PM
    SESSION_NIGHT = "Night"          # 7:00 PM to 4:59 AM

    # Category name keywords for session greetings
    SESSION_KEYWORDS = {
        SESSION_MORNING: ["good morning", "morning motivation", "morning spiritual"],
        SESSION_AFTERNOON: ["good afternoon"],
        SESSION_EVENING: ["good evening"],
        SESSION_NIGHT: ["good night", "night motivation"]
    }

    @classmethod
    def get_current_session(cls, current_hour: int) -> str:
        """
        Determine current active session name based on hour (0-23).

        Args:
            current_hour: Hour of day (0-23)

        Returns:
            Session name string (Morning, Afternoon, Evening, Night)
        """
        if 5 <= current_hour < 12:
            return cls.SESSION_MORNING
        elif 12 <= current_hour < 16:
            return cls.SESSION_AFTERNOON
        elif 16 <= current_hour < 19:
            return cls.SESSION_EVENING
        else:
            return cls.SESSION_NIGHT

    def is_post_matching_session(
        self,
        category_name: str,
        active_session: str
    ) -> Tuple[bool, bool]:
        """
        Check if a post belongs to a session greeting category, and if it matches current active session.

        Args:
            category_name: Name of category or feed metadata
            active_session: Current active session name

        Returns:
            Tuple of (is_session_post: bool, matches_current_session: bool)
        """
        cat_lower = str(category_name).lower().strip()

        # Check if this post is a session greeting post for ANY session
        post_session = None
        for sess_name, keywords in self.SESSION_KEYWORDS.items():
            if any(k in cat_lower for k in keywords):
                post_session = sess_name
                break

        if post_session is None:
            # General post (not a session greeting post)
            return False, True

        # Session post -> returns True for is_session_post, and whether it matches current active session
        return True, (post_session == active_session)

    def apply_session_filter(
        self,
        candidates: List[Dict[str, Any]],
        categories_map: Dict[str, str],
        current_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Apply strict session boundary filter.
        Session posts for inactive sessions (e.g. Good Morning posts during Afternoon hours)
        are HARD-LOCKED out and preserved unviewed for the next appropriate session window.

        Args:
            candidates: Candidate feed documents
            categories_map: Dict mapping category ObjectId string to category name
            current_time: Current datetime (IST or local time)

        Returns:
            Filtered list of candidate feeds compliant with active time slot session
        """
        try:
            active_session = self.get_current_session(current_time.hour)
            logger.info(f"⏰ Active Session Slot at Hour {current_time.hour:02d}:00 ➔ [{active_session} Session]")

            filtered_feeds = []
            locked_count = 0

            for feed in candidates:
                # Extract category name
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)
                cat_name = categories_map.get(cat_id, feed.get("caption", ""))

                is_session_post, matches_active = self.is_post_matching_session(cat_name, active_session)

                if is_session_post and not matches_active:
                    # Hard lock: Do NOT display mismatched session greetings
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
