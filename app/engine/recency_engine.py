# ============================================================================
# PRITHU BACKEND - USER RECENCY STAGGER ENGINE
# ============================================================================
# Manages Old User catch-up feeds vs New User historical backlog staggering
# ============================================================================

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


class UserRecencyStaggerEngine:
    """
    Sub-Optimizer responsible for account age detection and feed recency staggering.
    - Old Users: Queries dynamic catch-up feeds since last active login.
    - New Users: Queries 80% historical backlog (15-90 days old) + 20% fresh mix.
    """

    def __init__(self):
        self.db = get_db_manager()

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch user profile document."""
        try:
            from bson import ObjectId
            query_filter = {}
            if ObjectId.is_valid(user_id):
                query_filter = {"$or": [{"_id": ObjectId(user_id)}, {"_id": user_id}]}
            else:
                query_filter = {"_id": user_id}

            return (
                self.db.find_one(Config.COLLECTION_USERS, query_filter)
                or self.db.find_one("Accounts", query_filter)
                or self.db.find_one("users", query_filter)
                or {}
            )
        except Exception as e:
            logger.warning(f"Error getting user profile for {user_id}: {e}")
            return {}

    def get_days_since_last_login(self, user_id: str, user_profile: Dict[str, Any]) -> int:
        """Calculate days since last user activity/login."""
        try:
            last_active = (
                user_profile.get("lastActive")
                or user_profile.get("lastLoginAt")
                or user_profile.get("updatedAt")
            )
            if isinstance(last_active, datetime):
                days_away = (datetime.utcnow() - last_active).days
                return max(1, days_away + 1)

            return Config.OLD_USER_FRESHNESS_DAYS

        except Exception as e:
            logger.warning(f"Error calculating days since last login for {user_id}: {e}")
            return Config.OLD_USER_FRESHNESS_DAYS

    def classify_user(self, user_id: str, seen_count: int) -> Tuple[bool, int, str]:
        """
        Classify user as New User or Old User.

        Args:
            user_id: User identifier
            seen_count: Count of feeds seen in lifetime

        Returns:
            Tuple of (is_new_user: bool, days_away: int, strategy_label: str)
        """
        try:
            profile = self.get_user_profile(user_id)
            created_at = profile.get("createdAt") or profile.get("created_at")

            is_new_user = False
            account_age_days = Config.NEW_USER_AGE_DAYS + 1

            if isinstance(created_at, datetime):
                account_age_days = (datetime.utcnow() - created_at).days
                is_new_user = account_age_days <= Config.NEW_USER_AGE_DAYS
            elif seen_count < 10:
                # Level 2 Fallback: < 10 seen feeds -> New User
                is_new_user = True
                account_age_days = 1

            days_away = self.get_days_since_last_login(user_id, profile)

            label = "New User (Backlog Strategy)" if is_new_user else f"Old User (Catchup {days_away}d Strategy)"
            logger.info(f"👥 User {user_id}: Age={account_age_days}d, DaysAway={days_away}d ➔ Strategy: [{label}]")

            return is_new_user, days_away, label

        except Exception as e:
            logger.warning(f"Error classifying user {user_id}: {e}")
            return False, Config.OLD_USER_FRESHNESS_DAYS, "Old User (Default Catchup Strategy)"

    def get_candidate_feeds(
        self,
        user_id: str,
        is_new_user: bool,
        days_away: int,
        blacklist: set,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch candidate feeds based on user classification.

        Args:
            user_id: User identifier
            is_new_user: True if account age <= 14 days
            days_away: Days since user last logged in
            blacklist: Set of seen feed IDs
            limit: Target recommendation count

        Returns:
            List of candidate feed documents
        """
        try:
            base_query = {"isApproved": True, "isDeleted": False}
            current_time = datetime.utcnow()

            if not is_new_user:
                # Old User Catchup
                catchup_start = current_time - timedelta(days=days_away)
                fresh_query = {**base_query, "createdAt": {"$gte": catchup_start}}

                candidates = self.db.find_many(Config.COLLECTION_FEEDS, fresh_query, limit=1000)
                candidates = [f for f in candidates if str(f.get("_id")) not in blacklist]

                if len(candidates) < limit:
                    logger.info(f"⚠️ Old User {user_id}: Fallback to unviewed feeds")
                    fallback = self.db.find_many(Config.COLLECTION_FEEDS, base_query, limit=2000)
                    for f in fallback:
                        fid = str(f.get("_id"))
                        if fid not in blacklist and not any(str(x.get("_id")) == fid for x in candidates):
                            candidates.append(f)
                            if len(candidates) >= limit * 3:
                                break

                return candidates

            else:
                # New User Backlog (80% 15-90d / 20% fresh)
                backlog_start = current_time - timedelta(days=Config.BACKLOG_MAX_DAYS)
                backlog_end = current_time - timedelta(days=Config.BACKLOG_MIN_DAYS)

                backlog_query = {**base_query, "createdAt": {"$gte": backlog_start, "$lte": backlog_end}}
                backlog = self.db.find_many(Config.COLLECTION_FEEDS, backlog_query, limit=1500)
                backlog = [f for f in backlog if str(f.get("_id")) not in blacklist]

                fresh_query = {**base_query, "createdAt": {"$gte": current_time - timedelta(days=3)}}
                fresh = self.db.find_many(Config.COLLECTION_FEEDS, fresh_query, limit=500)
                fresh = [f for f in fresh if str(f.get("_id")) not in blacklist]

                target_backlog = int(limit * Config.NEW_USER_BACKLOG_RATIO)
                target_fresh = limit - target_backlog

                combined = backlog[:target_backlog * 3] + fresh[:target_fresh * 3]
                if not combined:
                    combined = self.db.find_many(Config.COLLECTION_FEEDS, base_query, limit=1000)
                    combined = [f for f in combined if str(f.get("_id")) not in blacklist]

                return combined

        except Exception as e:
            logger.error(f"Error fetching candidate feeds in UserRecencyStaggerEngine: {e}")
            raise OptimizerException(
                "Failed to fetch recency candidate feeds",
                details={"error": str(e)}
            )
