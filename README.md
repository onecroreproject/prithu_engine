# ============================================================================
# PRITHU RECOMMENDATION ENGINE - BACKEND DOCUMENTATION
# ============================================================================

## Project Structure

```
Backend - New/
├── config.py                 # Configuration management
├── exceptions.py             # Custom exceptions with error codes
├── logger_setup.py           # Logging configuration
├── db_connection.py          # MongoDB connection and operations
├── schemas.py                # Pydantic models for I/O validation
├── optimizer.py              # Core recommendation engine (Category-based RFRE)
├── api.py                    # FastAPI application and endpoints
├── main.py                   # Application entry point
├── requirements-new.txt      # Python dependencies
├── README.md                 # This file
└── .env                      # Environment configuration (from parent)
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│           Node.js Backend (Social Media API)            │
├─────────────────────────────────────────────────────────┤
│  POST /api/v1/recommend        POST /api/v1/analyze     │
│  └─────────────────┬──────────────────────┬─────────────┘
│                    │                      │
│                    ▼                      ▼
│        ┌──────────────────────────────────────────┐
│        │  FastAPI Application (api.py)            │
│        │  - Request validation (Pydantic)         │
│        │  - Error handling                        │
│        │  - Logging & monitoring                  │
│        └──────────────────┬───────────────────────┘
│                           │
│                           ▼
│        ┌──────────────────────────────────────────┐
│        │  Recommendation Optimizer (optimizer.py) │
│        │  - Category-based scoring                │
│        │  - Festival detection                    │
│        │  - Time relevance calculation            │
│        │  - Diversity filtering                   │
│        └──────────────────┬───────────────────────┘
│                           │
│                           ▼
│        ┌──────────────────────────────────────────┐
│        │  Database Layer (db_connection.py)       │
│        │  - Connection management                 │
│        │  - Query execution                       │
│        │  - Error handling                        │
│        └──────────────────┬───────────────────────┘
│                           │
│                           ▼
│              MongoDB Atlas (Prithu-DB)
└─────────────────────────────────────────────────────────┘
```

## Setup Instructions

### 1. Environment Variables

Create or update `.env` file in `Backend - New/` folder:

```env
# Database Configuration
PRITHU_DB_URI=mongodb+srv://...
PRITHU_DB_NAME=Prithu-DB

# Redis Configuration (optional)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Application Configuration
ENVIRONMENT=development
DEBUG=False
LOG_LEVEL=INFO

# Server Configuration
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
```

### 2. Install Dependencies

```bash
pip install -r requirements-new.txt
```

### 3. Run the Application

```bash
# Development mode with auto-reload
python main.py

# Or directly with uvicorn
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "database": true,
  "cache": true,
  "timestamp": "2026-09-11T10:30:00"
}
```

### 2. Get Recommendations

**Endpoint:** `POST /api/v1/recommend`

**Request:**
```json
{
  "user_id": "user123",
  "limit": 20,
  "exclude_ids": ["feed1", "feed2"],
  "diversity_boost": true,
  "prefer_short": false
}
```

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "recommended_feeds": [
    {
      "feed_id": "feed123",
      "category": "Motivation",
      "score": 85.5,
      "reason": "Festival relevant, High engagement",
      "metadata": {
        "metrics": {
          "festival_score": 50.0,
          "trending_score": 70.0,
          "push_score": 100.0,
          "time_relevance_score": 100.0
        }
      }
    }
  ],
  "total_count": 20,
  "engine_status": "online",
  "timestamp": "2026-09-11T10:30:00"
}
```

### 3. Analyze Feed

**Endpoint:** `POST /api/v1/analyze`

**Request:**
```json
{
  "feed_id": "feed123",
  "category": ["cat1", "cat2"],
  "caption": "Beautiful morning motivational quote",
  "hashtags": ["#motivation", "#morning"],
  "post_type": "image"
}
```

**Response:**
```json
{
  "success": true,
  "feed_id": "feed123",
  "analysis": {
    "feed_id": "feed123",
    "content_type": "image",
    "sub_category": "motivation",
    "emotion": "empowered",
    "topics": ["Self-Improvement", "Motivation"],
    "recommendation_tags": ["category-cat1", "short-form", "auto-recommended"],
    "auto_keywords": ["motivation", "morning", "beautiful"],
    "generated_hashtags": ["#motivation", "#morning"],
    "confidence_score": 0.85
  },
  "timestamp": "2026-09-11T10:30:00"
}
```

## Error Handling

All errors follow standardized format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "specific_field",
      "error": "Error details"
    }
  },
  "data": null
}
```

### Common Error Codes

- `DB_CONNECTION_FAILED` - Database connection error
- `INVALID_INPUT` - Invalid input parameters
- `VALIDATION_ERROR` - Input validation failed
- `RESOURCE_NOT_FOUND` - Requested resource not found
- `OPTIMIZER_ERROR` - Recommendation engine error
- `INTERNAL_SERVER_ERROR` - Unexpected server error

## Configuration

### Recommendation Weights (config.py)

```python
Config.WEIGHT_FESTIVAL = 0.40      # Festival relevance weight
Config.WEIGHT_PUSH = 0.30          # Trending/viral weight
Config.WEIGHT_TRENDING = 0.30      # General trending weight
```

### Time Slots

Recommendations are time-aware:
- **Morning (3-11)**: Motivation, Spiritual content
- **Afternoon (11-15)**: Educational, Business content
- **Evening (15-19)**: Travel, Entertainment content
- **Night (19-23, 0-3)**: Love, Emotional content

### Categories

82 categories are configured in MongoDB, grouped as:
- **Spiritual**: God, Bhakti, Devotional, etc.
- **Motivation**: Motivation, Confident, Success, etc.
- **Emotional**: Love, Breakup, Sad, etc.
- **Entertainment**: Movie, Story, Song, etc.
- **Time-based**: Good Morning, Good Evening, etc.
- **Festivals**: Diwali, Holi, Pongal, etc.

## Logging

Logs are written to:
- Console (all levels)
- File (if `LOG_FILE` env var is set)

Log format:
```
2026-09-11 10:30:00,123 - module_name - INFO - Log message
```

## Database Collections Used

- `Categories` - Category definitions
- `Feeds` - Content/posts with metadata
- `Users` - User profiles
- `UserFeedAnalytics` - User interactions (likes, saves, etc.)
- `UserSeenHistory` - Viewed content tracking
- `DailyFeeds` - Pre-generated daily feeds (cache)
- `TimeSlots` - Time slot configurations
- `GodConfig` - Weekday-to-deity mappings

## Performance Optimization

### Caching Strategy

- Categories cached for 1 hour
- Daily feeds cached per user per date
- Feed scores calculated on-demand

### Pagination

- Default limit: 20 recommendations
- Maximum limit: 100 recommendations
- Efficient MongoDB cursors with indexes

### Indexes

MongoDB indexes are created on:
- `Feeds` (isApproved, isDeleted)
- `Categories` (_id, name)
- `UserFeedAnalytics` (userId, feedId)

## Testing

Run tests with pytest:

```bash
pytest -v
pytest -v --cov=.
```

## Monitoring

Check application status:

```bash
# Health check
curl http://localhost:8000/health

# View documentation
curl http://localhost:8000/docs

# Error codes
curl http://localhost:8000/api/v1/errors
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-new.txt .
RUN pip install -r requirements-new.txt
COPY . .
CMD ["python", "main.py"]
```

### Environment Variables (Production)

```bash
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
```

## Troubleshooting

### Database Connection Error

```
Error: DB_CONNECTION_FAILED
```

**Solution:**
1. Verify `PRITHU_DB_URI` in `.env`
2. Check MongoDB Atlas network access
3. Ensure credentials are correct

### Timeout Error

```
Error: serverSelectionTimeoutError
```

**Solution:**
1. Check internet connectivity
2. Verify MongoDB Atlas cluster is running
3. Increase `MONGODB_TIMEOUT` in config.py

### Empty Recommendations

**Solution:**
1. Check if feeds exist in database
2. Verify categories are properly linked
3. Review logs for scoring errors

## Next Steps

1. **Optimizer Customization**: Add ML models for sentiment analysis
2. **Performance**: Implement Redis caching for scored feeds
3. **Advanced Scoring**: Add collaborative filtering
4. **A/B Testing**: Track recommendation effectiveness
5. **Analytics**: Log recommendation impressions and clicks

## Support

For issues or questions:
1. Check logs: `tail -f prithu.log`
2. Review documentation in `/docs`
3. Check error codes in API response

---

**Version:** 1.0.0  
**Last Updated:** 2026-09-11  
**Status:** Production Ready ✅
