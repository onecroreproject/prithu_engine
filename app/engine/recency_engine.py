# ============================================================================
# PRITHU BACKEND - USER RECENCY STAGGER ENGINE
# ============================================================================
# Manages Old User catch-up feeds vs New User historical backlog staggering
# ============================================================================

from typing import List, Dict, Any, Tuple, Optional, Set
from datetime import datetime, timedelta

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

logger = get_logger(__name__)


FEED_PROJECTION = {
    "_id": 1,
    "category": 1,
    "subCategory": 1,
    "language": 1,
    "duration": 1,
    "postType": 1,
    "createdAt": 1,
    "total_views": 1,
    "playbackStats.totalViews": 1,
    "likes": 1,
    "engagementStats.likes": 1,
    "isApproved": 1,
    "isDeleted": 1,
    "status": 1,
    "tags": 1,
    "specialDay": 1,
    "god": 1
}


class UserRecencyStaggerEngine:
    """
    Sub-Optimizer responsible for account age detection and feed recency staggering.
    - Old Users: Queries dynamic catch-up feeds since last active login.
    - New Users: Queries 80% historical backlog (15-90 days old) + 20% fresh mix.
    """
    _feed_pool_cache: List[Dict[str, Any]] = []
    _feed_pool_cached_at: Optional[datetime] = None
    _user_profile_cache: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}

    def __init__(self):
        self.db = get_db_manager()

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch user profile document with fast in-memory caching."""
        now = datetime.utcnow()
        if user_id in self._user_profile_cache:
            cached_at, profile = self._user_profile_cache[user_id]
            if (now - cached_at).total_seconds() < 120:
                return profile

        try:
            from bson import ObjectId
            query_filter = {}
            if ObjectId.is_valid(user_id):
                query_filter = {"$or": [{"_id": ObjectId(user_id)}, {"_id": user_id}]}
            else:
                query_filter = {"_id": user_id}

            proj = {"createdAt": 1, "created_at": 1, "lastActive": 1, "lastLoginAt": 1, "updatedAt": 1}
            profile = (
                self.db.find_one(Config.COLLECTION_USERS, query_filter, projection=proj)
                or self.db.find_one("Accounts", query_filter, projection=proj)
                or self.db.find_one("users", query_filter, projection=proj)
                or {}
            )
            self._user_profile_cache[user_id] = (now, profile)
            return profile
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
            days_away = self.get_days_since_last_login(user_id, profile)
            
            # Disable Backlog Strategy completely based on user feedback
            is_new_user = False
            label = f"Standard Strategy (Catchup {days_away}d)"
            logger.info(f"👥 User {user_id}: DaysAway={days_away}d ➔ Strategy: [{label}]")

            return is_new_user, days_away, label

        except Exception as e:
            logger.warning(f"Error classifying user {user_id}: {e}")
            return False, Config.OLD_USER_FRESHNESS_DAYS, "Standard Strategy"

    def get_candidate_feeds(
        self,
        user_id: str,
        is_new_user: bool,
        days_away: int,
        blacklist: set,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch candidate feeds with fast in-memory caching and lean projection.
        """
        try:
            now = datetime.utcnow()

            # Fast in-memory feed pool cache (60s TTL)
            if (
                UserRecencyStaggerEngine._feed_pool_cache
                and UserRecencyStaggerEngine._feed_pool_cached_at
                and (now - UserRecencyStaggerEngine._feed_pool_cached_at).total_seconds() < 60
            ):
                all_candidates = UserRecencyStaggerEngine._feed_pool_cache
            else:
                base_query = {
                    "isApproved": True,
                    "isDeleted": False,
                    "status": {"$in": ["Published", "published"]}
                }
                logger.info("🔄 Refreshing candidate feeds pool from MongoDB with lean projection...")
                all_candidates = self.db.find_many(
                    Config.COLLECTION_FEEDS,
                    base_query,
                    projection=FEED_PROJECTION,
                    limit=2000,
                    sort=[("createdAt", -1)]
                )
                UserRecencyStaggerEngine._feed_pool_cache = all_candidates
                UserRecencyStaggerEngine._feed_pool_cached_at = now
                logger.info(f"✅ Cached {len(all_candidates)} candidate feeds in memory")

            if not is_new_user:
                # Old User Catchup
                catchup_start = now - timedelta(days=days_away)
                candidates = [
                    f for f in all_candidates
                    if str(f.get("_id")) not in blacklist
                    and f.get("createdAt") and f["createdAt"] >= catchup_start
                ]

                if len(candidates) < limit:
                    # Fallback to any unviewed feeds in pool
                    for f in all_candidates:
                        fid = str(f.get("_id"))
                        if fid not in blacklist and not any(str(x.get("_id")) == fid for x in candidates):
                            candidates.append(f)
                            if len(candidates) >= limit * 3:
                                break

                return candidates

            else:
                # New User Backlog (80% 15-90d / 20% fresh)
                backlog_start = now - timedelta(days=Config.BACKLOG_MAX_DAYS)
                backlog_end = now - timedelta(days=Config.BACKLOG_MIN_DAYS)
                fresh_start = now - timedelta(days=3)

                backlog = [
                    f for f in all_candidates
                    if str(f.get("_id")) not in blacklist
                    and f.get("createdAt") and backlog_start <= f["createdAt"] <= backlog_end
                ]
                fresh = [
                    f for f in all_candidates
                    if str(f.get("_id")) not in blacklist
                    and f.get("createdAt") and f["createdAt"] >= fresh_start
                ]

                target_backlog = int(limit * Config.NEW_USER_BACKLOG_RATIO)
                target_fresh = limit - target_backlog

                combined = backlog[:target_backlog * 3] + fresh[:target_fresh * 3]
                if not combined:
                    combined = [f for f in all_candidates if str(f.get("_id")) not in blacklist][:limit * 3]

                return combined

        except Exception as e:
            logger.error(f"Error fetching candidate feeds in UserRecencyStaggerEngine: {e}")
            raise OptimizerException(
                "Failed to fetch recency candidate feeds",
                details={"error": str(e)}
            )
