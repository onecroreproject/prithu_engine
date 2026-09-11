# ============================================================================
# PRITHU BACKEND - CONFIGURATION MODULE
# ============================================================================
# Manages all environment configuration and constants
# ============================================================================

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """
    Application configuration class.
    Loads settings from environment variables with fallbacks.
    """

    # ========================================================================
    # DATABASE CONFIGURATION
    # ========================================================================

    MONGODB_URI: str = os.getenv(
        "PRITHU_DB_URI",
        "mongodb+srv://prithuapp_db_user:eETUIeouSRU7Xipu@cluster0.x0vkq8e.mongodb.net/Prithu-DB?retryWrites=true&w=majority&appName=Cluster0"
    )

    MONGODB_DATABASE: str = os.getenv(
        "PRITHU_DB_NAME",
        "Prithu-DB"
    )

    MONGODB_TIMEOUT: int = int(
        os.getenv("MONGODB_TIMEOUT", "10000")
    )

    # ========================================================================
    # REDIS CONFIGURATION
    # ========================================================================

    REDIS_HOST: str = os.getenv(
        "REDIS_HOST",
        "127.0.0.1"
    )

    REDIS_PORT: int = int(
        os.getenv("REDIS_PORT", "6379")
    )

    REDIS_DB: int = int(
        os.getenv("REDIS_DB", "0")
    )

    REDIS_TIMEOUT: int = int(
        os.getenv("REDIS_TIMEOUT", "5")
    )

    # ========================================================================
    # APPLICATION CONFIGURATION
    # ========================================================================

    APP_NAME: str = "Prithu Recommendation Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ========================================================================
    # RECOMMENDATION ENGINE CONFIGURATION
    # ========================================================================

    # Daily feed constraints
    DAILY_FEED_MAX: int = 20
    FEEDS_PER_SLOT: int = 5
    TIME_SLOTS: list = ["Morning", "Afternoon", "Evening", "Night"]

    # Recommendation limits
    MIN_RECOMMENDATIONS: int = 5
    MAX_RECOMMENDATIONS: int = 100
    DEFAULT_RECOMMENDATION_LIMIT: int = 20

    # Caching configuration
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL", "3600"))
    CACHE_KEY_PREFIX: str = "prithu:reco:"

    # ========================================================================
    # MONGODB COLLECTION NAMES
    # ========================================================================

    COLLECTION_CATEGORIES = "Categories"
    COLLECTION_BLOGS = "Blogs"
    COLLECTION_FEEDS = "Feeds"
    COLLECTION_USERS = "Users"
    COLLECTION_USER_FEED_ANALYTICS = "UserFeedAnalytics"
    COLLECTION_USER_SEEN_HISTORY = "UserSeenHistory"
    COLLECTION_DAILY_FEEDS = "DailyFeeds"
    COLLECTION_TIME_SLOTS = "TimeSlots"
    COLLECTION_GOD_CONFIG = "GodConfig"

    # ========================================================================
    # LOGGING CONFIGURATION
    # ========================================================================

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

    # ========================================================================
    # USER RECENCY & FEED STAGGERING STRATEGY
    # ========================================================================

    NEW_USER_AGE_DAYS: int = 14            # Accounts <= 14 days old are classified as New Users
    OLD_USER_FRESHNESS_DAYS: int = 3       # Old users prioritize content from the last 3 days (admin uploads)
    BACKLOG_MIN_DAYS: int = 15             # New users start receiving content at least 15 days old
    BACKLOG_MAX_DAYS: int = 90             # New users receive historical backlog up to 90 days old
    NEW_USER_BACKLOG_RATIO: float = 0.80   # 80% backlog, 20% fresh content for new users
    FRESHNESS_BOOST_MAX: float = 2.5       # Maximum multiplier for fresh uploads (today's posts)

    # ========================================================================
    # SCORING WEIGHTS
    # ========================================================================

    WEIGHT_FESTIVAL: float = 0.40
    WEIGHT_TRENDING: float = 0.30
    WEIGHT_PUSH: float = 0.30

    # Interaction weights for UserFeedAnalytics
    INTERACTION_WEIGHTS = {
        "liked": 8,
        "saved": 15,
        "shared": 12,
        "commented": 10,
        "watch_full": 10,      # >= 90% watched
        "rewatch": 15,
        "profile_visit": 5,
        "quick_skip": -10,
        "not_interested": -25,
        "repeated_ignore": -20,
    }

    # ========================================================================
    # VALIDATION CONFIGURATION
    # ========================================================================

    VALID_POST_TYPES = ["image", "video", "image+audio"]
    VALID_UPLOAD_MODES = ["normal", "template"]

    # ========================================================================
    # CLASS METHODS
    # ========================================================================

    @classmethod
    def validate(cls) -> bool:
        """
        Validate critical configuration settings.

        Returns:
            bool: True if configuration is valid, raises exception otherwise.
        """
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is not configured")

        if not cls.MONGODB_DATABASE:
            raise ValueError("MONGODB_DATABASE is not configured")

        return True

    @classmethod
    def to_dict(cls) -> dict:
        """
        Convert configuration to dictionary (excluding sensitive data).

        Returns:
            dict: Configuration as dictionary.
        """
        return {
            k: v for k, v in cls.__dict__.items()
            if not k.startswith("_") and k.isupper()
            and not any(x in k for x in ["PASSWORD", "SECRET", "TOKEN", "URI"])
        }


# Validate configuration on module import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️ Configuration Error: {e}")
    raise
