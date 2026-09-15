# ============================================================================
# PRITHU BACKEND - USER PREFERENCE & ALTERNATIVE SUBSTITUTION OPTIMIZER
# ============================================================================
# Handles non-interested category filtering, alternative category substitution,
# and interaction signal scoring (watch time, likes, shares, saves, skips).
# ============================================================================

from typing import List, Dict, Any, Set
from bson import ObjectId
from collections import defaultdict

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.core.logger_setup import get_logger
from app.exceptions import OptimizerException

from datetime import datetime, timedelta

logger = get_logger(__name__)


class UserPreferenceOptimizer:
    """
    Sub-Optimizer responsible for user preference modeling:
    1. Reads nonInterestedCategories from UserCategorys collection and hard-filters them out.
    2. Performs Alternative Substitution: Replaces filtered-out categories with user's top-preferred or trending categories so daily feed count (20-30) is maintained.
    3. Scores engagement signals from UserFeedAnalytics (watch time, completion rate, likes, shares, saves, skips).
    """
    _non_interested_cache: Dict[str, Any] = {}
    _affinity_cache: Dict[str, Any] = {}

    def __init__(self):
        self.db = get_db_manager()

    def get_non_interested_categories(self, user_id: str) -> Set[str]:
        """
        Fetch category ObjectIds marked as 'Not Interested' by the user with caching.
        """
        now = datetime.utcnow()
        if user_id in self._non_interested_cache:
            cached_at, non_int = self._non_interested_cache[user_id]
            if (now - cached_at).total_seconds() < 60:
                return non_int

        try:
            user_filter = {}
            if ObjectId.is_valid(user_id):
                user_filter = {"$or": [{"userId": ObjectId(user_id)}, {"userId": user_id}]}
            else:
                user_filter = {"userId": user_id}

            record = self.db.find_one("UserCategorys", user_filter, projection={"nonInterestedCategories": 1})
            if not record:
                self._non_interested_cache[user_id] = (now, set())
                return set()

            raw_list = record.get("nonInterestedCategories", [])
            non_interested = {str(cid) for cid in raw_list}

            self._non_interested_cache[user_id] = (now, non_interested)
            logger.debug(f"🚫 User {user_id} has {len(non_interested)} non-interested categories")
            return non_interested

        except Exception as e:
            logger.warning(f"Error fetching non-interested categories for user {user_id}: {e}")
            return set()

    def calculate_user_category_affinity(self, user_id: str) -> Dict[str, float]:
        """
        Calculate category interest scores for user based on UserFeedAnalytics history with caching.
        """
        now = datetime.utcnow()
        if user_id in self._affinity_cache:
            cached_at, aff = self._affinity_cache[user_id]
            if (now - cached_at).total_seconds() < 60:
                return aff

        try:
            user_filter = {}
            if ObjectId.is_valid(user_id):
                user_filter = {"$or": [{"userId": ObjectId(user_id)}, {"userId": user_id}]}
            else:
                user_filter = {"userId": user_id}

            analytics = self.db.find_many(
                Config.COLLECTION_USER_FEED_ANALYTICS,
                user_filter,
                projection={
                    "feedId": 1, "liked": 1, "saved": 1, "shared": 1,
                    "commented": 1, "percentageWatched": 1, "skipped": 1,
                    "replayCount": 1, "notInterested": 1
                },
                limit=300
            )

            weights = Config.INTERACTION_WEIGHTS
            category_scores = defaultdict(float)

            for item in analytics:
                feed_id = item.get("feedId")
                if not feed_id:
                    continue

                # Compute item engagement score
                item_score = 0.0
                if item.get("liked"): item_score += weights.get("liked", 8)
                if item.get("saved"): item_score += weights.get("saved", 15)
                if item.get("shared"): item_score += weights.get("shared", 12)
                if item.get("commented"): item_score += weights.get("commented", 10)

                # Watch time signals
                pct_watched = item.get("percentageWatched", 0)
                if pct_watched >= 90:
                    item_score += weights.get("watch_full", 10)
                elif pct_watched < 20 and item.get("skipped"):
                    item_score += weights.get("quick_skip", -10)

                if item.get("replayCount", 0) > 0:
                    item_score += weights.get("rewatch", 15)

                if item.get("notInterested"):
                    item_score += weights.get("not_interested", -25)

                feed_doc = self.db.find_one(Config.COLLECTION_FEEDS, {"_id": feed_id}, projection={"category": 1})
                if feed_doc:
                    cats = feed_doc.get("category", [])
                    if isinstance(cats, list) and cats:
                        cat_id = str(cats[0])
                        category_scores[cat_id] += item_score

            return category_scores

        except Exception as e:
            logger.warning(f"Error calculating category affinity for user {user_id}: {e}")
            return {}

    def apply_preference_and_substitution_filter(
        self,
        candidates: List[Dict[str, Any]],
        all_feeds_pool: List[Dict[str, Any]],
        user_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Filter out non-interested categories and substitute with alternative categories user enjoys
        or trending items to ensure full quota (limit) is reached.

        Args:
            candidates: Primary candidate feed documents
            all_feeds_pool: Broader pool of available feeds for substitution
            user_id: User identifier
            limit: Quota target count (e.g. 20-30)

        Returns:
            Filtered and substituted candidate feeds
        """
        try:
            non_interested_cats = self.get_non_interested_categories(user_id)

            if not non_interested_cats:
                return candidates

            # 1. Filter out non-interested categories
            filtered = []
            excluded_count = 0

            for feed in candidates:
                raw_cat = feed.get("category", [])
                cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)

                if cat_id in non_interested_cats:
                    excluded_count += 1
                else:
                    filtered.append(feed)

            logger.info(
                f"🚫 User Preference Filter for {user_id}: Excluded {excluded_count} feeds matching non-interested categories. "
                f"Remaining: {len(filtered)}"
            )

            # 2. Alternative Substitution: If filtered candidates < required limit, substitute with alternative categories
            if len(filtered) < limit:
                needed = limit - len(filtered)
                logger.info(f"🔄 Alternative Category Substitution: Need {needed} alternative feeds for user {user_id}")

                affinity_scores = self.calculate_user_category_affinity(user_id)
                existing_ids = {str(f.get("_id")) for f in filtered}

                # Sort pool candidates by user affinity & engagement
                substitutes = []
                for f in all_feeds_pool:
                    fid = str(f.get("_id"))
                    if fid in existing_ids:
                        continue

                    raw_cat = f.get("category", [])
                    cat_id = str(raw_cat[0]) if isinstance(raw_cat, list) and raw_cat else str(raw_cat)

                    if cat_id not in non_interested_cats:
                        substitutes.append((f, affinity_scores.get(cat_id, 0.0)))

                substitutes.sort(key=lambda x: x[1], reverse=True)

                for f, score in substitutes:
                    filtered.append(f)
                    if len(filtered) >= limit * 2:
                        break

                logger.info(f"✅ Alternative Substitution Complete: Total candidates restored to {len(filtered)}")

            return filtered

        except Exception as e:
            logger.error(f"Error in UserPreferenceOptimizer for user {user_id}: {e}")
            raise OptimizerException(
                "Failed to apply user preference filter",
                details={"error": str(e)}
            )
