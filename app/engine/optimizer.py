# ============================================================================
# PRITHU BACKEND - RECOMMENDATION OPTIMIZER (FACADE)
# ============================================================================
# Main Recommendation Facade coordinating all modular sub-optimizers
# ============================================================================

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.config import Config
from app.database.db_connection import get_db_manager
from app.models.schemas import (
    FeedRecommendation,
    ScoringMetrics,
    CategoryMetadata
)
from app.exceptions import (
    OptimizerException,
    ScoringException,
    ErrorCode
)
from app.core.logger_setup import get_logger

# Import Modular Sub-Optimizers
from app.engine.lifetime_filter import LifetimeSeenFilter
from app.engine.session_optimizer import SessionTimeSlotOptimizer
from app.engine.recency_engine import UserRecencyStaggerEngine
from app.engine.special_day_optimizer import SpecialDayOptimizer
from app.engine.god_optimizer import GodCategoryOptimizer
from app.engine.user_preference_optimizer import UserPreferenceOptimizer

logger = get_logger(__name__)


class CategoryOptimizer:
    """
    Main Recommendation Optimizer Facade.

    Coordinates modular sub-engine components:
    1. LifetimeSeenFilter: Ensures 100% lifetime exclusion of viewed content.
    2. UserRecencyStaggerEngine: Old User catch-up vs New User historical backlog.
    3. UserPreferenceOptimizer: Non-interested category filtering & alternative category substitution.
    4. SpecialDayOptimizer: 24-hour active window & midnight expiry for Special Days (NO daily limit).
    5. GodCategoryOptimizer: 24-hour Day-of-Week God Schedule (Monday-Sunday deities).
    6. SessionTimeSlotOptimizer: Enforces Morning/Afternoon/Evening/Night session boundaries.
    """

    def __init__(self):
        """Initialize facade and sub-optimizers."""
        self.db = get_db_manager()
        self.lifetime_filter = LifetimeSeenFilter()
        self.recency_engine = UserRecencyStaggerEngine()
        self.preference_optimizer = UserPreferenceOptimizer()
        self.special_day_optimizer = SpecialDayOptimizer()
        self.god_optimizer = GodCategoryOptimizer()
        self.session_optimizer = SessionTimeSlotOptimizer()

        self._category_cache: Dict[str, CategoryMetadata] = {}
        self._category_names_map: Dict[str, str] = {}
        self._last_cache_update: Optional[datetime] = None

    # ========================================================================
    # CATEGORY DYNAMIC LOADING (ZERO HARDCODING)
    # ========================================================================

    def _load_categories(self, force_refresh: bool = False) -> Dict[str, CategoryMetadata]:
        """
        Load categories dynamically from MongoDB.
        No categories are hardcoded in code.

        Returns:
            Dictionary of category ID to CategoryMetadata
        """
        try:
            if (
                not force_refresh
                and self._category_cache
                and self._last_cache_update
                and datetime.utcnow() - self._last_cache_update < timedelta(hours=1)
            ):
                return self._category_cache

            logger.info("Loading categories dynamically from MongoDB...")

            categories = self.db.find_many(
                Config.COLLECTION_CATEGORIES,
                {},
                {"_id": 1, "name": 1, "feedIds": 1}
            )

            self._category_cache = {}
            self._category_names_map = {}

            for cat in categories:
                cat_id = str(cat["_id"])
                cat_name = cat.get("name", "Unknown")
                self._category_cache[cat_id] = CategoryMetadata(
                    id=cat_id,
                    name=cat_name,
                    feed_count=len(cat.get("feedIds", []))
                )
                self._category_names_map[cat_id] = cat_name

            self._last_cache_update = datetime.utcnow()
            logger.info(f"✅ Loaded {len(self._category_cache)} categories dynamically from MongoDB")

            return self._category_cache

        except Exception as e:
            logger.error(f"Failed to load categories: {e}")
            raise OptimizerException(
                "Failed to load categories from database",
                details={"error": str(e)}
            )

    # ========================================================================
    # SCORING METHODS
    # ========================================================================

    def _calculate_trending_score(self, feed: Dict[str, Any], total_views_max: float, total_likes_max: float) -> float:
        """Calculate trending score based on views and likes."""
        try:
            v_max = max(1.0, total_views_max)
            l_max = max(1.0, total_likes_max)

            views = feed.get("total_views", feed.get("playbackStats", {}).get("totalViews", 0))
            likes = feed.get("likes", feed.get("engagementStats", {}).get("likes", 0))

            views_score = (views / v_max) * 40.0
            likes_score = (likes / l_max) * 60.0

            return min(100.0, views_score + likes_score)
        except Exception:
            return 0.0

    def _calculate_push_score(self, feed: Dict[str, Any]) -> float:
        """Calculate push score for high engagement posts."""
        try:
            views = feed.get("total_views", feed.get("playbackStats", {}).get("totalViews", 0))
            likes = feed.get("likes", feed.get("engagementStats", {}).get("likes", 0))
            if views >= 1000 or likes >= 50:
                return 100.0
            return 0.0
        except Exception:
            return 0.0

    def calculate_final_score(
        self,
        feed: Dict[str, Any],
        current_date: datetime,
        total_views_max: float,
        total_likes_max: float
    ) -> ScoringMetrics:
        """Calculate final recommendation score."""
        try:
            push_score = self._calculate_push_score(feed)
            trending_score = self._calculate_trending_score(feed, total_views_max, total_likes_max)

            final_score = (
                (Config.WEIGHT_PUSH * push_score) +
                (Config.WEIGHT_TRENDING * trending_score)
            )

            final_score = min(100.0, final_score)

            reasons = []
            if push_score > 0:
                reasons.append("High engagement")
            if trending_score > 50:
                reasons.append("Trending")

            return ScoringMetrics(
                feed_id=str(feed.get("_id")),
                festival_score=0.0,
                trending_score=round(trending_score, 2),
                push_score=push_score,
                time_relevance_score=0.0,
                final_score=round(final_score, 2),
                reasons=reasons or ["General recommendation"]
            )

        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            raise ScoringException(
                "Failed to calculate score",
                details={"error": str(e), "feed_id": str(feed.get("_id"))}
            )

    # ========================================================================
    # MAIN RECOMMENDATION GENERATION
    # ========================================================================

    def get_recommendations(
        self,
        user_id: str,
        limit: int = Config.DEFAULT_RECOMMENDATION_LIMIT,
        exclude_ids: Optional[List[str]] = None,
        diversity_boost: bool = False,
        prefer_short: bool = False,
        section: str = "all",
        language: Optional[str] = None,
        gender: Optional[str] = None,
        category_id: Optional[str] = None,
        sub_category: Optional[str] = None
    ) -> List[FeedRecommendation]:
        """
        Generate recommendations using all modular sub-optimizers.

        Args:
            user_id: User identifier
            limit: Recommendation count (20-30 for general/all, unlimited for special_day)
            exclude_ids: Feed IDs to exclude
            diversity_boost: Apply category diversity
            prefer_short: Prefer short video content
            section: Section tab ('all', 'special_day', 'god', 'general')
            language: User preferred language ('ta', 'en', 'both')
            gender: User gender ('male', 'female', 'other')
            category_id: Specific category ObjectId filter
            sub_category: Specific subcategory filter

        Returns:
            List of FeedRecommendation objects
        """
        try:
            # Enforce Daily Limit Rules:
            # Special Day Section: EXEMPT from limit (returns all active festival posts, e.g. 50+)
            # General / All Sections: Quota capped at 20-30 items per day.
            if section.lower() == "special_day":
                target_limit = max(limit, 100)  # Return all active special day posts
            else:
                target_limit = min(max(limit, 10), 30)  # Daily quota: 20-30 items

            logger.info(f"🎯 Requesting recommendations for user {user_id} [Section: '{section}', Target Quota: {target_limit}]")

            # 1. Load categories dynamically from MongoDB
            self._load_categories()

            # 2. Get lifetime seen feed IDs (100% Lifetime Exclusion Guarantee)
            seen_ids = self.lifetime_filter.get_seen_feed_ids(user_id)
            blacklist = seen_ids.union(set(exclude_ids or []))

            # 3. Classify User Recency Strategy (Old vs New User)
            is_new_user, days_away, user_strategy_label = self.recency_engine.classify_user(
                user_id, len(seen_ids)
            )

            # 4. Fetch candidate feeds from Recency Engine
            candidates = self.recency_engine.get_candidate_feeds(
                user_id=user_id,
                is_new_user=is_new_user,
                days_away=days_away,
                blacklist=blacklist,
                limit=target_limit * 4
            )

            if not candidates:
                logger.warning(f"No candidate feeds remaining for user {user_id}")
                return []

            # 4b. Filter by Language preference if specified
            if language and language.lower() != "both":
                lang_code = language.lower().strip()
                candidates = [
                    f for f in candidates
                    if str(f.get("language", "en")).lower() in [lang_code, "both"]
                ] or candidates

            # 4c. Filter by Specific Category ID if specified
            if category_id:
                cid_str = str(category_id)
                candidates = [
                    f for f in candidates
                    if cid_str in [str(c) for c in (f.get("category") if isinstance(f.get("category"), list) else [f.get("category")])]
                ] or candidates

            # 4d. Filter by Specific SubCategory if specified
            if sub_category:
                sub_str = str(sub_category).lower().strip()
                candidates = [
                    f for f in candidates
                    if str(f.get("subCategory", "")).lower() == sub_str
                ] or candidates

            india_time = datetime.utcnow() + timedelta(hours=5, minutes=30)

            # 5. Apply User Preference Filter (Non-Interested Exclusion + Alternative Category Substitution)
            candidates = self.preference_optimizer.apply_preference_and_substitution_filter(
                candidates=candidates,
                all_feeds_pool=candidates,
                user_id=user_id,
                limit=target_limit
            )

            # 6. Apply Special Day 24-Hour Active Window & Section Filter
            candidates = self.special_day_optimizer.apply_special_day_filter(
                candidates=candidates,
                categories_map=self._category_names_map,
                current_time=india_time,
                section=section
            )

            # 7. Apply God Category 24-Hour Day-of-Week Schedule Filter
            candidates = self.god_optimizer.apply_god_schedule_filter(
                candidates=candidates,
                categories_map=self._category_names_map,
                current_time=india_time,
                section=section
            )

            # 8. Apply Session Time Slot Hard-Lock Filter (Morning/Afternoon/Evening/Night)
            candidates = self.session_optimizer.apply_session_filter(
                candidates=candidates,
                categories_map=self._category_names_map,
                current_time=india_time
            )

            if not candidates:
                logger.warning(f"No feeds matched active filters for user {user_id}")
                return []

            # 9. Score & Rank Remaining Candidate Feeds
            total_views_max = max([f.get("total_views", 0) for f in candidates]) or 1.0
            total_likes_max = max([f.get("likes", 0) for f in candidates]) or 1.0

            scored_feeds = []
            for feed in candidates:
                try:
                    metrics = self.calculate_final_score(feed, india_time, total_views_max, total_likes_max)
                    score = metrics.final_score

                    if prefer_short and feed.get("duration", 0) > 30:
                        score *= 0.7

                    score = min(100.0, round(score, 2))

                    raw_cat = feed.get("category", "General")
                    if isinstance(raw_cat, list):
                        cat_str = str(raw_cat[0]) if raw_cat else "General"
                    else:
                        cat_str = str(raw_cat)

                    cat_display_name = self._category_names_map.get(cat_str, cat_str)

                    recommendation = FeedRecommendation(
                        feed_id=str(feed.get("_id")),
                        category=cat_display_name,
                        score=score,
                        reason=", ".join(metrics.reasons),
                        metadata={
                            "metrics": metrics.dict(),
                            "user_strategy": user_strategy_label,
                            "section": section,
                            "active_session": self.session_optimizer.get_current_session_from_db(india_time.hour)
                        }
                    )
                    scored_feeds.append(recommendation)

                except ScoringException as e:
                    logger.warning(f"Failed to score feed {feed.get('_id')}: {e}")
                    continue

            # Sort by score descending
            scored_feeds.sort(key=lambda x: x.score, reverse=True)

            # Diversity Filter
            if diversity_boost:
                scored_feeds = self._apply_diversity_filter(scored_feeds, max_per_category=5)

            result = scored_feeds[:target_limit]

            logger.info(f"✅ Delivered {len(result)} [{user_strategy_label}] recommendations [Section: '{section}'] to user {user_id}")
            return result

        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}")
            raise OptimizerException(
                f"Failed to generate recommendations for user {user_id}",
                details={"error": str(e)}
            )

    def _apply_diversity_filter(
        self,
        recommendations: List[FeedRecommendation],
        max_per_category: int = 5
    ) -> List[FeedRecommendation]:
        """Apply diversity filter across categories."""
        try:
            filtered = []
            category_counts = defaultdict(int)

            for rec in recommendations:
                category = rec.category
                if category_counts[category] < max_per_category:
                    filtered.append(rec)
                    category_counts[category] += 1

            return filtered
        except Exception:
            return recommendations

    def health_check(self) -> bool:
        """Check optimizer health status."""
        try:
            return self.db.health_check()
        except Exception:
            return False


# Singleton instance
_optimizer_instance: Optional[CategoryOptimizer] = None


def get_optimizer() -> CategoryOptimizer:
    """Get or create CategoryOptimizer singleton."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = CategoryOptimizer()
    return _optimizer_instance
