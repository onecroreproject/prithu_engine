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
from app.database.redis_cache import get_redis_manager
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
        self.redis = get_redis_manager()

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

    def _calculate_freshness_score(self, feed: Dict[str, Any], current_date: datetime) -> float:
        """Calculate freshness score based on createdAt date."""
        try:
            created_at = feed.get("createdAt")
            if not isinstance(created_at, datetime):
                return 0.0
            
            hours_old = (current_date - created_at).total_seconds() / 3600.0
            if hours_old <= 48:
                return 30.0  # Massive boost for videos under 48 hours old
            elif hours_old <= 168: # 1 week
                return max(0.0, 30.0 - ((hours_old - 48) / 4))
            else:
                return 0.0
        except Exception:
            return 0.0

    def _calculate_engagement_score(self, feed: Dict[str, Any]) -> float:
        """Calculate engagement score based on percentageWatched and scrollStopDuration."""
        try:
            # The backend aggregates the UserFeedAnalytics into Feeds, or we use raw fields
            pct_watched = feed.get("playbackStats", {}).get("completionRate", 0)
            if pct_watched == 0:
                pct_watched = feed.get("percentageWatched", 0)
                
            scroll_duration = feed.get("engagementStats", {}).get("scrollStopDuration", 0)
            if scroll_duration == 0:
                scroll_duration = feed.get("scrollStopDuration", 0)
            
            score = 0.0
            if pct_watched > 0:
                score += min(40.0, (pct_watched / 100.0) * 40.0)
            
            # For images, 3 seconds = 3000ms = great engagement
            if scroll_duration > 3000:
                score += 40.0
            elif scroll_duration > 1000:
                score += 20.0
                
            return score
        except Exception:
            return 0.0

    def _calculate_ml_quality_score(self, feed: Dict[str, Any]) -> float:
        """Calculate score based on ML confidence."""
        try:
            confidence = feed.get("mlMetadata", {}).get("confidenceScore", 0.0)
            return min(30.0, confidence * 30.0)
        except Exception:
            return 0.0

    def _calculate_social_proof_score(self, feed: Dict[str, Any], total_views_max: float, total_likes_max: float) -> float:
        """Calculate basic trending score for social proof."""
        try:
            v_max = max(1.0, total_views_max)
            views = feed.get("total_views", feed.get("playbackStats", {}).get("totalViews", 0))
            return min(10.0, (views / v_max) * 10.0)
        except Exception:
            return 0.0

    def calculate_final_score(
        self,
        feed: Dict[str, Any],
        current_date: datetime,
        total_views_max: float,
        total_likes_max: float
    ) -> ScoringMetrics:
        """Calculate final recommendation score using the 4-Pillar Formula."""
        try:
            engagement_score = self._calculate_engagement_score(feed)
            ml_quality_score = self._calculate_ml_quality_score(feed)
            freshness_score = self._calculate_freshness_score(feed, current_date)
            social_proof_score = self._calculate_social_proof_score(feed, total_views_max, total_likes_max)

            # The 4-Pillar Perfect Formula
            # 1. True Engagement (40%)
            # 2. ML Quality (30%)
            # 3. Freshness (20%)
            # 4. Social Proof (10%)
            final_score = engagement_score + ml_quality_score + freshness_score + social_proof_score

            final_score = min(100.0, final_score)

            reasons = []
            if freshness_score >= 20:
                reasons.append(f"Fresh Content (+{round(freshness_score,1)})")
            if engagement_score >= 20:
                reasons.append(f"High Engagement (+{round(engagement_score,1)})")
            if ml_quality_score >= 20:
                reasons.append(f"High Quality Match (+{round(ml_quality_score,1)})")

            return ScoringMetrics(
                feed_id=str(feed.get("_id")),
                festival_score=freshness_score, # repurposing legacy field for debug tracking
                trending_score=engagement_score,
                push_score=ml_quality_score,
                time_relevance_score=social_proof_score,
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
            # Limit Enforcement: Max 30 PER DAY
            if section.lower() == "special_day":
                target_limit = max(limit, 100)  # Return all active special day posts
            else:
                # Instead of standard limit, we cap at max 30 per request
                target_limit = min(limit, 30)

            # Generate cache key
            cache_key = f"recs:{user_id}:{target_limit}:{section}:{prefer_short}:{language}:{category_id}:{sub_category}"
            if diversity_boost:
                cache_key += ":div"
            
            # Try to get from cache
            cached_result = self.redis.get(cache_key)
            if cached_result:
                logger.info(f"🎯 Returning cached recommendations for user {user_id}")
                return [FeedRecommendation(**item) for item in cached_result]

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

            active_session = self.session_optimizer.get_current_session_from_db(india_time.hour)
            
            # Apply Strict Allocation Filter (Session: 3-6, God: 2-3, Others: 20-25)
            if diversity_boost:
                scored_feeds = self._apply_strict_feed_allocation(scored_feeds, active_session)

            # Apply Strict GLOBAL Daily Cap (30 feeds total across all categories per day)
            scored_feeds = self._enforce_daily_global_limit(user_id, scored_feeds, daily_limit=30)

            result = scored_feeds[:target_limit]
            
            # Cache the result for 5 minutes (300 seconds)
            self.redis.set(cache_key, [r.dict() for r in result], ttl=300)

            logger.info(f"✅ Delivered {len(result)} [{user_strategy_label}] recommendations [Section: '{section}'] to user {user_id}")
            return result

        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}")
            raise OptimizerException(
                f"Failed to generate recommendations for user {user_id}",
                details={"error": str(e)}
            )

    def _apply_strict_feed_allocation(
        self,
        scored_feeds: List[FeedRecommendation],
        active_session: str
    ) -> List[FeedRecommendation]:
        """
        Build a strictly balanced feed allocation for the 30-post daily quota:
        - Sessions: Morning (2), Afternoon (2), Evening (2), Night (2)
        - God (Today's Deity): 2 to 3 posts
        - Other categories: fill the rest (~19 to 20 posts)
        - Cap at 1 or 2 per category (God exception: up to 3).
        """
        try:
            god_posts = []
            
            # Track posts for all 4 distinct sessions
            session_buckets = {
                "Morning": [],
                "Afternoon": [],
                "Evening": [],
                "Night": []
            }
            
            other_posts = []
            
            current_weekday = datetime.utcnow().weekday()
            active_god_keywords = self.god_optimizer.get_todays_god_keywords_from_db(current_weekday)
            
            category_counts = defaultdict(int)

            for rec in scored_feeds:
                cat_lower = rec.category.lower().strip()
                
                # Check if God post
                is_god = False
                if cat_lower in ["god", "god quotes", "devotional", "bhakti", "spiritual"] or any(k in cat_lower for k in active_god_keywords):
                    is_god = True
                    
                # Check if Session post (and which one)
                post_session_name = None
                for sess_name, keywords in self.session_optimizer.SESSION_KEYWORDS.items():
                    if any(k in cat_lower for k in keywords):
                        post_session_name = sess_name
                        break
                
                if post_session_name:
                    # Allocate strictly 2 per session
                    if len(session_buckets[post_session_name]) < 2 and category_counts[rec.category] < 2:
                        session_buckets[post_session_name].append(rec)
                        category_counts[rec.category] += 1
                elif is_god:
                    if len(god_posts) < 3 and category_counts[rec.category] < 3:
                        god_posts.append(rec)
                        category_counts[rec.category] += 1
                else:
                    if category_counts[rec.category] < 2:
                        other_posts.append(rec)
                        category_counts[rec.category] += 1
            
            # Combine all session posts (exactly 2 from each, if available)
            final_session = []
            for sess_name in ["Morning", "Afternoon", "Evening", "Night"]:
                final_session.extend(session_buckets[sess_name][:2])
                
            final_god = god_posts[:3]
            
            remaining_slots = 30 - len(final_session) - len(final_god)
            final_other = other_posts[:remaining_slots]
            
            final_feed = []
            final_feed.extend(final_session)
            final_feed.extend(final_god)
            final_feed.extend(final_other)
            
            # Re-sort the combined allocation by score to interleave them nicely
            final_feed.sort(key=lambda x: x.score, reverse=True)
            
            return final_feed
        except Exception as e:
            logger.error(f"Failed strict allocation: {e}")
            return scored_feeds

    def _enforce_daily_global_limit(
        self,
        user_id: str,
        recommendations: List[FeedRecommendation],
        daily_limit: int = 30
    ) -> List[FeedRecommendation]:
        """
        Enforce a strict daily cap (e.g. 30 feeds TOTAL) across all categories per user.
        Tracks unique served feed IDs in a Redis Set.
        """
        try:
            if not getattr(self.redis, 'enabled', False) or not getattr(self.redis, 'client', None):
                return recommendations

            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            redis_key = f"daily_global_cap:{user_id}:{today_str}"
            
            # Get the number of unique feeds already served today
            current_served = self.redis.client.scard(redis_key)
            if current_served >= daily_limit:
                # Limit reached for today, return empty list (no more refreshing)
                return []
            
            filtered = []
            new_feed_ids = []

            for rec in recommendations:
                # Check if this specific feed was already allocated to them today
                is_member = self.redis.client.sismember(redis_key, rec.feed_id)
                
                if is_member:
                    # They are refreshing, and this feed was already part of their daily quota, so allow it
                    filtered.append(rec)
                else:
                    # This is a brand new feed attempting to be served today
                    if (current_served + len(new_feed_ids)) < daily_limit:
                        filtered.append(rec)
                        new_feed_ids.append(rec.feed_id)
                    
            # Update Redis with the newly served feed IDs
            if new_feed_ids:
                self.redis.client.sadd(redis_key, *new_feed_ids)
                # Ensure the key expires after 24 hours (86400 seconds)
                self.redis.client.expire(redis_key, 86400)
                
            return filtered
        except Exception as e:
            logger.error(f"Failed to enforce daily global limit: {e}")
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
