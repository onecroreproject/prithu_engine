# ============================================================================
# PRITHU BACKEND - FASTAPI APPLICATION
# ============================================================================
# Main API application for Node.js integration
# Handles recommendation and analysis requests with error handling
# ============================================================================

from contextlib import asynccontextmanager
from datetime import datetime
import traceback

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import Config
from app.core.logger_setup import get_logger
from app.database.db_connection import get_db_manager
from app.engine.optimizer import get_optimizer
from app.models.schemas import (
    RecommendationRequest,
    FeedAnalysisRequest,
    RecommendationResponse,
    AnalysisResponse,
    FeedRecommendation,
    FeedAnalysisResult,
    ErrorResponse,
    HealthCheckResponse,
    TrackInteractionRequest,
    TrackInteractionResponse
)
from app.exceptions import PrithuException, ErrorCode


logger = get_logger(__name__)


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    Yields:
        Control to FastAPI
    """
    # ========================================================================
    # STARTUP
    # ========================================================================

    logger.info("=" * 80)
    logger.info("🚀 PRITHU RECOMMENDATION ENGINE - STARTUP")
    logger.info("=" * 80)

    try:
        # Initialize database
        db = get_db_manager()
        logger.info("✅ Database initialized")

        # Initialize optimizer
        optimizer = get_optimizer()
        if optimizer.health_check():
            logger.info("✅ Optimizer initialized")
        else:
            logger.warning("⚠️ Optimizer health check failed")

        logger.info("=" * 80)
        logger.info(f"📊 Environment: {Config.ENVIRONMENT}")
        logger.info(f"📚 Database: {Config.MONGODB_DATABASE}")
        logger.info(f"✨ Application Ready")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("=" * 80)
        logger.error("❌ STARTUP FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        traceback.print_exc()
        raise

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    logger.info("=" * 80)
    logger.info("🛑 PRITHU RECOMMENDATION ENGINE - SHUTDOWN")
    logger.info("=" * 80)

    try:
        db = get_db_manager()
        db.close()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("=" * 80)


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

app = FastAPI(
    title=Config.APP_NAME,
    version=Config.APP_VERSION,
    lifespan=lifespan
)

# Prometheus Metrics
REQUEST_COUNT = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
REQUEST_LATENCY = Histogram('request_latency_seconds', 'Request latency', ['endpoint'])
RECOMMENDATION_COUNT = Counter('recommendation_count', 'Total recommendations generated', ['section'])

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(PrithuException)
async def prithu_exception_handler(request: Request, exc: PrithuException):
    """Handle custom Prithu exceptions."""
    logger.error(f"Prithu Exception: {exc.message} ({exc.error_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation Error: {exc}")
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            success=False,
            error={
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Input validation failed",
                "details": exc.errors()
            }
        ).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected Error: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error={
                "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": "Internal server error",
                "details": str(exc) if Config.DEBUG else "Unknown error"
            }
        ).model_dump()
    )


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check application health status.

    Returns:
        HealthCheckResponse: Health status
    """
    try:
        db = get_db_manager()
        optimizer = get_optimizer()

        db_healthy = db.health_check()
        optimizer_healthy = optimizer.health_check()

        status = "healthy" if (db_healthy and optimizer_healthy) else "degraded"

        logger.debug(f"Health check: DB={db_healthy}, Optimizer={optimizer_healthy}")

        return HealthCheckResponse(
            status=status,
            database=db_healthy,
            cache=True  # Redis health check can be added later
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            database=False,
            cache=False
        )


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "name": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "recommend": "/api/v1/recommend",
            "analyze": "/api/v1/analyze",
            "docs": "/docs"
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Endpoint for Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ============================================================================
# RECOMMENDATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/recommend", response_model=RecommendationResponse)
@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Get recommendations for a user.

    Called by Node.js backend with user ID and preferences.
    Supports both /api/v1/recommend and legacy /recommend paths.
    """
    try:
        logger.info(f"📥 Recommendation request: user_id={request.user_id}")

        with REQUEST_LATENCY.labels(endpoint='/recommend').time():
            # Get optimizer
            optimizer = get_optimizer()

            # Generate recommendations
            recommendations = optimizer.get_recommendations(
                user_id=request.user_id,
                limit=request.limit,
                exclude_ids=request.exclude_ids,
                diversity_boost=request.diversity_boost,
                prefer_short=request.prefer_short,
                section=request.section,
                language=request.language,
                gender=request.gender,
                category_id=request.category_id,
                sub_category=request.sub_category
            )
            
        RECOMMENDATION_COUNT.labels(section=request.section).inc(len(recommendations))

        # Build response
        response = RecommendationResponse(
            success=True,
            user_id=request.user_id,
            recommended_feeds=recommendations,
            recommended_reels=recommendations,
            total_count=len(recommendations),
            engine_status="online",
            metadata={
                "diversity_boost": request.diversity_boost,
                "prefer_short": request.prefer_short,
                "section": request.section,
                "language": request.language,
                "gender": request.gender,
                "category_id": request.category_id,
                "sub_category": request.sub_category
            }
        )

        logger.info(f"✅ Sent {len(recommendations)} recommendations to {request.user_id}")
        return response

    except PrithuException as e:
        logger.error(f"Recommendation error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    except Exception as e:
        logger.error(f"Unexpected error in /recommend: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                    "message": "Failed to generate recommendations"
                }
            }
        )


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_feed(request: FeedAnalysisRequest):
    """
    Analyze feed content and classify.

    Called by Node.js to get content type, emotion, and recommendations tags.

    Args:
        request: FeedAnalysisRequest

    Returns:
        AnalysisResponse with content classification

    Raises:
        HTTPException: If analysis fails
    """
    try:
        logger.info(f"📥 Analysis request: feed_id={request.feed_id}")

        # Simple content classification (can be extended with ML)
        analysis_result = FeedAnalysisResult(
            feed_id=request.feed_id,
            content_type=_classify_content_type(request.post_type),
            sub_category=_classify_subcategory(request.category, request.caption),
            emotion=_classify_emotion(request.caption, request.hashtags),
            topics=_extract_topics(request.caption, request.hashtags),
            recommendation_tags=_generate_recommendation_tags(
                request.category, request.caption
            ),
            auto_keywords=_generate_keywords(request.caption, request.hashtags),
            generated_hashtags=request.hashtags or [],
            confidence_score=0.85
        )

        response = AnalysisResponse(
            success=True,
            feed_id=request.feed_id,
            analysis=analysis_result,
            metadata=analysis_result
        )

        logger.info(f"✅ Analyzed feed {request.feed_id}")
        return response

    except PrithuException as e:
        logger.error(f"Analysis error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    except Exception as e:
        logger.error(f"Unexpected error in /analyze: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                    "message": "Failed to analyze feed"
                }
            }
        )


# ============================================================================
# INTERACTION & ML DATASET TRACKING ENDPOINT
# ============================================================================

@app.post("/api/v1/track", response_model=TrackInteractionResponse)
@app.post("/track", response_model=TrackInteractionResponse)
async def track_interaction(request: TrackInteractionRequest):
    """
    Log detailed user interactions (likes, comments, shares, watch time, completion, skips, gender, language)
    into MongoDB UserFeedAnalytics collection to construct ML/DL training datasets.
    """
    try:
        from bson import ObjectId

        logger.info(f"📊 Tracking interaction: user={request.user_id}, feed={request.feed_id}")

        db = get_db_manager()
        record_data = {
            "userId": ObjectId(request.user_id) if ObjectId.is_valid(request.user_id) else request.user_id,
            "feedId": ObjectId(request.feed_id) if ObjectId.is_valid(request.feed_id) else request.feed_id,
            "sessionId": request.session_id,
            "watchTime": request.watch_time,
            "percentageWatched": request.percentage_watched,
            "replayCount": request.replay_count,
            "pauseCount": request.pause_count,
            "deviceType": request.device_type,
            "gender": request.gender,
            "language": request.language,
            "liked": request.liked,
            "saved": request.saved,
            "shared": request.shared,
            "commented": request.commented,
            "notInterested": request.not_interested,
            "skipped": request.skipped,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }

        inserted_id = db.insert_one(Config.COLLECTION_USER_FEED_ANALYTICS, record_data)

        # If user marked Not Interested, update UserCategorys document
        if request.not_interested:
            feed_doc = db.find_one(Config.COLLECTION_FEEDS, {"_id": record_data["feedId"]}, projection={"category": 1})
            if feed_doc and feed_doc.get("category"):
                cats = feed_doc.get("category")
                cat_id = cats[0] if isinstance(cats, list) else cats
                db.update_one(
                    "UserCategorys",
                    {"userId": record_data["userId"]},
                    {"$addToSet": {"nonInterestedCategories": cat_id}},
                    upsert=True
                )

        return TrackInteractionResponse(
            success=True,
            message="Interaction tracked successfully for ML training",
            record_id=str(inserted_id)
        )

    except Exception as e:
        logger.error(f"Error tracking interaction: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})


# ============================================================================
# CACHE & ENGINE REFRESH ENDPOINT
# ============================================================================

@app.post("/api/v1/refresh")
@app.post("/refresh")
async def refresh_engine():
    """
    Refresh cache and reload category/festival weights.
    Called periodically by Node.js cron or admin panel.
    """
    try:
        optimizer = get_optimizer()
        optimizer.categories = optimizer._load_categories(force_refresh=True)
        from app.engine.recency_engine import UserRecencyStaggerEngine
        from app.engine.lifetime_filter import LifetimeSeenFilter
        from app.engine.user_preference_optimizer import UserPreferenceOptimizer
        UserRecencyStaggerEngine._feed_pool_cache = []
        UserRecencyStaggerEngine._feed_pool_cached_at = None
        UserRecencyStaggerEngine._user_profile_cache.clear()
        LifetimeSeenFilter._seen_cache.clear()
        UserPreferenceOptimizer._non_interested_cache.clear()
        UserPreferenceOptimizer._affinity_cache.clear()
        logger.info("✅ Cleared all feed pool and user metadata in-memory caches")
        return {"success": True, "message": "ML Engine cache refreshed successfully"}
    except Exception as e:
        logger.error(f"Failed to refresh engine: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# HELPER FUNCTIONS FOR ANALYSIS
# ============================================================================

def _classify_content_type(post_type: str) -> str:
    """Classify content type."""
    type_map = {
        "video": "video",
        "image": "image",
        "image+audio": "multimedia"
    }
    return type_map.get(post_type, "unknown")


def _classify_subcategory(categories: list, caption: str) -> str:
    """Classify subcategory based on categories and caption."""
    if categories:
        return str(categories[0])
    return "general"


def _classify_emotion(caption: str, hashtags: list) -> str:
    """Classify emotion from caption and hashtags."""
    text = (caption + " " + " ".join(hashtags)).lower()

    if any(w in text for w in ["happy", "joy", "smile", "love", "beautiful"]):
        return "happy"
    elif any(w in text for w in ["sad", "pain", "alone", "breakup", "miss"]):
        return "sad"
    elif any(w in text for w in ["motivation", "success", "confident", "strong"]):
        return "empowered"
    elif any(w in text for w in ["spiritual", "god", "prayer", "faith"]):
        return "peaceful"
    else:
        return "neutral"


def _extract_topics(caption: str, hashtags: list) -> list:
    """Extract topics from caption and hashtags."""
    topics = []
    text = (caption + " " + " ".join(hashtags)).lower()

    topic_keywords = {
        "motivation": ["motivation", "success", "hard work"],
        "love": ["love", "relationship", "romantic"],
        "spirituality": ["god", "spiritual", "prayer"],
        "entertainment": ["movie", "story", "song"],
        "lifestyle": ["lifestyle", "fashion", "beauty"]
    }

    for topic, keywords in topic_keywords.items():
        if any(k in text for k in keywords):
            topics.append(topic.title())

    return topics or ["General"]


def _generate_recommendation_tags(categories: list, caption: str) -> list:
    """Generate recommendation tags."""
    tags = []

    if categories:
        tags.append(f"category-{str(categories[0])[:8]}")

    if caption:
        if len(caption) < 50:
            tags.append("short-form")
        else:
            tags.append("long-form")

    tags.append("auto-recommended")
    return tags[:5]  # Limit to 5 tags


def _generate_keywords(caption: str, hashtags: list) -> list:
    """Generate keywords from caption and hashtags."""
    keywords = set()

    # Add hashtags as keywords
    keywords.update(hashtags)

    # Add common words from caption
    if caption:
        words = caption.split()[:5]  # First 5 words
        keywords.update(words)

    return list(keywords)[:10]  # Limit to 10 keywords


# ============================================================================
# ERROR DOCUMENTATION
# ============================================================================

@app.get("/api/v1/errors")
async def error_codes():
    """
    Get all error codes and descriptions.

    Returns:
        Dictionary of error codes
    """
    return {
        "error_codes": {
            code.value: code.name
            for code in ErrorCode
        }
    }


# ============================================================================
# DEBUG / TRANSPARENCY ENDPOINT
# ============================================================================

@app.get("/api/v1/debug-feed")
async def debug_feed(user_id: str, category: str = "Motivation", limit: int = 30):
    """
    Debug endpoint to visualize exactly why feeds were chosen.
    Returns the feed ID, final score, and the exact mathematical breakdown.
    """
    try:
        optimizer = get_optimizer()
        
        # We simulate a recommendation request
        recommendations = optimizer.get_recommendations(
            user_id=user_id,
            limit=limit,
            category_id=category
        )
        
        debug_output = []
        for rec in recommendations:
            metrics = rec.metadata.get("metrics", {})
            debug_output.append({
                "feed_id": rec.feed_id,
                "category": rec.category,
                "final_score": rec.score,
                "optimizer_math": {
                    "freshness_points": f"+{metrics.get('festival_score', 0)} (Decay formula applied)",
                    "engagement_points": f"+{metrics.get('trending_score', 0)} (Based on watch time/scroll)",
                    "ml_quality_points": f"+{metrics.get('push_score', 0)} (AI Confidence)",
                    "social_proof_points": f"+{metrics.get('time_relevance_score', 0)} (Raw views)",
                },
                "reasons": rec.reason
            })
            
        return {
            "success": True,
            "user_id": user_id,
            "requested_category": category,
            "total_returned": len(debug_output),
            "debug_feed": debug_output
        }
    except Exception as e:
        logger.error(f"Debug feed error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=Config.DEBUG
    )
