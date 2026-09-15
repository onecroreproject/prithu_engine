# ============================================================================
# PRITHU BACKEND - LIFETIME SEEN FILTER
# ============================================================================
# Ensures users NEVER see the same video or image twice in their lifetime
# ============================================================================

from typing import List, Dict, Any, Set
from bson import ObjectId

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

from datetime import datetime, timedelta

logger = get_logger(__name__)


class LifetimeSeenFilter:
    """
    Sub-Optimizer responsible for permanent, lifetime exclusion of viewed content.
    Queries UserSeenHistory collection and merges with explicit exclude_ids.
    """
    _seen_cache: Dict[str, Any] = {}

    def __init__(self):
        self.db = get_db_manager()

    def get_seen_feed_ids(self, user_id: str) -> Set[str]:
        """
        Fetch all feed IDs ever viewed by user from UserSeenHistory collection with caching.
        """
        now = datetime.utcnow()
        if user_id in self._seen_cache:
            cached_at, seen_set = self._seen_cache[user_id]
            if (now - cached_at).total_seconds() < 60:
                return seen_set

        try:
            user_filter = {}
            if ObjectId.is_valid(user_id):
                user_filter = {"$or": [{"userId": ObjectId(user_id)}, {"userId": user_id}]}
            else:
                user_filter = {"userId": user_id}

            records = self.db.find_many(
                Config.COLLECTION_USER_SEEN_HISTORY,
                user_filter,
                projection={"feedId": 1, "contentId": 1},
                limit=3000
            )

            seen_ids = set()
            for r in records:
                fid = r.get("feedId") or r.get("contentId")
                if fid:
                    seen_ids.add(str(fid))

            self._seen_cache[user_id] = (now, seen_ids)
            logger.debug(f"🔍 User {user_id} has seen {len(seen_ids)} feeds in lifetime")
            return seen_ids

        except Exception as e:
            logger.warning(f"Error fetching lifetime seen history for user {user_id}: {e}")
            return set()

    def filter_unseen_candidates(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        exclude_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter candidates to return ONLY feeds never seen by user in their lifetime.

        Args:
            user_id: User identifier
            candidates: List of feed documents
            exclude_ids: Additional feed IDs from client request

        Returns:
            List of unseen candidate feed documents
        """
        try:
            seen_ids = self.get_seen_feed_ids(user_id)
            blacklist = seen_ids.union(set(exclude_ids or []))

            unseen = [
                f for f in candidates
                if str(f.get("_id")) not in blacklist
            ]

            logger.info(f"🛡️ Lifetime Filter for User {user_id}: {len(candidates)} candidates -> {len(unseen)} unseen feeds remaining")
            return unseen

        except Exception as e:
            logger.error(f"Error in LifetimeSeenFilter for user {user_id}: {e}")
            raise OptimizerException(
                "Failed to apply lifetime seen filter",
                details={"user_id": user_id, "error": str(e)}
            )
