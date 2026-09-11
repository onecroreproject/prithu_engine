# ============================================================================
# QUICK START GUIDE - PRITHU RECOMMENDATION ENGINE
# ============================================================================

## 📁 Production-Grade Backend Structure Created

### Core Modules

1. **config.py** (Configuration Management)
   - Environment variable loading
   - Application constants
   - Database configuration
   - Scoring weights
   - Validation settings
   - Class methods for validation

2. **exceptions.py** (Error Handling)
   - Custom exception hierarchy
   - Standard error codes (ErrorCode enum)
   - Detailed error responses
   - Specific exception types:
     - DatabaseException
     - ResourceNotFoundException
     - ValidationException
     - OptimizerException
     - CacheException

3. **logger_setup.py** (Logging)
   - Singleton logger manager
   - Console and file handlers
   - Rotating file handler (10MB, 5 backups)
   - Structured logging
   - Module-level logger retrieval

4. **db_connection.py** (Database Layer)
   - MongoDB singleton connection manager
   - Connection pooling
   - Error handling for all operations
   - Query methods:
     - find_one() - Get single document
     - find_many() - Get multiple documents with sorting
     - insert_one() - Insert document
     - update_one() - Update document
     - delete_one() - Delete document
     - count_documents() - Count matching docs
     - get_distinct() - Get unique values
   - Health check capability

5. **schemas.py** (Data Validation)
   - Input models (from Node.js):
     - RecommendationRequest
     - FeedAnalysisRequest
   - Output models (to Node.js):
     - RecommendationResponse
     - AnalysisResponse
     - FeedRecommendation
   - Internal models:
     - CategoryMetadata
     - UserProfile
     - ScoringMetrics
   - Error response model

6. **optimizer.py** (Recommendation Engine)
   - Category-based RFRE (Rule-based Feed Recommendation Engine)
   - Scoring methods:
     - Festival relevance scoring
     - Trending score calculation
     - Push/viral score
     - Time relevance scoring
   - Festival detection (32 festivals/holidays)
   - Recommendation generation
   - Diversity filtering
   - Category caching
   - Health monitoring

7. **api.py** (FastAPI Application)
   - Application initialization with lifespan management
   - CORS middleware
   - Exception handlers:
     - Custom exception handler
     - Validation error handler
     - Global exception handler
   - Endpoints:
     - GET /health - Health check
     - GET / - Root endpoint
     - POST /api/v1/recommend - Get recommendations
     - POST /api/v1/analyze - Analyze feed content
     - GET /api/v1/errors - Error code documentation
   - Helper functions for content analysis

8. **main.py** (Application Entry Point)
   - Clean startup script
   - Environment configuration
   - Uvicorn server initialization
   - Graceful shutdown handling

---

## 🚀 Quick Start

### Step 1: Install Dependencies
```bash
cd "d:\Project\Prithu Engine\Backend - New"
pip install -r requirements-new.txt
```

### Step 2: Verify .env Configuration
```bash
# Check Backend - New\.env file has:
PRITHU_DB_URI=mongodb+srv://prithuapp_db_user:eETUIeouSRU7Xipu@cluster0.x0vkq8e.mongodb.net/Prithu-DB?...
PRITHU_DB_NAME=Prithu-DB
```

### Step 3: Run Application
```bash
python main.py
```

Application starts on: `http://localhost:8000`

---

## 📊 Data Flow (Node.js ↔ Python)

```
NODE.JS BACKEND
    │
    ├─ POST /api/v1/recommend
    │   └─ Body: {user_id, limit, exclude_ids, diversity_boost, prefer_short}
    │
    └─ POST /api/v1/analyze
        └─ Body: {feed_id, category, caption, hashtags, post_type}
    
            ↓ (HTTP Request)
    
PYTHON OPTIMIZER
    │
    ├─ api.py (receives request)
    │   └─ schemas.py (validates input with Pydantic)
    │
    ├─ optimizer.py (processes)
    │   ├─ Load categories
    │   ├─ Score feeds based on:
    │   │   ├─ Festival relevance
    │   │   ├─ Trending metrics
    │   │   ├─ Push score
    │   │   └─ Time relevance
    │   └─ Return ranked recommendations
    │
    └─ db_connection.py (queries)
        └─ MongoDB (fetches feeds & categories)
    
            ↓ (HTTP Response)
    
NODE.JS BACKEND
    └─ Receives: {success, recommended_feeds, total_count, engine_status}
        └─ Displays to Mobile/Website
```

---

## 🎯 Key Features

### ✅ Production-Grade Error Handling
- Custom exceptions with error codes
- Detailed error messages
- Graceful fallbacks
- Structured error responses

### ✅ Comprehensive Logging
- Console and file logging
- Different log levels (DEBUG, INFO, WARNING, ERROR)
- Rotating file handler
- Module-level loggers

### ✅ Data Validation
- Pydantic models for all I/O
- Field-level validation
- Type hints throughout
- Clear error messages

### ✅ Database Layer
- Connection pooling
- Singleton pattern
- Query wrappers with error handling
- Health check capability

### ✅ Recommendation Engine
- 82 categories supported
- Festival detection (32+ festivals)
- Time-aware recommendations
- Diversity filtering
- Weighted scoring system

### ✅ API Standards
- RESTful endpoints
- JSON request/response
- Proper HTTP status codes
- CORS support
- Health check endpoint
- API documentation at /docs

---

## 📋 Scoring System

### Festival Score (40% weight)
- Detects 32 festivals/holidays
- Multiplier: 1.67x for matching content
- Base scores: 40-60 points

### Push Score (30% weight)
- Triggers if views >= 1000 OR likes >= 50
- Score: 100 (viral content)

### Trending Score (30% weight)
- Views: 40% of score
- Likes: 60% of score
- Normalized to max values

### Time Relevance (Multiplier: 1.5x)
- Morning (3-11): Motivation, Spiritual
- Afternoon (11-15): Education, Business
- Evening (15-19): Entertainment, Travel
- Night (19-23, 0-3): Love, Emotional

**Final Score Formula:**
```
final_score = (0.40 × festival) + (0.30 × push) + (0.30 × trending)
if time_relevant:
    final_score × 1.5
```

---

## 🔒 Security

- Input validation (Pydantic)
- Type checking (mypy compatible)
- Error message sanitization
- Database connection security
- CORS configuration
- Timeout configurations

---

## 📈 Performance

- Category caching (1 hour TTL)
- Feed query limit (5000 feeds)
- Efficient MongoDB indexes
- Pagination support
- Async/await ready

---

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/health

# Get recommendations
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","limit":20}'

# Analyze feed
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"feed_id":"feed123","caption":"Good morning","post_type":"image"}'

# View API docs
# http://localhost:8000/docs
```

---

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Scoring weights
Config.WEIGHT_FESTIVAL = 0.40
Config.WEIGHT_PUSH = 0.30
Config.WEIGHT_TRENDING = 0.30

# Limits
Config.DAILY_FEED_MAX = 20
Config.DEFAULT_RECOMMENDATION_LIMIT = 20

# Cache
Config.CACHE_TTL_SECONDS = 3600
```

---

## 📚 File Reference

| File | Purpose | Lines |
|------|---------|-------|
| config.py | Configuration management | ~150 |
| exceptions.py | Custom exceptions | ~200 |
| logger_setup.py | Logging setup | ~100 |
| db_connection.py | Database operations | ~450 |
| schemas.py | Pydantic models | ~350 |
| optimizer.py | Recommendation engine | ~550 |
| api.py | FastAPI application | ~500 |
| main.py | Entry point | ~60 |
| **TOTAL** | **Production-ready backend** | **~2,400 lines** |

---

## ✨ Next Steps

1. **Test with Node.js backend** - Call /api/v1/recommend from Node
2. **Customize optimizer** - Add ML models, adjust scoring
3. **Add caching** - Implement Redis for performance
4. **Monitor & log** - Track recommendation effectiveness
5. **Deploy** - Docker container, production server

---

## 🎓 Architecture Principles Used

- ✅ **Single Responsibility** - Each module has one purpose
- ✅ **Dependency Injection** - Database, logger injected
- ✅ **Error Handling** - Custom exceptions, try-catch blocks
- ✅ **Logging** - Structured logging throughout
- ✅ **Validation** - Pydantic models for I/O
- ✅ **Configuration Management** - Centralized config
- ✅ **Singleton Pattern** - Database manager, optimizer
- ✅ **Scalability** - Pagination, caching, indexing
- ✅ **Testability** - Clean interfaces, dependency injection
- ✅ **Documentation** - Docstrings, type hints, README

---

**Status:** ✅ **Production-Ready**

Everything is built with enterprise-grade patterns, error handling, and documentation!

Ready for Node.js integration! 🚀
