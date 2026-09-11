# ============================================================================
# PRITHU BACKEND - DATA MODELS
# ============================================================================
# Pydantic models for input/output validation and serialization
# ============================================================================

from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# INPUT MODELS (From Node.js Backend)
# ============================================================================

class RecommendationRequest(BaseModel):
    """
    Request model for getting recommendations.
    Supports both camelCase (Node.js style) and snake_case (Python style) inputs.
    """

    user_id: str = Field(
        ...,
        min_length=1,
        validation_alias="userId",
        alias="user_id",
        description="User identifier"
    )

    exclude_ids: List[str] = Field(
        default=[],
        validation_alias="excludeIds",
        alias="exclude_ids",
        description="Feed IDs to exclude from recommendations"
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of recommendations"
    )

    diversity_boost: bool = Field(
        default=False,
        validation_alias="diversityBoost",
        alias="diversity_boost",
        description="Apply diversity filter across categories"
    )

    prefer_short: bool = Field(
        default=False,
        validation_alias="preferShort",
        alias="prefer_short",
        description="Prefer short-duration videos"
    )

    section: str = Field(
        default="all",
        validation_alias="section",
        alias="section",
        description="Target tab section: 'all', 'special_day', 'god', 'general'"
    )

    language: Optional[str] = Field(
        default=None,
        validation_alias="language",
        alias="language",
        description="Language filter: 'ta', 'en', 'both'"
    )

    gender: Optional[str] = Field(
        default=None,
        validation_alias="gender",
        alias="gender",
        description="User gender: 'male', 'female', 'other'"
    )

    category_id: Optional[str] = Field(
        default=None,
        validation_alias="categoryId",
        alias="category_id",
        description="Specific category ObjectId filter"
    )

    sub_category: Optional[str] = Field(
        default=None,
        validation_alias="subCategory",
        alias="sub_category",
        description="Specific subcategory filter"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """Validate user_id is not empty."""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class FeedAnalysisRequest(BaseModel):
    """
    Request model for analyzing feed content.
    Supports both camelCase and snake_case inputs.
    """

    feed_id: str = Field(
        ...,
        min_length=1,
        validation_alias="feedId",
        alias="feed_id",
        description="Feed identifier"
    )

    category: List[str] = Field(
        default=[],
        description="Category ObjectIds"
    )

    caption: str = Field(
        default="",
        description="Feed caption"
    )

    hashtags: List[str] = Field(
        default=[],
        description="Feed hashtags"
    )

    post_type: str = Field(
        default="image",
        validation_alias="postType",
        alias="post_type",
        description="Post type: image, video, image+audio"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True
    )


# ============================================================================
# OUTPUT MODELS (Response to Node.js)
# ============================================================================

class FeedRecommendation(BaseModel):
    """Single feed recommendation."""

    feed_id: str
    category: str
    score: float = Field(ge=0, le=100)
    reason: str
    metadata: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    """
    Response model for recommendation requests.

    Attributes:
        success: Request was successful
        user_id: User for which recommendations were generated
        recommended_feeds: List of recommended feeds
        total_count: Number of recommendations returned
        engine_status: Status of recommendation engine
        timestamp: Response timestamp
        metadata: Additional metadata
    """

    success: bool
    user_id: str
    recommended_feeds: List[FeedRecommendation]
    total_count: int
    engine_status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class FeedAnalysisResult(BaseModel):
    """Result of feed content analysis."""

    feed_id: str
    content_type: str
    sub_category: str
    emotion: str
    topics: List[str]
    recommendation_tags: List[str]
    auto_keywords: List[str]
    generated_hashtags: List[str]
    confidence_score: float = Field(ge=0, le=1)

    model_config = ConfigDict(from_attributes=True)


class AnalysisResponse(BaseModel):
    """
    Response model for feed analysis.

    Attributes:
        success: Request was successful
        feed_id: Feed being analyzed
        analysis: Analysis results
        timestamp: Response timestamp
    """

    success: bool
    feed_id: str
    analysis: FeedAnalysisResult
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """
    Standard error response model.

    Attributes:
        success: False
        error: Error details
        data: Additional error context
    """

    success: bool = False
    error: dict
    data: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)


class TrackInteractionRequest(BaseModel):
    """
    Request schema for recording user interactions for ML/DL model training dataset.
    Supports both camelCase and snake_case inputs.
    """

    user_id: str = Field(..., validation_alias="userId", alias="user_id", min_length=1)
    feed_id: str = Field(..., validation_alias="feedId", alias="feed_id", min_length=1)
    session_id: Optional[str] = Field(default="main_session", validation_alias="sessionId", alias="session_id")
    watch_time: float = Field(default=0.0, validation_alias="watchTime", alias="watch_time")
    percentage_watched: float = Field(default=0.0, validation_alias="percentageWatched", alias="percentage_watched")
    replay_count: int = Field(default=0, validation_alias="replayCount", alias="replay_count")
    pause_count: int = Field(default=0, validation_alias="pauseCount", alias="pause_count")
    device_type: Optional[str] = Field(default="mobile", validation_alias="deviceType", alias="device_type")
    gender: Optional[str] = Field(default=None, description="User gender: male, female, other")
    language: Optional[str] = Field(default="en")

    liked: bool = Field(default=False)
    saved: bool = Field(default=False)
    shared: bool = Field(default=False)
    commented: bool = Field(default=False)
    not_interested: bool = Field(default=False, validation_alias="notInterested", alias="not_interested")
    skipped: bool = Field(default=False)

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)


class TrackInteractionResponse(BaseModel):
    """Response schema for interaction tracking."""

    success: bool
    message: str
    record_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""

    status: str
    database: bool
    cache: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INTERNAL MODELS (For internal use)
# ============================================================================

class CategoryMetadata(BaseModel):
    """Category information."""

    id: str
    name: str
    feed_count: int = 0
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """User profile information."""

    user_id: str
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    preferences: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class ScoringMetrics(BaseModel):
    """Scoring metrics for a feed."""

    feed_id: str
    festival_score: float = 0.0
    trending_score: float = 0.0
    push_score: float = 0.0
    time_relevance_score: float = 0.0
    final_score: float = 0.0
    reasons: List[str] = []

    model_config = ConfigDict(from_attributes=True)
